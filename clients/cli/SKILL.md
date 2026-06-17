---
name: pp-dsa-research
description: "Printing Press CLI for Dsa Research. Query the aggregated EU Digital Services Act VLOP transparency reports (tables 3–11) with structured parameters (no SQL)"
author: "Kieran Maynard"
license: "Apache-2.0"
argument-hint: "<command> [args] | install cli|mcp"
allowed-tools: "Read Bash"
metadata:
  openclaw:
    requires:
      bins:
        - dsa-research-pp-cli
---

# Dsa Research — Printing Press CLI

## Prerequisites: Install the CLI

This skill drives the `dsa-research-pp-cli` binary. **You must verify the CLI is installed before invoking any command from this skill.** If it is missing, install it first:

1. Install via the Printing Press installer. It defaults binaries to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows:
   ```bash
   npx -y @mvanhorn/printing-press-library install dsa-research --cli-only
   ```
2. Verify: `dsa-research-pp-cli --version`
3. Ensure the reported install directory is on `$PATH` for the agent/runtime that will invoke this skill.

If the `npx` install fails before this CLI has a public-library category, install Node or use the category-specific Go fallback after publish.

If `--version` reports "command not found" after install, the runtime cannot see the binary directory on `$PATH`. Do not proceed with skill commands until verification succeeds.

Query the aggregated EU Digital Services Act VLOP transparency reports (tables 3–11) with structured parameters (no SQL). Pick a `table` (GET /tables), describe filters/group_by/aggregates, get a job id, then poll for results as JSON or CSV. Query syntax follows the TikTok Research API: boolean and/or/not clauses of {operation, field_name, field_values}.

## Command Reference

**admin** — Manage admin

- `dsa-research-pp-cli admin approve-registration` — Restore (or pre-create) an approved account — e.g. to undo a revoke.
- `dsa-research-pp-cli admin list-registrations` — List researcher registrations, optionally filtered by status.
- `dsa-research-pp-cli admin revoke-registration` — Revoke an account's access (its live sessions stop working immediately).

**ask** — Manage ask

- `dsa-research-pp-cli ask` — Authenticated natural-language query: an LLM translates the question into the *structured* QueryRequest (never SQL)

**dsa-vlop-transparency-api** — Manage dsa vlop transparency api

- `dsa-research-pp-cli dsa-vlop-transparency-api` — Root

**dsa-vlop-transparency-auth** — Manage dsa vlop transparency auth

- `dsa-research-pp-cli dsa-vlop-transparency-auth` — Auth Google

**dsa-vlop-transparency-jobs** — Manage dsa vlop transparency jobs

- `dsa-research-pp-cli dsa-vlop-transparency-jobs cancel` — Cancel Job
- `dsa-research-pp-cli dsa-vlop-transparency-jobs get` — Get Job
- `dsa-research-pp-cli dsa-vlop-transparency-jobs list` — List Jobs

**dsa-vlop-transparency-version** — Manage dsa vlop transparency version

- `dsa-research-pp-cli dsa-vlop-transparency-version` — The deployed build (commit SHA on Cloud Run, else 'dev') + app version.

**explore** — Manage explore

- `dsa-research-pp-cli explore explore` — Public, synchronous, bounded query for the interactive dashboard.
- `dsa-research-pp-cli explore options` — Public metadata for the dashboard's query builder: each table's queryable dimensions and measures

**fields** — Manage fields

- `dsa-research-pp-cli fields` — Fields for a report table (`?table=…`), or an overview of all tables.

**healthz** — Manage healthz

- `dsa-research-pp-cli healthz` — Health

**metrics** — Manage metrics

- `dsa-research-pp-cli metrics` — Prometheus metrics. No auth — scrape over an internal network only.

**overview** — Manage overview

- `dsa-research-pp-cli overview` — Public headline aggregates for the dashboard — no auth.

**portal** — Manage portal

