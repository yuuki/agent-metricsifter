"""Tests for sift_metrics script."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
