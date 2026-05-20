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

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")
ROW_LIMIT = 100_000
WORKER_THREADS = 4
QUERY_TIMEOUT_SECONDS = 300

JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]


@dataclass
class Job:
    id: str
    sql: str
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


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "SQL Query Demo API",
        "pattern": "async-job",
        "endpoints": {
            "POST /query": "Submit a SQL query, returns 202 + job_id",
            "GET /jobs": "List recent jobs",
            "GET /jobs/{job_id}": "Job status",
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
def list_tables() -> dict[str, list[str]]:
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return {"tables": [r[0] for r in rows]}


@app.get("/schema/{table}")
def table_schema(table: str) -> dict[str, Any]:
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
def submit_query(body: QueryRequest, response: Response) -> dict[str, Any]:
    job = Job(id=uuid.uuid4().hex, sql=body.sql)
    with _jobs_lock:
        _jobs[job.id] = job
    _executor.submit(_execute_job, job.id)
    response.headers["Location"] = f"/jobs/{job.id}"
    return job.to_public()


@app.get("/jobs")
def list_jobs(limit: int = 50) -> dict[str, Any]:
    with _jobs_lock:
        items = sorted(_jobs.values(), key=lambda j: j.submitted_at, reverse=True)[:limit]
        return {"jobs": [j.to_public() for j in items]}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job.to_public()


@app.get("/jobs/{job_id}/result", response_model=None)
def get_job_result(
    job_id: str, format: Literal["json", "csv"] = "json"
) -> JSONResponse | PlainTextResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
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
def cancel_job(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
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
        # Either way, drop the job from the table.
        del _jobs[job_id]
    return {"job_id": job_id, "previous_status": prior, "deleted": True}
