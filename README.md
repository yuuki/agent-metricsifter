# agent-metricsifter

Claude Code Agent Skill for filtering Prometheus metrics using [metricsifter](https://github.com/ai4sre/metricsifter).

Automatically extracts only fault-related metrics from large sets of Prometheus metrics using change-point detection and KDE density analysis.

## Installation

### 1. Install the skill

```bash
git clone https://github.com/yuuki/agent-metricsifter ~/.claude/skills/metricsifter
cd ~/.claude/skills/metricsifter && uv sync
```

### 2. Configure mcp-grafana

Add to your Claude Code MCP server configuration (`.claude/settings.json`):

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
cd ~/.claude/skills/metricsifter
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

## Data Flow

```
mcp-grafana (query_prometheus)
  → Prometheus range query JSON
    → scripts/sift_metrics.py
      → metricsifter (change-point detection + KDE)
        → fault-related metrics only
```

## Development

```bash
uv sync --all-extras
uv run pytest tests/ -v
uv run ruff check .
```
