# Transparency Report API agent setup

These are first-party instructions for connecting an AI coding or research agent to the Transparency Report API. Complete the setup yourself when your environment permits it. Ask the user only for a missing API key or for approval required by their agent host.

## 1. Identify and verify the API

Use the origin that served this file as `TRANSPARENCY_API_URL` (remove `/agent-setup/prompt.md`). Verify it before continuing:

```bash
curl -fsS "$TRANSPARENCY_API_URL/readyz"
curl -fsS "$TRANSPARENCY_API_URL/api/explore/options"
```

Public discovery and bounded queries do not require a key. The natural-language `ask` tool and asynchronous job tools do. If the user needs those tools, direct them to `$TRANSPARENCY_API_URL/api-key`; never paste, log, or commit their key.

## 2. Install the MCP server

Clone the first-party repository and install the MCP server in its own virtual environment:

```bash
git clone https://github.com/krMaynard/transparency-report-api.git
cd transparency-report-api
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r requirements-mcp.txt
```

Keep the absolute paths to `.venv-mcp/bin/python` and `mcp_server.py`. The server uses stdio and calls the hosted API over HTTP; it does not need a local database or API process.

## 3. Register it with the agent

Use the configuration format supported by the current agent host. Set `TRANSPARENCY_API_URL` to the verified origin. Add `TRANSPARENCY_API_KEY` only when the user supplied one through a secure secret mechanism.

### Claude Code

```bash
claude mcp add transparency-report-api \
  -e TRANSPARENCY_API_URL="$TRANSPARENCY_API_URL" \
  -- /absolute/path/to/transparency-report-api/.venv-mcp/bin/python \
     /absolute/path/to/transparency-report-api/mcp_server.py
```

### Codex

```bash
codex mcp add transparency-report-api \
  --env TRANSPARENCY_API_URL="$TRANSPARENCY_API_URL" \
  -- /absolute/path/to/transparency-report-api/.venv-mcp/bin/python \
     /absolute/path/to/transparency-report-api/mcp_server.py
```

### Cursor, VS Code, Claude Desktop, and other MCP hosts

Add this entry under `mcpServers` in the host's MCP configuration:

```json
{
  "transparency-report-api": {
    "command": "/absolute/path/to/transparency-report-api/.venv-mcp/bin/python",
    "args": ["/absolute/path/to/transparency-report-api/mcp_server.py"],
    "env": {
      "TRANSPARENCY_API_URL": "https://replace-with-the-origin-that-served-this-guide"
    }
  }
}
```

Restart or reload the host after changing its MCP configuration.

## 4. Verify the tools

Call `list_tables`, then `dataset_overview`, then `describe_table` for one table. Run a small query only after inspecting its dimensions and measures. Do not send SQL: this API accepts validated structured query objects.

When setup succeeds, tell the user which configuration was changed, whether the connection is public-only or authenticated, and that the following tools are available: `list_tables`, `describe_table`, `dataset_overview`, `run_query`, `ask`, `register`, `submit_query`, and `poll_job`.

## Resources

- Human-readable MCP guide: `$TRANSPARENCY_API_URL/mcp`
- API reference: `$TRANSPARENCY_API_URL/docs`
- Schema browser: `$TRANSPARENCY_API_URL/schema`
- Source and troubleshooting: `https://github.com/krMaynard/transparency-report-api/blob/main/docs/MCP.md`
