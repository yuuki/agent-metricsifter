# agent-metricsifter

Agent skills for Prometheus metrics analysis and incident investigation using mcp-grafana + metricsifter.

## Prerequisites

- Python 3.10+
- mcp-grafana configured as an MCP server

## Setup

```bash
cd skills/metricsifter && uv sync
```

## Test

```bash
cd skills/metricsifter && uv run pytest tests/ -v
```

## Lint

```bash
cd skills/metricsifter && uv run ruff check .
```

## Usage

Invoke `/metricsifter` in Claude Code, or ask to analyze and filter Prometheus metrics.
After filtering, invoke `/grafana-incident-dashboard` to create a Grafana dashboard from the results.

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
