# Dsa Research CLI

Query the aggregated EU Digital Services Act VLOP transparency reports (tables 3–11) with structured parameters (no SQL). Pick a `table` (GET /tables), describe filters/group_by/aggregates, get a job id, then poll for results as JSON or CSV. Query syntax follows the TikTok Research API: boolean and/or/not clauses of {operation, field_name, field_values}.

## Install

The recommended path installs both the `dsa-research-pp-cli` binary and the `pp-dsa-research` agent skill (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, and other agents supported by the upstream [`skills`](https://github.com/vercel-labs/skills) CLI) in one shot:

```bash
npx -y @mvanhorn/printing-press-library install dsa-research
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press-library install dsa-research --cli-only
```

For skill only — installs the skill into the same agents as the default command above, but skips the CLI binary (use this to update or reinstall just the skill):

```bash
npx -y @mvanhorn/printing-press-library install dsa-research --skill-only
```

To constrain the skill install to one or more specific agents (repeatable — agent names match the [`skills`](https://github.com/vercel-labs/skills) CLI):

```bash
npx -y @mvanhorn/printing-press-library install dsa-research --agent claude-code
npx -y @mvanhorn/printing-press-library install dsa-research --agent claude-code --agent codex
```

### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/dsa-research-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

Install the CLI binary first. The installer writes binaries to a per-user managed bin directory by default: `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows.

```bash
npx -y @mvanhorn/printing-press-library install dsa-research --cli-only
```

Then install the focused Hermes skill.

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-dsa-research --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-dsa-research --force
```

Restart the Hermes session or gateway if the newly installed skill is not visible immediately.

## Install for OpenClaw
Install both the CLI binary and the focused OpenClaw skill. The installer defaults binaries to a per-user bin directory (`$HOME/.local/bin` on macOS/Linux, `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows):

```bash
npx -y @mvanhorn/printing-press-library install dsa-research --agent openclaw
```

Restart the OpenClaw session or gateway if the newly installed skill is not visible immediately.

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/dsa-research-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.
3. Fill in `DSA_RESEARCH_APIKEY_HEADER` when Claude Desktop prompts you.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dsa-research": {
      "command": "dsa-research-pp-mcp",
      "env": {
        "DSA_RESEARCH_APIKEY_HEADER": "<your-key>"
      }
    }
  }
}
```

</details>

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Set Up Credentials

Get your API key from your API provider's developer portal. The key typically looks like a long alphanumeric string.

```bash
export DSA_RESEARCH_APIKEY_HEADER="<paste-your-key>"
```

You can also persist this in your config file at `~/.config/dsa-vlop-transparency-pp-cli/config.toml`.

### 3. Verify Setup

```bash
dsa-research-pp-cli doctor
```

This checks your configuration and credentials.

### 4. Try Your First Command

```bash
dsa-research-pp-cli dsa-vlop-transparency-jobs list
```

## Usage

Run `dsa-research-pp-cli --help` for the full command reference and flag list.

## Commands

### admin

Manage admin

- **`dsa-research-pp-cli admin approve-registration`** - Restore (or pre-create) an approved account — e.g. to undo a revoke.
- **`dsa-research-pp-cli admin list-registrations`** - List researcher registrations, optionally filtered by status.
- **`dsa-research-pp-cli admin revoke-registration`** - Revoke an account's access (its live sessions stop working immediately).

### ask

Manage ask

- **`dsa-research-pp-cli ask`** - Authenticated natural-language query: an LLM translates the question into the
*structured* QueryRequest (never SQL), which is then run through the exact same
compile_query trust boundary as /api/explore. The model only proposes — a bad
field is a 400, and no model-authored SQL can reach the database.

Requires an API key (sign in to get one) — LLM calls cost money, so this is
gated and rate-limited per key. Disabled (503) unless ANTHROPIC_API_KEY is set.

### dsa-vlop-transparency-api

Manage dsa vlop transparency api

- **`dsa-research-pp-cli dsa-vlop-transparency-api`** - Root

### dsa-vlop-transparency-auth

Manage dsa vlop transparency auth

- **`dsa-research-pp-cli dsa-vlop-transparency-auth`** - Auth Google

### dsa-vlop-transparency-jobs

Manage dsa vlop transparency jobs

- **`dsa-research-pp-cli dsa-vlop-transparency-jobs cancel`** - Cancel Job
- **`dsa-research-pp-cli dsa-vlop-transparency-jobs get`** - Get Job
- **`dsa-research-pp-cli dsa-vlop-transparency-jobs list`** - List Jobs

### dsa-vlop-transparency-version

Manage dsa vlop transparency version

- **`dsa-research-pp-cli dsa-vlop-transparency-version`** - The deployed build (commit SHA on Cloud Run, else "dev") + app version.

### explore

Manage explore

- **`dsa-research-pp-cli explore explore`** - Public, synchronous, bounded query for the interactive dashboard.

Same validated structured-query model as POST /api/query (no SQL is ever
accepted; every field/operation is checked against the table registry and all
values are bound), but it runs inline and hard-caps the row count — no auth,
no job, no webhook. IP-rate-limited so the open endpoint can't be hammered.
- **`dsa-research-pp-cli explore options`** - Public metadata for the dashboard's query builder: each table's queryable
dimensions and measures, from the fixed registry (no DB, no secrets).

### fields

Manage fields

- **`dsa-research-pp-cli fields`** - Fields for a report table (`?table=…`), or an overview of all tables.

### healthz

Manage healthz

- **`dsa-research-pp-cli healthz`** - Health

### metrics

Manage metrics

- **`dsa-research-pp-cli metrics`** - Prometheus metrics. No auth — scrape over an internal network only.

### overview

Manage overview

- **`dsa-research-pp-cli overview`** - Public headline aggregates for the dashboard — no auth. Memoised: the
read-only DB is static, so we compute the fixed queries once (no user input
reaches SQL) and serve from memory thereafter.

### portal

Manage portal

- **`dsa-research-pp-cli portal page`** - Serve the researcher portal single-page app.
- **`dsa-research-pp-cli portal register`** - Issue a demo API key for a researcher (no real authentication).
- **`dsa-research-pp-cli portal revoke-key`** - Revoke the calling key/session (configured demo keys can't be revoked).

### query

Manage query

- **`dsa-research-pp-cli query`** - Submit Query

### readyz

Manage readyz

- **`dsa-research-pp-cli readyz`** - Ready

### schema

Manage schema

- **`dsa-research-pp-cli schema <table>`** - The queryable field registry (dimensions + measures) for a report table.

### static

Manage static

- **`dsa-research-pp-cli static <filename>`** - Serve a vendored third-party asset (e.g. Chart.js) from static/vendor.

### tables

Manage tables

- **`dsa-research-pp-cli tables`** - The queryable DSA report tables and the dataset's reporting period.


## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
dsa-research-pp-cli dsa-vlop-transparency-jobs list

# JSON for scripting and agents
dsa-research-pp-cli dsa-vlop-transparency-jobs list --json

# Filter to specific fields
dsa-research-pp-cli dsa-vlop-transparency-jobs list --json --select id,name,status

# Dry run — show the request without sending
dsa-research-pp-cli dsa-vlop-transparency-jobs list --dry-run

# Agent mode — JSON + compact + no prompts in one flag
dsa-research-pp-cli dsa-vlop-transparency-jobs list --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select id,name` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries and `--ignore-missing` to delete retries when a no-op success is acceptable
- **Confirmable** - `--yes` for explicit confirmation of destructive actions
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Offline-friendly** - sync/search commands can use the local SQLite store when available
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `4` auth error, `5` API error, `7` rate limited, `10` config error.

## Health Check

```bash
dsa-research-pp-cli doctor
```

Verifies configuration, credentials, and connectivity to the API.

## Configuration

Config file: `~/.config/dsa-vlop-transparency-pp-cli/config.toml`

Static request headers can be configured under `headers`; per-command header overrides take precedence.

Environment variables:

| Name | Kind | Required | Description |
| --- | --- | --- | --- |
| `DSA_RESEARCH_APIKEY_HEADER` | per_call | Yes | Set to your API credential. |

### agentcookie (optional)

If you use agentcookie to sync secrets across machines, this CLI auto-adopts agentcookie-managed credentials with no extra setup. When the daemon writes to this CLI's config, `dsa-research-pp-cli doctor` reports `agentcookie: detected` and `auth-status` labels the source as `agentcookie`. Skip this section if you don't use agentcookie - the CLI works the same as any other.

## Troubleshooting
**Authentication errors (exit code 4)**
- Run `dsa-research-pp-cli doctor` to check credentials
- Verify the environment variable is set: `echo $DSA_RESEARCH_APIKEY_HEADER`
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
