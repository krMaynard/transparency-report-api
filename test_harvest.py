"""Tests for scripts/harvest-harmonized.py."""
import csv
import importlib.util
import sqlite3
from pathlib import Path

import pytest
import seed

# ---------------------------------------------------------------------------
# Import the hyphen-named script via importlib
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).parent / "scripts" / "harvest-harmonized.py"
_spec = importlib.util.spec_from_file_location("harvest_harmonized", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

harvest_service = _mod.harvest_service
_int_or_none = _mod._int_or_none
_open_csv = _mod._open_csv
_find_part = _mod._find_part
_T4_COLS = _mod._T4_COLS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMPTY_SEED: dict = {
    "meta": {"period": "2025-07-01/2025-12-31", "generated": "2026-05-13"},
    "services": [],
    "service_platforms": [],
    "categories": [],
    "category_labels": {},
    "sections": [],
    "indicators": [],
    "scopes": [],
    "surfaces": [],
    "t3": [], "t4": [], "t5": [], "t6": [],
    "t7": [], "t8": [], "t9": [], "t10": [], "t11": [],
}


@pytest.fixture()
def harvest_db(tmp_path):
    """Fresh writable DB with the DSA star schema and no fact rows."""
    db = str(tmp_path / "harvest_test.db")
    seed.build_db(_EMPTY_SEED, db)
    return db


def _write_csv(path: Path, headers: list, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow(row)


@pytest.fixture()
def csv_dir(tmp_path):
    """Temp directory pre-populated with one fixture CSV per Annex I Part (1–11)."""
    d = tmp_path / "parts"
    d.mkdir()

    _write_csv(d / "part1.csv",
        ["Service identifier", "Reporting period start date", "Reporting period end date",
         "Date of publication", "Type of provider"],
        [["TestPlatform", "2026-01-01", "2026-06-30", "2026-08-01",
          "very large online platform"]],
    )
    _write_csv(d / "part2.csv",
        ["Category code", "Category name"],
        [["TOTAL", "All categories"], ["ILLEGAL_SPEECH", "Illegal or harmful speech"]],
    )
    _write_csv(d / "part3.csv",
        ["Category code", "Type of order",
         "Number of removal orders", "Number of items subject to removal orders",
         "Number of information orders"],
        [["TOTAL", "Removal", "10", "50", "3"]],
    )
    _write_csv(d / "part4.csv",
        ["Category code", "Number of notices received",
         "Number of notices from trusted flaggers",
         "Number of items subject to notices",
         "Number of items subject to trusted-flagger notices",
         "Median time to process notices (days)",
         "Median time to process trusted-flagger notices (days)",
         "Actions taken on legal basis",
         "Trusted-flagger actions on legal basis",
         "Actions taken on terms-and-conditions basis",
         "Trusted-flagger actions on T&C basis"],
        [["TOTAL", "100", "10", "200", "20", "5", "N/A", "30", "3", "70", "7"]],
    )
    _write_csv(d / "part5.csv",
        ["Category code", "Total measures", "Measures applied using automated means",
         "Visibility: removal", "Visibility: disabling access", "Visibility: demotion",
         "Visibility: age restriction", "Visibility: interaction restriction",
         "Visibility: labelling", "Visibility: other",
         "Monetary: suspension", "Monetary: termination", "Monetary: other",
         "Service: suspension", "Service: termination",
         "Account: suspension", "Account: termination"],
        [["TOTAL", "9", "4", "5", "0", "0", "0", "0", "0", "0",
          "0", "0", "0", "0", "0", "0", "0"]],
    )
    _write_csv(d / "part6.csv",
        ["Category code", "Total measures", "Measures applied using automated means",
         "Visibility: removal", "Visibility: disabling access", "Visibility: demotion",
         "Visibility: age restriction", "Visibility: interaction restriction",
         "Visibility: labelling", "Visibility: other",
         "Monetary: suspension", "Monetary: termination", "Monetary: other",
         "Service: suspension", "Service: termination",
         "Account: suspension", "Account: termination",
         "Surface type"],
        [["TOTAL", "9", "4", "5", "0", "0", "0", "0", "0", "0",
          "0", "0", "0", "0", "0", "0", "0", "Main feed"]],
    )
    _write_csv(d / "part7.csv",
        ["Section", "Indicator", "Scope", "Surface", "Value"],
        [["Internal complaints mechanism", "Number of complaints",
          "Total number", "All", "1000"]],
    )
    _write_csv(d / "part8.csv",
        ["Section", "Indicator", "Scope", "Surface", "Value"],
        [["Detection", "Automated detections", "Total number", "All", "500"]],
    )
    _write_csv(d / "part9.csv",
        ["Section", "Indicator", "Scope", "Value"],
        [["Content moderation", "FTE", "Total number", "12"]],
    )
    _write_csv(d / "part10.csv",
        ["Scope", "Average monthly active recipients"],
        [["Total number", "64000000"]],
    )
    _write_csv(d / "part11.csv",
        ["Indicator", "Description"],
        [["Summary of policies", "This is a qualitative description."]],
    )

    return d


_ENTRY = {
    "service_name": "TestPlatform",
    "platform": "TestCo",
    "tier": "vlop",
    "period_start": "2026-01-01",
    "period_end": "2026-06-30",
    "report_url": None,
}


# ---------------------------------------------------------------------------
# _int_or_none
# ---------------------------------------------------------------------------

class TestIntOrNone:
    def test_valid_int(self):
        assert _int_or_none("42") == 42

    def test_with_commas(self):
        assert _int_or_none("1,234,567") == 1234567

    def test_zero(self):
        assert _int_or_none("0") == 0

    def test_empty_string(self):
        assert _int_or_none("") is None

    def test_na_uppercase(self):
        assert _int_or_none("N/A") is None

    def test_na_lowercase(self):
        assert _int_or_none("n/a") is None

    def test_dash(self):
        assert _int_or_none("-") is None

    def test_none_input(self):
        assert _int_or_none(None) is None

    def test_negative_int(self):
        assert _int_or_none("-1") == -1


# ---------------------------------------------------------------------------
# _open_csv
# ---------------------------------------------------------------------------

class TestOpenCsv:
    def test_canonical_mapping(self, tmp_path):
        p = tmp_path / "t4.csv"
        _write_csv(p, ["Category code", "Number of notices received"], [["TOTAL", "100"]])
        headers, rows = _open_csv(p, _T4_COLS)
        assert "Category code" in headers
        assert rows[0]["category_code"] == "TOTAL"
        assert rows[0]["notices"] == "100"

    def test_case_insensitive_headers(self, tmp_path):
        p = tmp_path / "t4.csv"
        _write_csv(p, ["CATEGORY CODE", "NUMBER OF NOTICES RECEIVED"], [["SPAM", "5"]])
        _, rows = _open_csv(p, _T4_COLS)
        assert rows[0]["category_code"] == "SPAM"
        assert rows[0]["notices"] == "5"

    def test_empty_csv_returns_empty(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        headers, rows = _open_csv(p, _T4_COLS)
        assert headers == []
        assert rows == []

    def test_unknown_header_passed_through(self, tmp_path):
        p = tmp_path / "t4.csv"
        _write_csv(p, ["Unknown column"], [["val"]])
        _, rows = _open_csv(p, _T4_COLS)
        assert rows[0]["Unknown column"] == "val"


# ---------------------------------------------------------------------------
# _find_part
# ---------------------------------------------------------------------------

class TestFindPart:
    def test_finds_part_by_prefix(self, tmp_path):
        (tmp_path / "part3.csv").touch()
        found = _find_part(tmp_path, 3)
        assert found is not None
        assert found.name == "part3.csv"

    def test_returns_none_when_missing(self, tmp_path):
        assert _find_part(tmp_path, 4) is None

    def test_ignores_xlsx(self, tmp_path):
        (tmp_path / "part3.xlsx").touch()
        assert _find_part(tmp_path, 3) is None

    def test_finds_by_substring(self, tmp_path):
        (tmp_path / "my_notices_part4_final.csv").touch()
        found = _find_part(tmp_path, 4)
        assert found is not None


# ---------------------------------------------------------------------------
# harvest_service — integration
# ---------------------------------------------------------------------------

class TestHarvestService:
    def test_row_counts(self, harvest_db, csv_dir):
        counts = harvest_service(
            _ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False
        )
        assert counts == {
            "t3": 1, "t4": 1, "t5": 1, "t6": 1, "t7": 1,
            "t8": 1, "t9": 1, "t10": 1, "t11": 1,
        }

    def test_t4_values_written(self, harvest_db, csv_dir):
        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        row = conn.execute(
            "SELECT notices, tf_median_time FROM t4_notices n "
            "JOIN services s ON s.id = n.service_id WHERE s.name = 'TestPlatform'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 100
        assert row[1] is None  # "N/A" → _int_or_none → None

    def test_t10_amar_value(self, harvest_db, csv_dir):
        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        val = conn.execute(
            "SELECT value FROM t10_amar n "
            "JOIN services s ON s.id = n.service_id WHERE s.name = 'TestPlatform'"
        ).fetchone()[0]
        conn.close()
        assert val == 64_000_000

    def test_t11_qualitative_text(self, harvest_db, csv_dir):
        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        text = conn.execute(
            "SELECT value_text FROM t11_qualitative n "
            "JOIN services s ON s.id = n.service_id WHERE s.name = 'TestPlatform'"
        ).fetchone()[0]
        conn.close()
        assert text == "This is a qualitative description."

    def test_tier_resolved_from_part1(self, harvest_db, csv_dir):
        """'very large online platform' in Part 1 maps to 'vlop' in reports table."""
        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        tier = conn.execute(
            "SELECT tier FROM reports WHERE period_start = '2026-01-01'"
        ).fetchone()[0]
        conn.close()
        assert tier == "vlop"

    def test_dry_run_no_db_writes(self, harvest_db, csv_dir):
        counts = harvest_service(
            _ENTRY, harvest_db, csv_dir, {}, dry_run=True, show_headers=False
        )
        assert counts["part3"] == 1
        assert counts["part4"] == 1
        conn = sqlite3.connect(harvest_db)
        n_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        n_t4 = conn.execute("SELECT COUNT(*) FROM t4_notices").fetchone()[0]
        conn.close()
        assert n_reports == 1   # only the seed's initial row
        assert n_t4 == 0

    def test_skip_when_no_url_and_no_source_dir(self, harvest_db):
        counts = harvest_service(
            _ENTRY, harvest_db, None, {}, dry_run=False, show_headers=False
        )
        assert counts == {}

    def test_second_run_reuses_report_row(self, harvest_db, csv_dir):
        """Re-ingesting the same period+tier reuses the existing reports row."""
        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        n_before = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        conn.close()

        harvest_service(_ENTRY, harvest_db, csv_dir, {}, dry_run=False, show_headers=False)
        conn = sqlite3.connect(harvest_db)
        n_after = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        conn.close()
        assert n_after == n_before
