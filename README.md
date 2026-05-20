# api-demo

A small FastAPI service that lets a researcher submit a SQL query, runs it
asynchronously on a worker thread, and serves the results back as JSON or CSV.
Backed by a read-only SQLite database seeded from the **Google Government
Content Removals** dataset (`../krMaynard.github.io/data/google-government-removals.json`).

## Why an async job pattern?

A SQL query against a large dataset can take seconds or minutes. If the API
held the HTTP connection open the whole time, slow queries would tie up
workers, time out at intermediate proxies, and stall the service.

So `POST /query` does **not** return rows. It returns `202 Accepted` plus a
`job_id` immediately, runs the query on a background worker, and the client
polls `/jobs/{job_id}` until it sees `status="done"`. Then it fetches
`/jobs/{job_id}/result?format=json|csv`.

```
client                          server
  │                               │
  │── POST /query ───────────────▶│   enqueue
  │◀── 202 + {job_id, status_url} │
  │                               │   ┌─ worker thread
  │                               │   │   open ro conn
  │── GET /jobs/{id} ────────────▶│   │   execute SQL
  │◀── {status: running}          │   │   buffer rows
  │── GET /jobs/{id} ────────────▶│   │
  │◀── {status: done, result_url} │◀──┘
  │── GET /jobs/{id}/result ─────▶│
  │◀── rows (json or csv)         │
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                     # builds demo.db from the JSON dataset
uvicorn main:app --reload          # http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000/docs> for the interactive Swagger UI.

## Endpoints

| Method | Path                                | Description                                    |
|--------|-------------------------------------|------------------------------------------------|
| GET    | `/`                                 | Service info                                   |
| GET    | `/tables`                           | List tables                                    |
| GET    | `/schema/{table}`                   | Show a table's columns                         |
| POST   | `/query`                            | Submit a SQL query — returns `202 + job_id`    |
| GET    | `/jobs`                             | List recent jobs                               |
| GET    | `/jobs/{job_id}`                    | Job status                                     |
| GET    | `/jobs/{job_id}/result?format=…`    | Result rows (only when `status=done`)          |
| DELETE | `/jobs/{job_id}`                    | Cancel a running job, or remove a finished one |

## Example

Submit a query:

```bash
curl -i -X POST 'http://127.0.0.1:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"sql": "SELECT c.name, SUM(r.items_requested) AS items FROM removals r JOIN countries c ON c.id = r.country_id GROUP BY c.name ORDER BY items DESC LIMIT 5"}'
# HTTP/1.1 202 Accepted
# Location: /jobs/c7be1dc4894c4f4e84688847c5d829de
# {"job_id":"c7be1dc4894c4f4e84688847c5d829de","status":"running",...}
```

Poll until done:

```bash
curl http://127.0.0.1:8000/jobs/c7be1dc4894c4f4e84688847c5d829de
# {"status":"done","row_count":5,"result_url":"/jobs/.../result", ...}
```

Fetch the result:

```bash
curl 'http://127.0.0.1:8000/jobs/c7be1dc4894c4f4e84688847c5d829de/result?format=json'
curl 'http://127.0.0.1:8000/jobs/c7be1dc4894c4f4e84688847c5d829de/result?format=csv' -o russia.csv
```

## Job statuses

- `queued` — accepted, waiting for a worker
- `running` — a worker is executing the SQL
- `done` — finished successfully; result available at `/jobs/{id}/result`
- `failed` — SQL or row-limit error; see `error` field
- `cancelled` — client called `DELETE /jobs/{id}` before completion

`DELETE` while running calls SQLite's `interrupt()` to abort the in-flight
query, then drops the job from the registry.

## Schema (Google Government Content Removals)

Star schema — one fact table plus five small dimension tables:

- `removals(period_id, country_id, requestor_id, product_id, reason_id, num_requests, items_requested, removed_legal, removed_policy, not_found, not_enough_info, no_action, already_removed)`
- `periods(id, label)` — e.g. "January - June 2024"
- `countries(id, code, name)` — ISO code + display name
- `requestors(id, name)` — Court Order, Police, Government Officials, …
- `products(id, name)` — YouTube, Web Search, Maps, …
- `reasons(id, name)` — Defamation, National security, Privacy, …

## Sample queries

```sql
-- Top 10 countries by items requested for removal
SELECT c.name, SUM(r.items_requested) AS items
FROM removals r JOIN countries c ON c.id = r.country_id
GROUP BY c.name ORDER BY items DESC LIMIT 10;

-- Defamation requests by product
SELECT p.name AS product, SUM(r.num_requests) AS requests
FROM removals r
JOIN products p ON p.id = r.product_id
JOIN reasons rn ON rn.id = r.reason_id
WHERE rn.name = 'Defamation'
GROUP BY p.name ORDER BY requests DESC;

-- Trend of EU items requested over time
SELECT pr.label, SUM(r.items_requested) AS items
FROM removals r
JOIN periods pr ON pr.id = r.period_id
JOIN countries c ON c.id = r.country_id
WHERE c.code IN ('DE','FR','IT','ES','PL','NL','BE','SE','AT','IE')
GROUP BY pr.label ORDER BY pr.id;
```

## Safety notes

- The DB is opened with `mode=ro`, so any `INSERT`/`UPDATE`/`DELETE`/`DROP`
  surfaces as `status=failed` with a `readonly database` error — no SQL
  parsing required.
- Per-job results are capped at 100,000 rows; over that the job fails and the
  client is asked to add a `LIMIT`.
- Jobs and their result rows live in process memory. Restart = clear.
- This is a **demo**. Production would need: persistent job storage, auth,
  per-user quotas, query allow-listing or row-level filtering, and result
  pagination/streaming for large outputs.
