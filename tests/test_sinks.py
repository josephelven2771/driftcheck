"""Tests for driftcheck.sinks."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.sinks import _JsonFileSink, _StreamSink, log_sink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(name: str = "svc") -> DriftResult:
    return DriftResult(service_name=name, drifted=False, drifted_fields={})


def _drifted(name: str = "svc") -> DriftResult:
    return DriftResult(
        service_name=name,
        drifted=True,
        drifted_fields={"image": ("a:1", "a:2")},
    )


# ---------------------------------------------------------------------------
# _StreamSink
# ---------------------------------------------------------------------------

def test_stream_sink_ok_message():
    buf = io.StringIO()
    sink = _StreamSink(buf)
    sink([_ok("web"), _ok("db")])
    assert "OK" in buf.getvalue()
    assert "2" in buf.getvalue()


def test_stream_sink_drift_message():
    buf = io.StringIO()
    sink = _StreamSink(buf)
    sink([_ok("db"), _drifted("web")])
    out = buf.getvalue()
    assert "DRIFT" in out
    assert "web" in out


def test_stream_sink_no_output_for_empty_list():
    buf = io.StringIO()
    sink = _StreamSink(buf)
    sink([])
    # Empty list → 0 services, still writes OK line
    assert "OK" in buf.getvalue()


# ---------------------------------------------------------------------------
# _JsonFileSink
# ---------------------------------------------------------------------------

def test_json_file_sink_creates_file(tmp_path: Path):
    out = tmp_path / "drift.jsonl"
    sink = _JsonFileSink(out)
    sink([_ok()])
    assert out.exists()


def test_json_file_sink_valid_json(tmp_path: Path):
    out = tmp_path / "drift.jsonl"
    sink = _JsonFileSink(out)
    sink([_drifted("api")])
    record = json.loads(out.read_text().strip())
    assert record["total"] == 1
    assert record["drifted"][0]["service"] == "api"


def test_json_file_sink_appends_multiple_ticks(tmp_path: Path):
    out = tmp_path / "drift.jsonl"
    sink = _JsonFileSink(out)
    sink([_ok()])
    sink([_drifted()])
    lines = [l for l in out.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# log_sink (smoke test via caplog)
# ---------------------------------------------------------------------------

def test_log_sink_no_drift(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="driftcheck.sinks"):
        log_sink([_ok("a"), _ok("b")])
    assert any("No drift" in r.message for r in caplog.records)


def test_log_sink_with_drift(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="driftcheck.sinks"):
        log_sink([_ok("a"), _drifted("b")])
    assert any("Drift detected" in r.message for r in caplog.records)
