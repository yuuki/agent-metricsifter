---
name: metricsifter-calibration
description: Use when calibrating or tuning metricsifter hyperparameters (penalty_adjust and bandwidth) for a specific system. Triggered by "calibrate metricsifter", "tune parameters", "too many/few metrics remain", "adjust sensitivity", "the fault segment timing is wrong", "find the best parameters for my system", or when the user wants to verify that metricsifter default parameters are appropriate for their environment. Runs sift_metrics.py iteratively with human feedback and Grafana visualization to converge on optimal values for penalty_adjust and bandwidth.
---

# MetricSifter Calibration

Interactive hyperparameter calibration for metricsifter via human-in-the-loop feedback. Iterates `penalty_adjust` and `bandwidth` based on user judgment of Grafana dashboard visualizations until the filtering result matches the target system's characteristics.

**Skill directory**: The directory containing this SKILL.md is referred to as `SKILL_DIR` below. The metricsifter skill directory is referred to as `METRICSIFTER_SKILL_DIR` (resolve from the sibling `metricsifter/` directory).

## Prerequisites

- mcp-grafana configured as an MCP server (provides `update_dashboard`, `create_annotation`, `generate_deeplink`, `list_datasources`)
- metricsifter skill installed (sibling `metricsifter/` directory with `scripts/sift_metrics.py`)

## Hyperparameters

| Parameter | Default | Range | Step | Effect |
|-----------|---------|-------|------|--------|
| `penalty_adjust` | 2.0 | 0.5–5.0 | 0.2 | Higher → stricter filter (fewer metrics remain). Controls change-point detection sensitivity (penalty weight ω in the paper) |
| `bandwidth` | 2.5 | 0.5–5.0 | 0.2 | Higher → wider fault segment time window. Controls KDE smoothing bandwidth (h in the paper) |

**Sensitivity priority**: `penalty_adjust` has significantly higher impact on accuracy than `bandwidth`. `bandwidth` is stable across anomaly types. Always calibrate `penalty_adjust` first, then fine-tune `bandwidth`.

## Workflow

### Step 1: Confirm Data Source

Confirm the following with the user:

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| datasourceUid | Yes | - | Prometheus datasource UID |
| PromQL / pattern | Yes | - | Target metrics to fetch |
| startTime | Yes | - | Start time (RFC3339 or "now-1h") |
| endTime | No | "now" | End time |
| stepSeconds | No | 15 | Sampling interval in seconds |
| actual fault period | No | - | Known fault start/end time for segment evaluation |

- If `datasourceUid` is unknown, search for the Prometheus datasource using `list_datasources`
- If `$TMPDIR/prometheus_metrics.json` exists from a prior metricsifter run, ask the user if it should be reused (no need to refetch)
- If new data is needed, follow the metricsifter skill's Step 1–2 to fetch and save to `$TMPDIR/prometheus_metrics.json`
- Recommended: time range / stepSeconds >= 30 data points

### Step 2: Baseline Run (Default Parameters)

Run with default parameters:

```bash
uv run --directory METRICSIFTER_SKILL_DIR python METRICSIFTER_SKILL_DIR/scripts/sift_metrics.py \
  --input $TMPDIR/prometheus_metrics.json \
  --penalty-adjust 2.0 --bandwidth 2.5
```

Initialize calibration state:
- `current_penalty_adjust = 2.0`
- `current_bandwidth = 2.5`
- `iteration = 1`
- `phase = 1` (penalty_adjust tuning)

### Step 3: Create Comparison Dashboard and Present Results

**3a. Text summary**

After each run, display:

```
## Iteration N (Phase P) — penalty_adjust=X.X, bandwidth=Y.Y

| Item                  | Value                          |
|-----------------------|--------------------------------|
| Input metrics         | NNN                            |
| Remaining metrics     | NNN (PP%)                      |
| Removed metrics       | NNN                            |
| Fault segment (start) | 2024-01-15T22:10:00+09:00      |
| Fault segment (end)   | 2024-01-15T22:25:00+09:00      |
| Segment duration      | 15 min                         |
```

Edge case warnings:
- `output_metrics_count == 0` → "All metrics were filtered out. penalty_adjust is likely too high — suggest decreasing it."
- `output_metrics_count == input_metrics_count` → "No metrics were filtered. penalty_adjust is likely too low — suggest increasing it."

**3b. Create Grafana comparison dashboard**

Build a dashboard with **both** filtered and removed metrics so the user can visually compare them.

**Dashboard structure**:

