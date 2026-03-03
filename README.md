# agent-metricsifter

Claude Code Agent Skill for filtering Prometheus metrics using [metricsifter](https://github.com/ai4sre/metricsifter).

Automatically extracts only fault-related metrics from large sets of Prometheus metrics using change-point detection and KDE density analysis.

## Data Flow

```
mcp-grafana (query_prometheus)
  → Prometheus range query JSON
    → scripts/sift_metrics.py
      → metricsifter (change-point detection + KDE)
        → fault-related metrics only
```

## Setup

### 1. Python Dependencies

```bash
uv sync
```

### 2. mcp-grafana

Add to Claude Code MCP server configuration:

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

## Usage

### As an Agent Skill

Invoke `/metricsifter` in Claude Code, or ask to analyze and filter Prometheus metrics for fault-related signals.

### Standalone Script

```bash
uv run python scripts/sift_metrics.py --input prometheus_data.json
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input` | (required) | Input JSON file (`-` for stdin) |
| `--penalty-adjust` | 2.0 | Change-point detection sensitivity |
| `--search-method` | pelt | Detection algorithm (pelt/binseg/bottomup) |
| `--bandwidth` | 2.5 | KDE bandwidth |
| `--n-jobs` | 1 | Number of parallel workers |

## Test

```bash
uv run pytest tests/ -v
```
