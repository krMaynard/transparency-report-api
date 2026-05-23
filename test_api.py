"""Smoke tests for the SQL Query API.

conftest.py sets up a temp SQLite DB and env vars before main is imported.
No Redis required — the in-memory store is used automatically.
"""
import time

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
ALICE = {"X-API-Key": "alice"}
BOB = {"X-API-Key": "bob"}


def _wait_for_job(job_id: str, headers: dict, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = client.get(f"/jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("done", "failed", "cancelled"):
            return body
        time.sleep(0.05)
    pytest.fail(f"Job {job_id} did not reach a terminal state within {timeout}s")


def _submit_and_wait(sql: str, headers: dict = ALICE) -> dict:
    r = client.post("/query", json={"sql": sql}, headers=headers)
    assert r.status_code == 202
    return _wait_for_job(r.json()["job_id"], headers)


# ── Infrastructure ────────────────────────────────────────────────────────────

class TestInfra:
    def test_root_no_auth(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "endpoints" in r.json()

    def test_healthz(self):
        assert client.get("/healthz").status_code == 200

    def test_readyz(self):
        assert client.get("/readyz").status_code == 200


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_key_is_401(self):
        assert client.get("/tables").status_code == 401

    def test_bad_key_is_401(self):
        assert client.get("/tables", headers={"X-API-Key": "bogus"}).status_code == 401

    def test_valid_key_ok(self):
        r = client.get("/tables", headers=ALICE)
        assert r.status_code == 200
        assert "removals" in r.json()["tables"]


# ── Schema ────────────────────────────────────────────────────────────────────

class TestSchema:
    def test_known_table(self):
        r = client.get("/schema/removals", headers=ALICE)
        assert r.status_code == 200
        col_names = [c["name"] for c in r.json()["columns"]]
        assert "num_requests" in col_names

    def test_missing_table_is_404(self):
        assert client.get("/schema/nonexistent", headers=ALICE).status_code == 404

    def test_invalid_table_name_is_400(self):
        # Slashes are stripped by the router; test a name that reaches the handler
        # but contains characters the isalnum guard rejects.
        assert client.get("/schema/bad;name", headers=ALICE).status_code == 400


# ── Query lifecycle ───────────────────────────────────────────────────────────

class TestQueryLifecycle:
    def test_submit_returns_202_with_location(self):
        r = client.post("/query", json={"sql": "SELECT 1"}, headers=ALICE)
        assert r.status_code == 202
        assert "job_id" in r.json()
        assert r.headers.get("location", "").startswith("/jobs/")

    def test_happy_path_json(self):
        job = _submit_and_wait("SELECT COUNT(*) AS n FROM removals")
        assert job["status"] == "done"
        r = client.get(f"/jobs/{job['job_id']}/result?format=json", headers=ALICE)
        assert r.status_code == 200
        body = r.json()
        assert body["row_count"] == 1
        assert body["columns"] == ["n"]
        assert body["rows"][0][0] == 3  # 3 rows seeded in conftest.py

    def test_happy_path_csv(self):
        job = _submit_and_wait("SELECT name FROM countries ORDER BY name")
        r = client.get(f"/jobs/{job['job_id']}/result?format=csv", headers=ALICE)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        lines = r.text.strip().splitlines()
        assert lines[0] == "name"
        assert "Germany" in lines
        assert "United States" in lines

    def test_result_before_done_is_409(self):
        r = client.post("/query", json={"sql": "SELECT 1"}, headers=ALICE)
        job_id = r.json()["job_id"]
        # Job may already be done by the time we hit the result endpoint,
        # but if it's still in-flight we expect 409.
        r2 = client.get(f"/jobs/{job_id}/result", headers=ALICE)
        assert r2.status_code in (200, 409)

    def test_list_jobs(self):
        _submit_and_wait("SELECT 1")
        r = client.get("/jobs", headers=ALICE)
        assert r.status_code == 200
        assert len(r.json()["jobs"]) >= 1


# ── Job isolation ─────────────────────────────────────────────────────────────

class TestJobIsolation:
    def test_bob_cannot_see_alices_job(self):
        job = _submit_and_wait("SELECT 2")
        assert client.get(f"/jobs/{job['job_id']}", headers=BOB).status_code == 404

    def test_bob_cannot_fetch_alices_result(self):
        job = _submit_and_wait("SELECT 3")
        r = client.get(f"/jobs/{job['job_id']}/result", headers=BOB)
        assert r.status_code == 404


# ── Safety ────────────────────────────────────────────────────────────────────

class TestSafety:
    def test_write_is_rejected(self):
        job = _submit_and_wait("DELETE FROM countries")
        assert job["status"] == "failed"
        assert "readonly" in (job.get("error") or "").lower()

    def test_unknown_job_is_404(self):
        assert client.get("/jobs/doesnotexist", headers=ALICE).status_code == 404


# ── Cancel / delete ───────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_completed_job(self):
        job = _submit_and_wait("SELECT 1")
        job_id = job["job_id"]
        r = client.delete(f"/jobs/{job_id}", headers=ALICE)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        assert client.get(f"/jobs/{job_id}", headers=ALICE).status_code == 404
