# agent-metricsifter

Claude Code Agent Skills for Prometheus metrics analysis and incident investigation using [metricsifter](https://github.com/ai4sre/metricsifter) and [mcp-grafana](https://github.com/grafana/mcp-grafana).

## Skills

| Skill | Description |
|-------|-------------|
| [metricsifter](skills/metricsifter/) | Filter Prometheus metrics to extract only fault-related signals using change-point detection and KDE density analysis |
| [grafana-incident-dashboard](skills/grafana-incident-dashboard/) | Create a Grafana dashboard from metricsifter-filtered metrics for incident investigation |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yuuki/agent-metricsifter
```

### 2. Install skills

```bash
# metricsifter skill (requires Python dependencies)
ln -s "$(pwd)/agent-metricsifter/skills/metricsifter" ~/.claude/skills/metricsifter
cd ~/.claude/skills/metricsifter && uv sync

# grafana-incident-dashboard skill (no additional dependencies)
ln -s "$(pwd)/agent-metricsifter/skills/grafana-incident-dashboard" ~/.claude/skills/grafana-incident-dashboard
```

### 3. Configure mcp-grafana

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

### metricsifter

Invoke `/metricsifter` in Claude Code, or ask to analyze and filter Prometheus metrics for fault-related signals.

```bash
# Standalone script
cd ~/.claude/skills/metricsifter
uv run python scripts/sift_metrics.py --input prometheus_data.json
```

| Option | Default | Description |
|--------|---------|-------------|
| `--input` | (required) | Input JSON file (`-` for stdin) |
| `--penalty-adjust` | 2.0 | Change-point detection sensitivity |
| `--search-method` | pelt | Detection algorithm (pelt/binseg/bottomup) |
| `--bandwidth` | 2.5 | KDE bandwidth |
| `--n-jobs` | 1 | Number of parallel workers |

### grafana-incident-dashboard

After running metricsifter, ask to create a dashboard from the filtered metrics, or invoke `/grafana-incident-dashboard`. The skill groups filtered metrics by name into time series panels and marks the detected incident period as a Grafana annotation.

## Data Flow

```
mcp-grafana (query_prometheus)
  -> Prometheus range query JSON
    -> metricsifter (change-point detection + KDE)
      -> fault-related metrics only
        -> grafana-incident-dashboard
          -> Grafana dashboard + incident annotation
```

## Development

```bash
cd skills/metricsifter
uv sync --all-extras
uv run pytest tests/ -v
uv run ruff check .
```
