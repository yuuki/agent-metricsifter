"""Prometheus API JSON response to pandas DataFrame conversion."""

from __future__ import annotations

import pandas as pd


def build_metric_label(metric: dict[str, str]) -> str:
    """Build a unique identifier string from a Prometheus metric label dict.

    Example:
        {"__name__": "cpu_usage", "instance": "host1:9090", "job": "node"}
        -> 'cpu_usage{instance="host1:9090",job="node"}'
    """
    name = metric.get("__name__", "")
    labels = {k: v for k, v in sorted(metric.items()) if k != "__name__"}
    if not labels:
        return name
    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
    if name:
        return f"{name}{{{label_str}}}"
    return f"{{{label_str}}}"


def prometheus_result_to_dataframe(result: list[dict]) -> pd.DataFrame:
    """Convert a Prometheus range query result array to a DataFrame.

    Args:
        result: The ``data.result`` array from ``query_prometheus``.
                Each element has ``{"metric": {...}, "values": [[ts, val], ...]}``.

    Returns:
        DataFrame with columns=metric identifiers, index=DatetimeIndex, values=float64.

    Raises:
        ValueError: If *result* is empty.
    """
    if not result:
        raise ValueError("Empty result array")

    series_dict: dict[str, pd.Series] = {}
    for item in result:
        label = build_metric_label(item["metric"])
        values = item.get("values", [])
        if not values:
            continue
        timestamps = [pd.Timestamp(v[0], unit="s", tz="UTC") for v in values]
        data = [float(v[1]) for v in values]
        series_dict[label] = pd.Series(data, index=timestamps, dtype="float64")

    if not series_dict:
        raise ValueError("No time series data found in result")

    df = pd.DataFrame(series_dict)
    df.index.name = "timestamp"
    return df


def merge_multiple_query_results(results: list[list[dict]]) -> pd.DataFrame:
    """Merge multiple ``query_prometheus`` result arrays into one DataFrame.

    Joins horizontally.  When timestamps differ across queries the union of
    all timestamps is used and missing values are filled with ``NaN``.
    """
    frames = [prometheus_result_to_dataframe(r) for r in results if r]
    if not frames:
        raise ValueError("No non-empty results to merge")
    merged = pd.concat(frames, axis=1)
    merged.index.name = "timestamp"
    return merged
