# agent-metricsifter

Automatic Prometheus metrics filtering skill using mcp-grafana + metricsifter.

## Prerequisites

- Python 3.10+
- mcp-grafana configured as an MCP server

## Setup

```bash
uv sync
```

## Test

```bash
uv run pytest tests/ -v
```

## Lint

```bash
uv run ruff check .
```

## Usage

Invoke `/metricsifter` in Claude Code, or ask to analyze and filter Prometheus metrics.

## mcp-grafana Setup

Add the following to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "grafana": {
      "command": "uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "<token>"
      }
    }
  }
}
```
