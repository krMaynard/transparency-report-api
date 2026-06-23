"""Native MCP (Model Context Protocol) stdio server for the DSA VLOP transparency API.

Exposes the transparency-report-api's public, no-SQL query interface to MCP
clients (Claude Desktop, Claude Code, any MCP host) as a small set of tools, so
an agent can explore the EU DSA VLOP transparency dataset directly.

It is a **thin MCP front end over the running HTTP API**: every tool maps to a
real endpoint, so all queries pass through the exact same `compile_query` trust
boundary as the web service — no SQL is ever accepted, every field/operation is
validated against the table registry, and all values are bound as parameters.

The server deliberately does **not** import the FastAPI app. It talks to the API
over HTTP, so it has a tiny dependency footprint (`mcp` + `httpx`) and never
needs the SQLite DB, the dataset, or the app's heavier dependencies — which also
keeps it clear of the app's `fastapi`/`starlette` version pins. Point it at a
running server with `TRANSPARENCY_API_URL`.

Configuration (environment variables):
  TRANSPARENCY_API_URL      Base URL of the API (default http://127.0.0.1:8000)
  TRANSPARENCY_API_KEY      Optional X-API-Key. When set, the keyed tools
                            (`describe_table`, `ask`) use the authenticated
                            endpoints; without it the server runs against the
                            public surface only.
  TRANSPARENCY_API_TIMEOUT  Per-request timeout in seconds (default 30)

Run (stdio transport):
  pip install -r requirements-mcp.txt
  python mcp_server.py

Register with an MCP host (e.g. Claude Desktop) — see docs/MCP.md.
"""

from __future__ import annotations

import os
import threading
from typing import Any

import httpx

SERVER_NAME = "transparency-report-api"

