#!/usr/bin/env python3
"""Build data/esafety-bose.json — the tidy-long eSafety BOSE metrics snapshot.

Australia's eSafety Commissioner publishes transparency findings under the
Basic Online Safety Expectations (BOSE, Online Safety Act 2021). Unlike the
sibling `dsa-transparency-data` extractors, there is no machine-readable source
release for these — the figures are transcribed from the published PDFs / pages
(archived under `esafety-bose-reports/`), each row carrying a page/figure
citation in this builder. Two report streams are captured:

  * `csea_periodic` — "Basic Online Safety Expectations. Summary of industry
    responses to the periodic notices on CSEA and sexual extortion" (notices
    given 22 Jul 2024; reporting period 15 Jul–15 Dec 2024; Aug 2025 report,
    Feb 2026 update). Figure 4: user reports of CSEA per service (global) and
    the median time to reach an outcome where a human moderator reviewed.

  * `ai_companion_*` / `survey_prevalence` — "Findings from transparency notices
    on AI companion apps: October 2025 (non-periodic)". Notices to Chai,
    Character.AI, Chub AI and Nomi; reporting period 1 Jul–30 Sep 2025. Per-
    provider user-report counts by harm, trust-&-safety staffing, and eSafety's
    2026 prevalence survey of children aged 10–17.

Tidy-long shape mirrors singapore-online-safety.json:
    columns = service, period, section, category, metric, unit, value
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, os.pardir, "data", "esafety-bose.json")

COLUMNS = ["service", "period", "section", "category", "metric", "unit", "value"]

# ---------------------------------------------------------------------------
# Stream 1: CSEA & sexual-extortion periodic reporting — reporting period
# 15 Jul–15 Dec 2024 (Aug 2025 report, updated Feb 2026).
# Figure 4: "Number of user reports and median time taken to reach an outcome,
# where reports were reviewed by human moderators – global."
CSEA_PERIOD = "2024-07-15..2024-12-15"

# Subsequent editions in the same four-report periodic-notice series. Report 2's
# public snapshot is chiefly qualitative, so its two rows record the scope of
# the edition. Report 3 publishes complaint counts in its accessible text.
# Sources:
#   /periodic-notice-report-2-snapshot (published 2026)
#   /periodic-notice-report-3-snapshot (published 14 Jul 2026)
CSEA_REPORT_2_PERIOD = "2025-01-01..2025-06-30"
CSEA_REPORT_3_PERIOD = "2025-07-01..2025-12-31"

CSEA_REPORT_2 = [
    ("All providers (report 2)", "providers_in_scope", "count", 8),
    ("All providers (report 2)", "providers_with_observed_safety_improvements", "count", 8),
]

CSEA_REPORT_3 = [
    ("All complaints", "sexual_extortion_complaints", "count", 2_206),
    ("Male complainants", "share_of_complaints", "percent", 85),
    ("Males aged 18 to 24", "sexual_extortion_complaints", "count", 803),
    ("Males aged 25 to 39", "sexual_extortion_complaints", "count", 574),
    ("Instagram", "service_referenced_in_complaint", "count", 695),
    ("WhatsApp", "service_referenced_in_complaint", "count", 612),
    ("Telegram", "service_referenced_in_complaint", "count", 558),
    ("Tinder", "initial_contact_service", "count", 162),
    ("Instagram", "initial_contact_service", "count", 73),
    ("Grindr", "initial_contact_service", "count", 60),
    ("WhatsApp", "threat_service", "count", 596),
    ("Telegram", "threat_service", "count", 547),
    ("Instagram", "threat_service", "count", 241),
]

# service -> (user reports global, median response minutes | None)
# Median times transcribed from Figure 4 (h/m) and converted to minutes.
CSEA_FIG4 = {
    "Facebook":            (6_700_000, 11 * 60 + 46),   # 11h46m
    "Instagram":           (2_100_000, 8 * 60 + 58),    # 8h58m
    "Snapchat":            (1_361_148, 1 * 60 + 30),    # 1h30m
    "WhatsApp Messaging":  (811_208, 27 * 60 + 1),      # 27h1m  (accounts banned proxy)
    "Skype":               (310_955, 1 * 60 + 49),      # 1h49m
    "Discord":             (86_990, 58),                # 58m
    "Threads":             (46_900, 33),                # 33m
    "Facebook Messenger":  (30_700, 8 * 60 + 19),       # 8h19m
    "WhatsApp Channels":   (8_656, 16 * 60 + 20),       # 16h20m
    "Xbox":                (1_331, 1 * 60 + 8),         # 1h8m
    "Microsoft Teams":     (778, 1 * 60 + 41),          # 1h41m
    "Google Drive":        (207, 7 * 60 + 12),          # 7h12m
    "Outlook.com":         (74, 6 * 60 + 21),           # 6h21m
    "Microsoft OneDrive":  (27, 2 * 60 + 32),           # 2h32m
    "Google Chat":         (1, 54),                     # 54m
    "Google Meet":         (1, 99 * 60 + 12),           # 99h12m (single complex report)
    "Google Messages":     (0, None),                   # N/A median
}

# Australia-specific + aggregate figures from the report's "Key insights".
# These are TOTALS that overlap the per-service rows above — see the TableSpec
# note. Stored under distinct service labels so a naive SUM can be avoided.
CSEA_AUS = [
    ("All services (total)", "user_reports_global",    "count", 11_458_969),
    ("All services (total)", "user_reports_australia", "count", 374_261),
    ("Meta services (aggregate)", "user_reports_global",    "count", 8_877_600),
    ("Meta services (aggregate)", "user_reports_australia", "count", 39_749),
    ("Snapchat", "user_reports_australia", "count", 27_796),
]

# ---------------------------------------------------------------------------
# Stream 2: AI companion apps — reporting period 1 Jul–30 Sep 2025.
AIC_PERIOD = "2025-07-01..2025-09-30"

# provider -> {harm category: user reports}. Absent harm = not reported / 0.
AIC_USER_REPORTS = {
    "Character.AI": {"pornography": 3_164, "csea": 1_527, "self_harm": 642},
    "Chai":         {"pornography": 504,   "csea": 8,     "self_harm": 28},
    "Chub AI":      {"csea": 47},
    "Nomi":         {"pornography": 0,     "csea": 2,     "self_harm": 2},
}

# provider -> staff responsible for trust & safety (Figure 2, as at 30 Sep 2025)
AIC_TS_STAFF = {
    "Character.AI": 37,
    "Chai": 6.5,
    "Chub AI": 0,
    "Nomi": 0,
}

# eSafety 2026 survey of 1,950 children aged 10–17 (percentages).
SURVEY_PERIOD = "2026"
SURVEY = [
    ("AI companion or assistant", "ever_used",        79),
    ("AI companion",              "ever_used",        8),
    ("AI companion or assistant", "used_past_4_weeks", 66),
    ("AI companion",              "used_past_4_weeks", 4),
    # per-provider "ever used" among children 10–17
    ("Character.AI", "ever_used", 5),
    ("Chai",         "ever_used", 2),
    ("Chub AI",      "ever_used", 0.4),
    ("Nomi",         "ever_used", 0.3),
]


def build_rows() -> list[list]:
    rows: list[list] = []

    # --- CSEA per-service (Figure 4) ---
    for service, (reports, median_min) in CSEA_FIG4.items():
        rows.append([service, CSEA_PERIOD, "csea_periodic", "",
                     "user_reports_global", "count", reports])
        if median_min is not None:
            rows.append([service, CSEA_PERIOD, "csea_periodic", "",
                         "median_response_minutes", "minutes", median_min])
    # --- CSEA Australia / aggregate totals ---
    for service, metric, unit, value in CSEA_AUS:
        rows.append([service, CSEA_PERIOD, "csea_periodic", "", metric, unit, value])
    # --- Later CSEA periodic-report editions ---
    for service, metric, unit, value in CSEA_REPORT_2:
        rows.append([service, CSEA_REPORT_2_PERIOD, "csea_periodic_report_2", "",
                     metric, unit, value])
    for service, metric, unit, value in CSEA_REPORT_3:
        rows.append([service, CSEA_REPORT_3_PERIOD, "csea_periodic_report_3",
                     "sexual_extortion", metric, unit, value])

    # --- AI companion user reports by harm ---
    for provider, harms in AIC_USER_REPORTS.items():
        for harm, value in harms.items():
            rows.append([provider, AIC_PERIOD, "ai_companion_reports", harm,
                         "user_reports", "count", value])
    # --- AI companion trust & safety staffing ---
    for provider, staff in AIC_TS_STAFF.items():
        rows.append([provider, AIC_PERIOD, "ai_companion_staff", "",
                     "trust_safety_staff", "count", staff])
    # --- eSafety prevalence survey ---
    for service, metric, value in SURVEY:
        rows.append([service, SURVEY_PERIOD, "survey_prevalence", "children_10_17",
                     metric, "percent", value])

    return rows


def validate(rows: list[list]) -> None:
    """Fail-loud cross-checks against figures stated elsewhere in the reports."""
    def g(service):
        return next(r[6] for r in rows if r[0] == service and r[4] == "user_reports_global")

    # Meta's four services must sum to the report's stated Meta aggregate.
    meta_sum = sum(g(s) for s in ("Facebook", "Instagram", "Facebook Messenger", "Threads"))
    assert meta_sum == 8_877_600, f"Meta service sum {meta_sum} != stated 8,877,600"

    # Column arity.
    for r in rows:
        assert len(r) == len(COLUMNS), f"bad row arity: {r}"
        assert isinstance(r[6], (int, float)) and not isinstance(r[6], bool), f"non-numeric value: {r}"


def main() -> None:
    rows = build_rows()
    validate(rows)
    snapshot = {
        "source": "https://www.esafety.gov.au/industry/basic-online-safety-expectations",
        "regime": "Basic Online Safety Expectations (Online Safety Act 2021)",
        "publisher": "eSafety Commissioner (Australia)",
        "coverage": "2024-07-15..2025-12-31 (CSEA reports 1-3); 2025-07-01..2025-09-30 (AI companions)",
        "columns": COLUMNS,
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=0)
        f.write("\n")
    services = sorted({r[0] for r in rows})
    sections = sorted({r[2] for r in rows})
    print(f"wrote {len(rows)} rows across {len(services)} services, "
          f"{len(sections)} sections -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
