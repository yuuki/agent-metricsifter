"""Tests for prometheus_to_dataframe module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# Make scripts/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from prometheus_to_dataframe import (
    build_metric_label,
    merge_multiple_query_results,
    prometheus_result_to_dataframe,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# -- build_metric_label -------------------------------------------------------


class TestBuildMetricLabel:
    def test_name_only(self):
        assert build_metric_label({"__name__": "up"}) == "up"

    def test_name_with_single_label(self):
        assert build_metric_label({"__name__": "cpu", "host": "a"}) == 'cpu{host="a"}'

    def test_name_with_multiple_labels(self):
        result = build_metric_label({"__name__": "http_requests", "method": "GET", "code": "200"})
        assert result == 'http_requests{code="200",method="GET"}'

    def test_no_name(self):
        result = build_metric_label({"instance": "host1"})
        assert result == '{instance="host1"}'

    def test_empty(self):
        assert build_metric_label({}) == ""

    def test_labels_sorted(self):
        result = build_metric_label({"__name__": "m", "z": "1", "a": "2"})
        assert result == 'm{a="2",z="1"}'


# -- prometheus_result_to_dataframe -------------------------------------------


class TestPrometheusResultToDataframe:
    def test_basic_conversion(self):
        result = [
            {
                "metric": {"__name__": "cpu", "host": "a"},
                "values": [[1700000000, "0.5"], [1700000060, "0.7"]],
            }
        ]
        df = prometheus_result_to_dataframe(result)
        assert list(df.columns) == ['cpu{host="a"}']
        assert len(df) == 2
        assert df.iloc[0, 0] == 0.5
        assert df.iloc[1, 0] == 0.7

    def test_float_conversion(self):
        result = [
            {
                "metric": {"__name__": "mem"},
                "values": [[1700000000, "8000000000"]],
            }
        ]
        df = prometheus_result_to_dataframe(result)
        assert df.iloc[0, 0] == 8_000_000_000.0

    def test_datetime_index(self):
        result = [
            {
                "metric": {"__name__": "x"},
                "values": [[1700000000, "1"]],
            }
        ]
        df = prometheus_result_to_dataframe(result)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "timestamp"

    def test_empty_result_raises(self):
        with pytest.raises(ValueError, match="Empty result"):
            prometheus_result_to_dataframe([])

    def test_fixture_file(self):
        with open(FIXTURES / "prometheus_range_response.json") as f:
            data = json.load(f)
        df = prometheus_result_to_dataframe(data)
        assert df.shape == (6, 3)
        assert all(df.dtypes == "float64")


# -- merge_multiple_query_results ---------------------------------------------


class TestMergeMultipleQueryResults:
    def test_merge_two_results(self):
        r1 = [{"metric": {"__name__": "a"}, "values": [[1000, "1"], [1060, "2"]]}]
        r2 = [{"metric": {"__name__": "b"}, "values": [[1000, "3"], [1060, "4"]]}]
        df = merge_multiple_query_results([r1, r2])
        assert set(df.columns) == {"a", "b"}
        assert len(df) == 2

    def test_mismatched_timestamps(self):
        r1 = [{"metric": {"__name__": "a"}, "values": [[1000, "1"], [1060, "2"]]}]
        r2 = [{"metric": {"__name__": "b"}, "values": [[1000, "3"], [1120, "4"]]}]
        df = merge_multiple_query_results([r1, r2])
        assert len(df) == 3  # union of timestamps
        assert pd.isna(df.loc[df.index[1], "b"])  # ts=1060 missing in r2
        assert pd.isna(df.loc[df.index[2], "a"])  # ts=1120 missing in r1

    def test_empty_results_raises(self):
        with pytest.raises(ValueError):
            merge_multiple_query_results([])