```
Row 1: "Filtered (Remaining) Metrics" — row panel, collapsed: false
  ├── Panel: metric_name_A (timeseries, filtered series only)
  ├── Panel: metric_name_B
  └── ...

Row 2: "Removed Metrics" — row panel, collapsed: true (initially collapsed)
  ├── Panel: metric_name_C (timeseries, removed series only)
  ├── Panel: metric_name_D
  └── ...
```

**Dashboard JSON**:
```json
{
  "uid": "metricsifter-calibration-temp",
  "title": "[Calibration] Iteration N — pa=X.X bw=Y.Y",
  "tags": ["calibration", "metricsifter", "temporary"],
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

**Row panel template**:
```json
{
  "type": "row",
  "id": <id>,
  "title": "Filtered (Remaining) Metrics",
  "collapsed": false,
  "gridPos": { "x": 0, "y": <y>, "w": 24, "h": 1 }
}
```

For the "Removed Metrics" row, set `"collapsed": true` and nest the removed metric panels inside its `"panels"` array.

**Metric panel template** (same as grafana-incident-dashboard):
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
      "expr": "<metric_label_string>",
      "legendFormat": "auto"
    }
  ],
  "options": {
    "tooltip": { "mode": "multi" },
    "legend": { "showLegend": true, "placement": "bottom" }
  }
}
```

Group metrics by metric name (the part before `{`). Each group becomes one panel with multiple targets.

**Create/update the dashboard**:
```
update_dashboard(
  dashboard: <JSON>,
  message: "Calibration iteration N",
  overwrite: true
)
```

Use `overwrite: true` with the fixed UID `metricsifter-calibration-temp` to update in place on each iteration — this prevents dashboard proliferation.

**Add incident annotation** (only when `segment` is present):
```
create_annotation(
  dashboardUID: "metricsifter-calibration-temp",
  time: <segment.start_time as Unix ms>,
  timeEnd: <segment.end_time as Unix ms>,
  text: "Detected fault segment (iteration N)",
  tags: ["calibration", "metricsifter"]
)
```

**Generate link**:
```
generate_deeplink(dashboardUID: "metricsifter-calibration-temp")
```

**3c. Guide the user**

> A comparison dashboard has been created: [URL]
>
> The dashboard has two sections:
> - **Filtered (Remaining) Metrics**: Metrics that passed the filter (expanded)
> - **Removed Metrics**: Metrics that were filtered out (collapsed — click to expand)
>
> Please review the time series charts and evaluate:
> - Are there irrelevant metrics in the Filtered section?
> - Are there metrics in the Removed section that should have been kept?
> - Does the red annotation region match the actual fault period?

### Step 4: Collect Feedback

Calibration uses a phased approach based on the finding that `penalty_adjust` (ω) has significantly higher sensitivity to accuracy than `bandwidth` (h), which is stable across anomaly types (Tsubouchi & Tsuruta, 2024, Section IV-B5, Figure 9).

**Phase 1 — Tuning penalty_adjust** (bandwidth held constant):

Ask only Question A:
> After reviewing the Filtered / Removed sections in the dashboard, how is the filtering result?
> 1. Too many irrelevant metrics in Filtered → increase penalty_adjust (+0.2)
> 2. The remaining metrics are appropriate → proceed to Phase 2
> 3. Relevant metrics are missing (in Removed) → decrease penalty_adjust (-0.2)
> 4. Specify penalty_adjust value manually

**Phase 2 — Tuning bandwidth** (penalty_adjust held at Phase 1 result):

Ask only Question B (only if `segment` is not null):
> Is the red annotation region (fault segment) timing accurate?
> [If the user provided an actual fault period: show comparison here]
> 1. Segment is too wide → decrease bandwidth (-0.2)
> 2. Timing is appropriate → proceed to finalize
> 3. Segment is too narrow → increase bandwidth (+0.2)
> 4. Specify bandwidth value manually

**Phase 3 — Fine-tuning** (optional):

Present both Question A and B. If both answers are "appropriate", proceed to Step 7 (finalize).

### Step 5: Adjust Parameters

**penalty_adjust adjustment (from Question A)**:

| User choice | Formula |
|-------------|---------|
| Too many irrelevant | `min(current + 0.2, 5.0)` |
| Appropriate | No change |
| Relevant metrics missing | `max(current - 0.2, 0.5)` |
| Manual value | Use as-is. Warn if outside 0.5–5.0. Extra caution below 1.0 — accuracy drops sharply (paper Figure 9b) |

**bandwidth adjustment (from Question B)**:

