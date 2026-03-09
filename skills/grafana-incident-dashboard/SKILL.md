---
name: grafana-incident-dashboard
description: Use after metricsifter to create a Grafana dashboard for incident investigation from filtered metrics. Triggered when the user has metricsifter results and wants to visualize them in Grafana, or asks to "create a dashboard", "visualize filtered metrics", or "build an incident dashboard". Always use this skill when filtered_metrics and segment info are available from metricsifter output and the user wants to proceed to visualization.
---

# Grafana Incident Dashboard

Create a Grafana dashboard from metricsifter-filtered metrics for incident investigation. Groups metrics by name into time series panels, sets the dashboard time range, and marks the detected incident period as a Grafana annotation.

## Prerequisites

- mcp-grafana configured as an MCP server (provides `update_dashboard`, `create_annotation`, `generate_deeplink`, `list_datasources`)

## Workflow

### Step 1: Confirm Parameters

Confirm the following with the user (extract from prior metricsifter output when available):

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| filtered_metrics | Yes | - | `filtered_metrics` list from metricsifter output |
| datasourceUid | Yes | - | Prometheus datasource UID |
| segment | No | null | `segment` from metricsifter output (`start_time`/`end_time` in ISO 8601). Used for annotation only |
| startTime | No | now-1h | Dashboard display start (RFC 3339 or relative like `now-1h`) |
| endTime | No | now | Dashboard display end |
| dashboardTitle | No | auto | Auto-generated if omitted, e.g. "Incident Investigation 2024-01-15 22:13" |
| folderUid | No | null | Destination folder (General if omitted) |

- If `datasourceUid` is unknown, look it up with `list_datasources` and confirm with the user
- If `filtered_metrics` is empty, skip dashboard creation and explain why

### Step 2: Group Metrics by Name

Group the `filtered_metrics` label strings by **metric name** (the part before `{`). Each group becomes one panel.

Example grouping:
- `node_cpu_seconds_total{mode="idle"}` + `node_cpu_seconds_total{mode="system"}` -> 1 panel with 2 targets
- `node_memory_MemAvailable_bytes{instance="host1"}` -> 1 panel with 1 target

A metric string without `{` (e.g. `up`) is its own group with the full string as the metric name.

Maximum 500 metrics per panel. If a single metric name has more than 500 series, split into multiple panels with a suffix like `(1/2)`.

### Step 3: Build Dashboard JSON

Construct the dashboard JSON object. The metricsifter label strings (e.g. `cpu_usage{instance="host1"}`) are valid PromQL selectors and can be used directly as `expr` values -- no conversion needed.

**Dashboard structure**:
```json
{
  "uid": null,
  "title": "<dashboardTitle>",
  "tags": ["incident", "metricsifter"],
  "timezone": "browser",
  "time": {
    "from": "<startTime or 'now-1h'>",
    "to": "<endTime or 'now'>"
  },
  "schemaVersion": 41,
  "version": 0,
  "panels": []
}
```

**Panel template** (one per metric-name group):
```json
{
  "type": "timeseries",
  "id": <sequential_id>,
  "title": "<metric_name>",
  "gridPos": { "x": 0, "y": <8 * panel_index>, "w": 24, "h": 8 },
  "datasource": { "type": "prometheus", "uid": "<datasourceUid>" },
  "targets": [
    {
      "refId": "<A, B, C, ...>",
      "expr": "<filtered_metric_label_string>",
      "legendFormat": "auto"
    }
  ],
  "options": {
    "tooltip": { "mode": "multi" },
    "legend": { "showLegend": true, "placement": "bottom" }
  }
}
```

Each metric in the group becomes a separate target within the same panel, with sequential refIds (A, B, C, ...).

### Step 4: Create Dashboard and Add Annotation

**Create the dashboard**:
```
update_dashboard(
  dashboard: <JSON from Step 3>,
  folderUid: <folderUid or omit>,
  message: "Created by grafana-incident-dashboard skill (metricsifter output)",
  overwrite: false
)
```

**Add incident annotation** (only when `segment` is present):

Convert `segment.start_time` and `segment.end_time` from ISO 8601 strings to Unix milliseconds, then call:
```
create_annotation(
  dashboardUID: <UID returned by update_dashboard>,
  time: <segment.start_time as Unix ms>,
  timeEnd: <segment.end_time as Unix ms>,
  text: "Incident period detected by metricsifter",
  tags: ["incident", "metricsifter"]
)
```

This renders a red region annotation across all panels, marking the time window where metricsifter detected the highest density of change points.

### Step 5: Report Results

1. Report the created dashboard UID and title
2. Generate a direct URL using `generate_deeplink` and present it
3. Summarize: number of panels, total metrics visualized, and whether an incident annotation was added

## Common Mistakes

- **Missing datasourceUid**: Always confirm before building the JSON. Use `list_datasources` if the user doesn't know it
- **Forgetting annotation**: When `segment` is available, always add the annotation -- it is the key visual aid for incident investigation
- **Time format for annotation**: `create_annotation` expects Unix milliseconds (integer), not ISO 8601 strings. Convert before calling