# `... or default` (not getenv's default arg) so an explicitly empty value
# (e.g. `TRANSPARENCY_API_URL=`) falls back instead of becoming "".
API_URL = (os.getenv("TRANSPARENCY_API_URL") or "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("TRANSPARENCY_API_KEY") or None
try:
    API_TIMEOUT = float(os.getenv("TRANSPARENCY_API_TIMEOUT") or "30")
except ValueError:
    API_TIMEOUT = 30.0

# Lazily-built shared HTTP client. Tests inject their own (e.g. an ASGI transport
# bound to the app) by assigning to this module global before calling a tool.
_session: httpx.Client | None = None
_session_lock = threading.Lock()


def _client() -> httpx.Client:
    global _session
    # Double-checked locking: tools may run on concurrent threads, so guard the
    # one-time client build to avoid creating orphaned, unclosed clients.
    if _session is None:
        with _session_lock:
            if _session is None:
                headers = {"X-API-Key": API_KEY} if API_KEY else {}
                _session = httpx.Client(base_url=API_URL, headers=headers, timeout=API_TIMEOUT)
    return _session


class ApiError(RuntimeError):
    """An error returned by the HTTP API, surfaced to the MCP client."""


def _request(method: str, path: str, **kwargs: Any) -> Any:
    """Call the API and return parsed JSON, or raise ApiError with the server's
    detail message so the MCP client sees a useful error instead of a stack trace."""
    try:
        resp = _client().request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise ApiError(
            f"Could not reach the transparency API at {API_URL} "
            f"({type(exc).__name__}: {exc}). Is the server running? "
            "Set TRANSPARENCY_API_URL to point at it."
        ) from exc
    if resp.status_code >= 400:
        detail: Any
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise ApiError(f"API {method} {path} failed ({resp.status_code}): {detail}")
    # A 2xx with a non-JSON body (empty response, or an HTML error page injected
    # by a proxy/gateway) would otherwise surface as a raw traceback.
    try:
        return resp.json()
    except ValueError as exc:
        raise ApiError(
            f"API {method} {path} returned invalid JSON "
            f"(status {resp.status_code}): {resp.text[:200]}"
        ) from exc


# ── Tool implementations ─────────────────────────────────────────────
#
# Plain functions (no MCP dependency) so they can be unit-tested directly against
# the app via an httpx ASGI transport. build_server() registers them as tools.


def list_tables() -> dict[str, Any]:
    """List the queryable DSA report tables with their dimensions, measures, and
    the available aggregate functions and composite-query options.

    Start here to discover what can be queried. Returns the same metadata the
    dashboard's query builder uses (public endpoint, no API key required)."""
    return _request("GET", "/api/explore/options")


def describe_table(table: str) -> dict[str, Any]:
    """Describe one DSA report table: its dimensions and measures, the operations
    valid on each, and a runnable example query.

    `table` is one of the names from `list_tables` (e.g. "t4_notices"). With an
    API key configured the full field registry is returned; otherwise the
    dimensions/measures from the public discovery endpoint are returned."""
    if API_KEY:
        return _request("GET", f"/api/schema/{table}")
    options = _request("GET", "/api/explore/options")
    for entry in options.get("tables", []):
        if entry.get("table") == table:
            return entry
    known = ", ".join(e.get("table", "?") for e in options.get("tables", []))
    raise ApiError(f"Unknown table '{table}'. Available tables: {known}")


def dataset_overview() -> dict[str, Any]:
    """Headline aggregates for the whole dataset: reporting period, number of
    services and platforms, total Article 16 notices, and the top platforms and
    content categories by notice volume. Public endpoint, no API key required."""
    return _request("GET", "/api/overview")


def run_query(query: dict[str, Any]) -> dict[str, Any]:
    """Run a structured (no-SQL) query and return the results synchronously.

    `query` is the structured query object (NOT SQL). Single-table shape:
        {
          "table": "t4_notices",
          "query": {"and": [{"operation": "EQ",
                             "field_name": "platform",
                             "field_values": ["Meta"]}]},
          "group_by": ["service_name"],
          "aggregates": [{"function": "SUM", "field_name": "notices",
                          "alias": "total_notices"}],
          "sort": [{"field_name": "total_notices", "order": "desc"}],
          "max_count": 20
        }
    Composite (cross-table) shape: provide `legs` (named single-table sub-queries),
    `join_on`, `derived`, and `having` instead of `table`. Use `list_tables` /
    `describe_table` to discover valid fields.

    Every field and operation is validated server-side against the table registry
    and all values are bound as parameters — invalid fields raise an error. The
    result is row-capped (this runs the public, bounded query path) and returns
    {columns, rows, row_count, truncated}."""
    return _request("POST", "/api/explore", json=query)


def ask(question: str) -> dict[str, Any]:
    """Ask a natural-language question about the DSA VLOP data; an LLM translates
    it into a structured query that runs through the same validation as
    `run_query` (it never produces SQL). Returns the generated structured query
    alongside the results.

    Requires `TRANSPARENCY_API_KEY` (the /api/ask endpoint is authenticated) and
    the server must have natural-language queries enabled (ANTHROPIC_API_KEY)."""
    if not API_KEY:
        raise ApiError(
            "ask requires TRANSPARENCY_API_KEY — the /api/ask endpoint is "
            "authenticated. Use run_query for unauthenticated structured queries."
        )
    return _request("POST", "/api/ask", json={"question": question})


def register(name: str, email: str) -> dict[str, Any]:
    """Register for a demo API key via the researcher portal (no sign-in needed).

    Calls POST /api/portal/register (public endpoint; gated by ALLOW_DEMO_KEYS on
    the server, which defaults to on). Returns {"api_key": "...", "expires_at": "..."}.
    Once you have the key, set TRANSPARENCY_API_KEY in the MCP server config to
    unlock `submit_query`, `poll_job`, `ask`, and the full `describe_table`."""
    return _request("POST", "/api/portal/register", json={"name": name, "email": email})


def submit_query(query: dict[str, Any]) -> dict[str, Any]:
    """Submit a structured (no-SQL) query to the async job queue.

    Returns immediately with a job_id — use `poll_job` to wait for the result.
    This is the full, unrestricted query path (POST /api/query): no row cap,
    up to 4 composite legs, and CSV export available. Requires TRANSPARENCY_API_KEY
    (call `register` first if you don't have one).

    `query` is the same structured object accepted by `run_query`. Example:
        {
          "table": "t4_notices",
          "query": {"and": [{"operation": "EQ", "field_name": "platform",
                             "field_values": ["Meta"]}]},
          "group_by": ["service_name"],
          "aggregates": [{"function": "SUM", "field_name": "notices",
                          "alias": "total_notices"}],
          "sort": [{"field_name": "total_notices", "order": "desc"}],
          "max_count": 1000
        }
    Returns {job_id, status, status_url, …}. Pass job_id to `poll_job`."""
    if not API_KEY:
        raise ApiError(
            "submit_query requires TRANSPARENCY_API_KEY — POST /api/query is "
            "authenticated. Call register() to get a demo key, or use run_query "
            "for the public bounded query path."
        )
    return _request("POST", "/api/query", json=query)


def poll_job(job_id: str, timeout: float = 60.0) -> dict[str, Any]:
    """Poll a submitted job until it completes, then return its result rows.

    `job_id` is the value returned by `submit_query`. `timeout` is the maximum
    number of seconds to wait (default 60). On success returns
    {columns, rows, row_count, truncated}. Raises ApiError if the job fails or
    the timeout expires. Requires TRANSPARENCY_API_KEY."""
    import time

    if not API_KEY:
        raise ApiError(
            "poll_job requires TRANSPARENCY_API_KEY — /api/jobs/* is authenticated."
        )
    deadline = time.monotonic() + timeout
    delay = 0.5
    while True:
        status = _request("GET", f"/api/jobs/{job_id}")
        job_status = status.get("status")
        if job_status == "done":
            return _request("GET", f"/api/jobs/{job_id}/result")
        if job_status == "failed":
            raise ApiError(
                f"Job {job_id} failed: {status.get('error', 'unknown error')}"
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ApiError(
                f"Timed out waiting for job {job_id} after {timeout:.0f}s "
                f"(current status: {job_status!r})"
            )
        time.sleep(min(delay, remaining))
        delay = min(delay * 1.5, 5.0)


# ── MCP server wiring ────────────────────────────────────────────


def build_server() -> Any:
    """Build the FastMCP server with the tools registered. `mcp` is imported here
    (not at module top) so the tool functions above stay importable for tests
    without the MCP SDK installed."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(SERVER_NAME)
    for fn in (
        list_tables, describe_table, dataset_overview, run_query, ask,
        register, submit_query, poll_job,
    ):
        server.add_tool(fn)
    return server


def main() -> None:
    build_server().run()  # stdio transport by default


if __name__ == "__main__":
    main()