| User choice | Formula |
|-------------|---------|
| Too wide | `max(current - 0.2, 0.5)` |
| Appropriate | No change |
| Too narrow | `min(current + 0.2, 5.0)` |
| Manual value | Use as-is. Warn if outside 0.5–5.0 |

### Step 6: Re-run with Adjusted Parameters

```bash
uv run --directory METRICSIFTER_SKILL_DIR python METRICSIFTER_SKILL_DIR/scripts/sift_metrics.py \
  --input $TMPDIR/prometheus_metrics.json \
  --penalty-adjust <current_penalty_adjust> \
  --bandwidth <current_bandwidth>
```

Increment `iteration`. Return to Step 3 (dashboard is overwritten via same UID).

Convergence guard: if `iteration > 10`, suggest finalizing with current parameters.

### Step 7: Finalize, Save, and Clean Up

**7a. Persist calibrated parameters**

Save to `SKILL_DIR/calibrated_params.json`:

```json
{
  "penalty_adjust": 1.6,
  "bandwidth": 3.0,
  "calibrated_at": "2024-01-15T23:00:00+09:00",
  "iterations": 4,
  "datasource_context": "Production Prometheus (node_exporter metrics)"
}
```

This file is read by the metricsifter skill to override default parameter values. It is gitignored (user-specific).

**7b. Final report**

```
## Calibration Complete

### Recommended Parameters (saved)
| Parameter       | Default | Calibrated |
|-----------------|---------|------------|
| penalty_adjust  | 2.0     | X.X        |
| bandwidth       | 2.5     | Y.Y        |

### Final Result
- Remaining metrics: NNN (PP%)
- Fault segment: START ~ END (D min)
- Calibration iterations: N

Parameters saved. They will be used automatically in future /metricsifter runs.
```

**7c. Temporary dashboard disposition**

Ask the user:
> What would you like to do with the calibration dashboard?
> - Delete it
> - Keep it as-is
> - Recreate as a proper incident dashboard → invoke the `grafana-incident-dashboard` skill

## Parameter Tuning Reference (based on Tsubouchi & Tsuruta 2024)

### Sensitivity Priority

From the paper (Section IV-B5, Figure 9): **penalty_adjust (ω) has significantly higher sensitivity to balanced accuracy (BA) than bandwidth (h)**. bandwidth is stable across anomaly types. Calibrate penalty_adjust first, then fine-tune bandwidth.

### Paper Optimal Values vs Code Defaults

| Parameter | Code default | Paper optimal (synthetic data) | Note |
|-----------|-------------|-------------------------------|------|
| penalty_adjust (ω) | 2.0 | 2.5 | Figure 9(a): BA peaks at ω=2.5, h=3.5 |
| bandwidth (h) | 2.5 | 3.5 | h is stable; small impact on performance |

Paper optimal values are based on synthetic data (PyRCA). Real systems may have different optima — hence the need for calibration.

### Symptom Reference

| Symptom | Cause | Fix | Paper reference |
|---------|-------|-----|----------------|
| Too many irrelevant metrics in Filtered | penalty_adjust too low | +0.2 | Low ω allows change points outside the fault window (Section III-C) |
| Relevant metrics in Removed section | penalty_adjust too high | -0.2 | High ω suppresses change point detection |
| Changing penalty_adjust has little effect | STEP 2&3 compensate for ω variation | Switch to bandwidth tuning | Figure 10: for ω ≥ 2.5, STEP 2&3 presence makes little difference |
| Annotation spans entire time range | bandwidth too high | -0.2 | Excessive KDE smoothing merges segments (Section III-D, Eq.3) |
| Annotation is a single point or very narrow | bandwidth too low | +0.2 | Insufficient bandwidth fragments density estimate |
| No annotation (segment null) | Too few change points | Decrease penalty_adjust first | KDE segmentation cannot function without change points |
| Accuracy drops sharply below penalty_adjust=1.0 | Noise detected as change points outside fault window | Stay above 1.0 unless necessary | Figure 9(b): BA degrades significantly as ω → 1.0 |

## Common Mistakes

- **Unnecessary data refetch**: `$TMPDIR/prometheus_metrics.json` is reused across all iterations. Only refetch if the user wants a different time range or metric set
- **Dashboard UID must be fixed**: Always use `metricsifter-calibration-temp` with `overwrite: true` to prevent dashboard proliferation across iterations
- **Empty Removed section**: Normal when penalty_adjust is very low (most metrics pass). Explain to the user
- **Skip Question B when segment is null**: Focus on penalty_adjust adjustment first — a null segment typically means too few change points
- **penalty_adjust below 1.0 requires caution**: Per paper Figure 9(b), BA drops sharply. Warn the user when approaching this range
