#!/usr/bin/env python3
"""Filter Prometheus metrics using metricsifter.

Usage:
    python scripts/sift_metrics.py --input <json_file> [options]
    cat data.json | python scripts/sift_metrics.py --input - [options]

Input:  Prometheus range query ``data.result`` array as JSON.
Output: Filtering result as JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Allow importing the sibling module without package installation.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prometheus_to_dataframe import prometheus_result_to_dataframe  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter Prometheus metrics with metricsifter")
    parser.add_argument("--input", required=True, help="Input JSON file path (use '-' for stdin)")
    parser.add_argument("--penalty-adjust", type=float, default=2.0, help="Change-point detection sensitivity (default: 2.0)")
    parser.add_argument("--n-jobs", type=int, default=1, help="Number of parallel workers (default: 1)")
    parser.add_argument("--search-method", default="pelt", choices=["pelt", "binseg", "bottomup"], help="Change-point search algorithm (default: pelt)")
    parser.add_argument("--bandwidth", type=float, default=2.5, help="KDE bandwidth (default: 2.5)")
    parser.add_argument("--segment-selection-method", default="weighted_max", help="Segment selection method (default: weighted_max)")
    return parser.parse_args(argv)


def _load_input(path: str) -> list[dict]:
    if path == "-":
        raw = json.load(sys.stdin)
    else:
        with open(path) as f:
            raw = json.load(f)

    # Accept both the full Prometheus response envelope and the bare result array.
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, dict):
            raw = data.get("result", data)
        else:
            raise ValueError("Expected {\"data\": {\"result\": [...]}} or a JSON array")
    if not isinstance(raw, list):
        raise ValueError("Input must be a JSON array (Prometheus data.result)")
    return raw


def _index_to_isoformat(idx: pd.DatetimeIndex, pos: int) -> str | None:
    if pos < 0 or pos >= len(idx):
        return None
    return idx[pos].isoformat()


def run(argv: list[str] | None = None) -> dict:
    args = _parse_args(argv)

    result = _load_input(args.input)
    if not result:
        output = {"input_metrics_count": 0, "output_metrics_count": 0, "filtered_metrics": [], "removed_metrics": [], "segment": None}
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return output

    df = prometheus_result_to_dataframe(result)
    input_metrics = list(df.columns)

    from metricsifter.sifter import Sifter

    sifter = Sifter(
        search_method=args.search_method,
        penalty_adjust=args.penalty_adjust,
        bandwidth=args.bandwidth,
        segment_selection_method=args.segment_selection_method,
        n_jobs=args.n_jobs,
    )

    sifted_df, segment = sifter.run_with_selected_segment(data=df)

    filtered_metrics = list(sifted_df.columns)
    removed_metrics = [m for m in input_metrics if m not in filtered_metrics]

    segment_info = None
    if segment is not None:
        start_pos = segment.start_time
        end_pos = segment.end_time
        # Ensure the segment spans at least one step so that Grafana region
        # annotations are visible instead of collapsing to a zero-width point.
        if start_pos == end_pos:
            if end_pos + 1 < len(df.index):
                end_pos = end_pos + 1
            elif start_pos - 1 >= 0:
                start_pos = start_pos - 1
        segment_info = {
            "label": segment.label,
            "start_time": _index_to_isoformat(df.index, start_pos),
            "end_time": _index_to_isoformat(df.index, end_pos),
        }

    output = {
        "input_metrics_count": len(input_metrics),
        "output_metrics_count": len(filtered_metrics),
        "filtered_metrics": filtered_metrics,
        "removed_metrics": removed_metrics,
        "segment": segment_info,
    }

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return output


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