- `dsa-research-pp-cli portal page` — Serve the researcher portal single-page app.
- `dsa-research-pp-cli portal register` — Issue a demo API key for a researcher (no real authentication).
- `dsa-research-pp-cli portal revoke-key` — Revoke the calling key/session (configured demo keys can't be revoked).

**query** — Manage query

- `dsa-research-pp-cli query` — Submit Query

**readyz** — Manage readyz

- `dsa-research-pp-cli readyz` — Ready

**schema** — Manage schema

- `dsa-research-pp-cli schema <table>` — The queryable field registry (dimensions + measures) for a report table.

**static** — Manage static

- `dsa-research-pp-cli static <filename>` — Serve a vendored third-party asset (e.g. Chart.js) from static/vendor.

**tables** — Manage tables

- `dsa-research-pp-cli tables` — The queryable DSA report tables and the dataset's reporting period.


### Finding the right command

When you know what you want to do but not which command does it, ask the CLI directly:

```bash
dsa-research-pp-cli which "<capability in your own words>"
```

`which` resolves a natural-language capability query to the best matching command from this CLI's curated feature index. Exit code `0` means at least one match; exit code `2` means no confident match — fall back to `--help` or use a narrower query.

## Auth Setup
Run `dsa-research-pp-cli auth setup` to print the URL and steps for getting a key (add `--launch` to open the URL). Then set:

```bash
export DSA_RESEARCH_APIKEY_HEADER="<your-key>"
```

Or persist it in `~/.config/dsa-vlop-transparency-pp-cli/config.toml`.

Run `dsa-research-pp-cli doctor` to verify setup.

## Agent Mode

Add `--agent` to any command. Expands to: `--json --compact --no-input --no-color --yes`.

- **Pipeable** — JSON on stdout, errors on stderr
- **Filterable** — `--select` keeps a subset of fields. Dotted paths descend into nested structures; arrays traverse element-wise. Critical for keeping context small on verbose APIs:

  ```bash
  dsa-research-pp-cli dsa-vlop-transparency-jobs list --agent --select id,name,status
  ```
- **Previewable** — `--dry-run` shows the request without sending
- **Offline-friendly** — sync/search commands can use the local SQLite store when available
- **Non-interactive** — never prompts, every input is a flag
- **Explicit retries** — use `--idempotent` only when an already-existing create should count as success, and `--ignore-missing` only when a missing delete target should count as success

### Response envelope

Commands that read from the local store or the API wrap output in a provenance envelope:

```json
{
  "meta": {"source": "live" | "local", "synced_at": "...", "reason": "..."},
  "results": <data>
}
```

Parse `.results` for data and `.meta.source` to know whether it's live or local. A human-readable `N results (live)` summary is printed to stderr only when stdout is a terminal AND no machine-format flag (`--json`, `--csv`, `--compact`, `--quiet`, `--plain`, `--select`) is set — piped/agent consumers and explicit-format runs get pure JSON on stdout.

## Agent Feedback

When you (or the agent) notice something off about this CLI, record it:

```
dsa-research-pp-cli feedback "the --since flag is inclusive but docs say exclusive"
dsa-research-pp-cli feedback --stdin < notes.txt
dsa-research-pp-cli feedback list --json --limit 10
```

Entries are stored locally at `~/.local/share/dsa-research-pp-cli/feedback.jsonl`. They are never POSTed unless `DSA_RESEARCH_FEEDBACK_ENDPOINT` is set AND either `--send` is passed or `DSA_RESEARCH_FEEDBACK_AUTO_SEND=true`. Default behavior is local-only.

Write what *surprised* you, not a bug report. Short, specific, one line: that is the part that compounds.

## Output Delivery

Every command accepts `--deliver <sink>`. The output goes to the named sink in addition to (or instead of) stdout, so agents can route command results without hand-piping. Three sinks are supported:

| Sink | Effect |
|------|--------|
| `stdout` | Default; write to stdout only |
| `file:<path>` | Atomically write output to `<path>` (tmp + rename) |
| `webhook:<url>` | POST the output body to the URL (`application/json` or `application/x-ndjson` when `--compact`) |

Unknown schemes are refused with a structured error naming the supported set. Webhook failures return non-zero and log the URL + HTTP status on stderr.

## Named Profiles

A profile is a saved set of flag values, reused across invocations. Use it when a scheduled agent calls the same command every run with the same configuration - HeyGen's "Beacon" pattern.

```
dsa-research-pp-cli profile save briefing --json
dsa-research-pp-cli --profile briefing dsa-vlop-transparency-jobs list
dsa-research-pp-cli profile list --json
dsa-research-pp-cli profile show briefing
dsa-research-pp-cli profile delete briefing --yes
```

Explicit flags always win over profile values; profile values win over defaults. `agent-context` lists all available profiles under `available_profiles` so introspecting agents discover them at runtime.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (wrong arguments) |
| 3 | Resource not found |
| 4 | Authentication required |
| 5 | API error (upstream issue) |
| 7 | Rate limited (wait and retry) |
| 10 | Config error |

## Argument Parsing

Parse `$ARGUMENTS`:

1. **Empty, `help`, or `--help`** → show `dsa-research-pp-cli --help` output
2. **Starts with `install`** → ends with `mcp` → MCP installation; otherwise → see Prerequisites above
3. **Anything else** → Direct Use (execute as CLI command with `--agent`)

## MCP Server Installation

Install the MCP binary from this CLI's published public-library entry or pre-built release, then register it:

```bash
claude mcp add dsa-research-pp-mcp -- dsa-research-pp-mcp
```

Verify: `claude mcp list`

## Direct Use

1. Check if installed: `which dsa-research-pp-cli`
   If not found, offer to install (see Prerequisites at the top of this skill).
2. Match the user query to the best command from the Unique Capabilities and Command Reference above.
3. Execute with the `--agent` flag:
   ```bash
   dsa-research-pp-cli <command> [subcommand] [args] --agent
   ```
4. If ambiguous, drill into subcommand help: `dsa-research-pp-cli <command> --help`.
