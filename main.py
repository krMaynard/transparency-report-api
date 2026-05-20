"""Demo SQL-over-HTTP API for researchers, with async job execution.

Long-running queries can't tie up the HTTP connection, so submitting a query
returns 202 + a job id immediately. The query runs on a background worker;
clients poll /jobs/{id} for status and fetch /jobs/{id}/result when done.

The database is opened read-only so DDL/DML are rejected by SQLite itself.
"""
import csv
import io
import os
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")
ROW_LIMIT = 100_000
WORKER_THREADS = 4
QUERY_TIMEOUT_SECONDS = 300

# Demo-only API keys. In production these would live in a secret store
# (Vault, AWS SM, etc.) and be loaded at startup, not committed to git.
# We deliberately use the researcher's name as the key so it's obvious
# this is a demo placeholder, not a credential.
API_KEYS: dict[str, dict[str, str]] = {
    "alice": {"name": "alice"},
    "bob": {"name": "bob"},
}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Depends(api_key_header)) -> dict[str, str]:
    if not key or key not in API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Set header `X-API-Key: <key>`.",
        )
    return {"key": key, **API_KEYS[key]}


JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]


@dataclass
class Job:
    id: str
    sql: str
    owner_key: str
    submitted_by: str
    status: JobStatus = "queued"
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    _conn: sqlite3.Connection | None = field(default=None, repr=False)

    def to_public(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "status": self.status,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "row_count": len(self.rows) if self.rows is not None else None,
            "status_url": f"/jobs/{self.id}",
            "result_url": f"/jobs/{self.id}/result" if self.status == "done" else None,
        }


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="sql-worker")

app = FastAPI(
    title="SQL Query Demo API (async jobs)",
    description="Submit a SQL query, get a job id, poll for results as JSON or CSV.",
    version="0.2.0",
)


class QueryRequest(BaseModel):
    sql: str = Field(..., description="A single SELECT statement.", min_length=1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_ro() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("demo.db not found — run `python seed.py` first.")
    return sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
        timeout=QUERY_TIMEOUT_SECONDS,
        check_same_thread=False,
    )


def _execute_job(job_id: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None or job.status == "cancelled":
            return
        job.status = "running"
        job.started_at = _now()

    try:
        conn = _connect_ro()
        with _jobs_lock:
            job._conn = conn

        try:
            cur = conn.execute(job.sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(ROW_LIMIT + 1)
        finally:
            with _jobs_lock:
                job._conn = None
            conn.close()

        if len(rows) > ROW_LIMIT:
            raise ValueError(f"Result exceeds {ROW_LIMIT} rows; add a LIMIT clause.")

        with _jobs_lock:
            if job.status == "cancelled":
                return
            job.columns = cols
            job.rows = [list(r) for r in rows]
            job.status = "done"
            job.finished_at = _now()
    except sqlite3.OperationalError as exc:
        with _jobs_lock:
            if job.status == "cancelled":
                return
            job.status = "failed"
            job.error = f"SQL error: {exc}"
            job.finished_at = _now()
    except Exception as exc:
        with _jobs_lock:
            if job.status == "cancelled":
                return
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.finished_at = _now()


def _job_for_owner(job_id: str, owner_key: str) -> Job:
    """Look up a job and 404 if it isn't owned by this caller.

    We return 404 (not 403) for foreign jobs so the API doesn't leak the
    existence of other researchers' job ids.
    """
    job = _jobs.get(job_id)
    if job is None or job.owner_key != owner_key:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "SQL Query Demo API",
        "pattern": "async-job",
        "auth": "X-API-Key header required for all endpoints except `/`, `/docs`, `/openapi.json`",
        "endpoints": {
            "POST /query": "Submit a SQL query, returns 202 + job_id",
            "GET /jobs": "List your jobs",
            "GET /jobs/{job_id}": "Job status (your jobs only)",
            "GET /jobs/{job_id}/result?format=json|csv": "Result (only when status=done)",
            "DELETE /jobs/{job_id}": "Cancel a queued/running job, or remove a finished one",
            "GET /tables": "List tables in the demo database",
            "GET /schema/{table}": "Show columns for a table",
            "GET /docs": "Interactive Swagger UI",
        },
        "row_limit": ROW_LIMIT,
        "worker_threads": WORKER_THREADS,
    }


@app.get("/tables")
def list_tables(_: dict = Depends(require_api_key)) -> dict[str, list[str]]:
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return {"tables": [r[0] for r in rows]}


@app.get("/schema/{table}")
def table_schema(
    table: str, _: dict = Depends(require_api_key)
) -> dict[str, Any]:
    if not table.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name.")
    with _connect_ro() as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Table '{table}' not found.")
    return {
        "table": table,
        "columns": [
            {"name": r[1], "type": r[2], "notnull": bool(r[3]), "pk": bool(r[5])}
            for r in rows
        ],
    }


@app.post("/query", status_code=202)
def submit_query(
    body: QueryRequest,
    response: Response,
    principal: dict = Depends(require_api_key),
) -> dict[str, Any]:
    job = Job(
        id=uuid.uuid4().hex,
        sql=body.sql,
        owner_key=principal["key"],
        submitted_by=principal["name"],
    )
    with _jobs_lock:
        _jobs[job.id] = job
    _executor.submit(_execute_job, job.id)
    response.headers["Location"] = f"/jobs/{job.id}"
    return job.to_public()


@app.get("/jobs")
def list_jobs(
    limit: int = 50, principal: dict = Depends(require_api_key)
) -> dict[str, Any]:
    with _jobs_lock:
        mine = [j for j in _jobs.values() if j.owner_key == principal["key"]]
        items = sorted(mine, key=lambda j: j.submitted_at, reverse=True)[:limit]
        return {"jobs": [j.to_public() for j in items]}


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str, principal: dict = Depends(require_api_key)
) -> dict[str, Any]:
    with _jobs_lock:
        return _job_for_owner(job_id, principal["key"]).to_public()


@app.get("/jobs/{job_id}/result", response_model=None)
def get_job_result(
    job_id: str,
    format: Literal["json", "csv"] = "json",
    principal: dict = Depends(require_api_key),
) -> JSONResponse | PlainTextResponse:
    with _jobs_lock:
        job = _job_for_owner(job_id, principal["key"])
        if job.status != "done":
            raise HTTPException(
                status_code=409,
                detail=f"Job not ready (status={job.status}). Poll {job.id} again.",
            )
        cols = job.columns or []
        rows = job.rows or []

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(cols)
        writer.writerows(rows)
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
        )
    return JSONResponse({"columns": cols, "rows": rows, "row_count": len(rows)})


@app.delete("/jobs/{job_id}")
def cancel_job(
    job_id: str, principal: dict = Depends(require_api_key)
) -> dict[str, Any]:
    with _jobs_lock:
        job = _job_for_owner(job_id, principal["key"])
        prior = job.status
        if job.status in ("queued", "running"):
            job.status = "cancelled"
            job.finished_at = _now()
            if job._conn is not None:
                # interrupt() is safe to call from another thread; it asks the
                # SQLite engine to abort the in-flight query.
                try:
                    job._conn.interrupt()
                except sqlite3.Error:
                    pass
        del _jobs[job_id]
    return {"job_id": job_id, "previous_status": prior, "deleted": True}
