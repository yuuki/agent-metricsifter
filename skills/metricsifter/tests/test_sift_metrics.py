"""Tests for sift_metrics script."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sift_metrics import run  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestSiftMetrics:
    def test_empty_input(self, tmp_path: Path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]")
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = run(["--input", str(empty_file)])
        assert result["input_metrics_count"] == 0
        assert result["output_metrics_count"] == 0

    def test_fixture_input(self, tmp_path: Path):
        input_file = FIXTURES / "prometheus_range_response.json"
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = run(["--input", str(input_file)])
        assert result["input_metrics_count"] == 3
        assert isinstance(result["filtered_metrics"], list)
        assert isinstance(result["removed_metrics"], list)
        assert result["input_metrics_count"] == result["output_metrics_count"] + len(result["removed_metrics"])

    def test_output_is_valid_json(self, tmp_path: Path):
        input_file = FIXTURES / "prometheus_range_response.json"
        buf = StringIO()
        with patch("sys.stdout", buf):
            run(["--input", str(input_file)])
        output = json.loads(buf.getvalue())
        assert "input_metrics_count" in output
        assert "segment" in output

    def test_accepts_envelope_format(self, tmp_path: Path):
        """Accept full Prometheus API response envelope."""
        with open(FIXTURES / "prometheus_range_response.json") as f:
            bare = json.load(f)
        envelope = {"status": "success", "data": {"resultType": "matrix", "result": bare}}
        envelope_file = tmp_path / "envelope.json"
        envelope_file.write_text(json.dumps(envelope))
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = run(["--input", str(envelope_file)])
        assert result["input_metrics_count"] == 3

    def test_custom_penalty_adjust(self, tmp_path: Path):
        input_file = FIXTURES / "prometheus_range_response.json"
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = run(["--input", str(input_file), "--penalty-adjust", "5.0"])
        assert result["input_metrics_count"] == 3

    def test_rejects_malformed_envelope(self, tmp_path: Path):
        """Malformed envelope like {"data": []} should raise ValueError."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{"data": []}')
        buf = StringIO()
        import pytest

        with pytest.raises(ValueError, match="Expected"):
            with patch("sys.stdout", buf):
                run(["--input", str(bad_file)])


class TestSiftMetricsWithMockedSifter:
    """Test filtering results and segment output using a mocked Sifter."""

    def test_filtered_and_removed_metrics(self, tmp_path: Path):
        input_file = FIXTURES / "prometheus_range_response.json"

        @dataclass
        class FakeSegment:
            label: int = 0
            start_time: int = 1
            end_time: int = 3

        with open(input_file) as f:
            raw = json.load(f)
        from prometheus_to_dataframe import prometheus_result_to_dataframe

        df = prometheus_result_to_dataframe(raw)
        kept_col = df.columns[0]
        sifted_df = df[[kept_col]]

        mock_sifter_cls = MagicMock()
        mock_sifter_cls.return_value.run_with_selected_segment.return_value = (sifted_df, FakeSegment())

        buf = StringIO()
        with (
            patch("sys.stdout", buf),
            patch.dict("sys.modules", {"metricsifter": MagicMock(), "metricsifter.sifter": MagicMock(Sifter=mock_sifter_cls)}),
        ):
            result = run(["--input", str(input_file)])

        assert result["output_metrics_count"] == 1
        assert result["filtered_metrics"] == [kept_col]
        assert set(result["removed_metrics"]) == set(df.columns[1:])

    def test_segment_timestamps(self, tmp_path: Path):
        input_file = FIXTURES / "prometheus_range_response.json"

        with open(input_file) as f:
            raw = json.load(f)
        from prometheus_to_dataframe import prometheus_result_to_dataframe

        df = prometheus_result_to_dataframe(raw)

        @dataclass
        class FakeSegment:
            label: int = 0
            start_time: int = 1
            end_time: int = 4

        mock_sifter_cls = MagicMock()
        mock_sifter_cls.return_value.run_with_selected_segment.return_value = (df, FakeSegment())

        buf = StringIO()
        with (
            patch("sys.stdout", buf),
            patch.dict("sys.modules", {"metricsifter": MagicMock(), "metricsifter.sifter": MagicMock(Sifter=mock_sifter_cls)}),
        ):
            result = run(["--input", str(input_file)])

        assert result["segment"] is not None
        assert result["segment"]["label"] == 0
        expected_start = df.index[1].isoformat()
        expected_end = df.index[4].isoformat()
        assert result["segment"]["start_time"] == expected_start
        assert result["segment"]["end_time"] == expected_end
