---
name: metricsifter
description: Use when analyzing Prometheus metrics during incident investigation, filtering noise from large metric sets, or identifying which metrics changed during a fault window using mcp-grafana
---

# MetricSifter

Automatically extract only fault-related metrics from Prometheus. Uses change-point detection + KDE density analysis to keep only the metrics that changed during the fault period.

**Skill directory**: The directory containing this SKILL.md is referred to as `SKILL_DIR` below. Resolve it before running any scripts.

## Workflow

### Step 1: Confirm Parameters

Confirm the following with the user (ask interactively if unknown):

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| datasourceUid | Yes | - | Prometheus datasource UID |
| PromQL / pattern | Yes | - | Target metrics to fetch |
| startTime | Yes | - | Start time (RFC3339 or "now-1h") |
| endTime | No | "now" | End time |
| stepSeconds | No | 15 | Sampling interval in seconds |
| penalty_adjust | No | 2.0 | Filtering sensitivity (higher = stricter) |

- If `datasourceUid` is unknown, search for the Prometheus datasource using `list_datasources`
- Recommended: time range / stepSeconds >= 30 (at least 30 data points for reliable change-point detection)

### Step 2: Fetch Metrics

Fetch metrics using mcp-grafana tools.

**Identify metrics**:
1. PromQL specified → use as-is
2. Prefix specified → build `{__name__=~"prefix.*"}`
3. Not specified → list available metrics with `list_prometheus_metric_names` and confirm with user

**Execute range query**:
```
query_prometheus(
  datasourceUid: "<uid>",
  expr: "<promql>",
  startTime: "<start>",
  endTime: "<end>",
  stepSeconds: 15,
  queryType: "range"
)
```

**Save results**: Extract the `data.result` array from the response and save it to `$TMPDIR/prometheus_metrics.json` using the Write tool.

Expected input JSON format (`data.result` array):
```json
[
  {
    "metric": {"__name__": "cpu_usage", "instance": "host1"},
    "values": [[1700000000, "0.5"], [1700000060, "0.7"]]
  }
]
```

The script accepts both the bare result array and the full envelope format `{"status":"success","data":{"result":[...]}}`.

### Step 3: Run Filtering

```bash
uv run --directory SKILL_DIR python SKILL_DIR/scripts/sift_metrics.py --input $TMPDIR/prometheus_metrics.json
```

Replace `SKILL_DIR` with the absolute path of the directory containing this SKILL.md file.

**Options**:
- `--penalty-adjust 2.0` -- sensitivity (higher = stricter filter)
- `--search-method pelt` -- change-point detection algorithm (pelt/binseg/bottomup)
- `--bandwidth 2.5` -- KDE bandwidth
- `--n-jobs 1` -- number of parallel workers

### Step 4: Present Results

Parse the JSON output from the script and report:

1. **Summary**: input metric count → remaining metric count
2. **Remaining metrics list**: in table format
3. **Segment info**: time window with the highest change-point density (estimated fault impact period)
4. If all metrics were filtered out: suggest re-running with a lower `--penalty-adjust`

### Step 5: Deep Analysis (Optional)

If the user requests:
- Run additional queries on remaining metrics using `rate()`, `increase()`, etc.
- Generate Grafana dashboard links with `generate_deeplink`

## Common Mistakes

- **Insufficient data points**: stepSeconds too large causes insufficient data for change-point detection. Aim for time range / stepSeconds >= 30
- **penalty_adjust too high**: all metrics get filtered out. Adjust within 1.0 - 3.0 range
- **PromQL too broad**: queries like `{__name__=~".+"}` can return extremely large responses. Narrow the scope
