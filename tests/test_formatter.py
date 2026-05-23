"""Tests for driftcheck.formatter."""
from __future__ import annotations

import json
from typing import Dict, Tuple

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.formatter import FormatError, format_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(name: str) -> DriftResult:
    return DriftResult(service_name=name, drifted=False, differences={})


def _drifted(name: str, diffs: Dict[str, Tuple]) -> DriftResult:
    return DriftResult(service_name=name, drifted=True, differences=diffs)


# ---------------------------------------------------------------------------
# text format
# ---------------------------------------------------------------------------

def test_text_ok_service():
    out = format_results([_ok("web")], fmt="text")
    assert "[OK]" in out
    assert "web" in out


def test_text_drifted_service():
    r = _drifted("api", {"image": ("nginx:1.24", "nginx:1.25")})
    out = format_results([r], fmt="text")
    assert "[DRIFT]" in out
    assert "api" in out
    assert "image" in out
    assert "nginx:1.24" in out
    assert "nginx:1.25" in out


def test_text_multiple_services():
    results = [_ok("web"), _drifted("api", {"image": ("a", "b")})]
    out = format_results(results, fmt="text")
    assert "[OK]" in out
    assert "[DRIFT]" in out


def test_text_empty_results():
    out = format_results([], fmt="text")
    assert out == ""


# ---------------------------------------------------------------------------
# json format
# ---------------------------------------------------------------------------

def test_json_ok_service():
    out = format_results([_ok("web")], fmt="json")
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["service"] == "web"
    assert data[0]["drifted"] is False
    assert "differences" not in data[0]


def test_json_drifted_service():
    r = _drifted("api", {"image": ("nginx:1.24", "nginx:1.25")})
    out = format_results([r], fmt="json")
    data = json.loads(out)
    assert data[0]["drifted"] is True
    assert data[0]["differences"]["image"]["declared"] == "nginx:1.24"
    assert data[0]["differences"]["image"]["live"] == "nginx:1.25"


def test_json_empty_results():
    out = format_results([], fmt="json")
    assert json.loads(out) == []


def test_json_is_valid_json():
    results = [_ok("web"), _drifted("db", {"replicas": (3, 2)})]
    out = format_results(results, fmt="json")
    parsed = json.loads(out)  # must not raise
    assert isinstance(parsed, list)


# ---------------------------------------------------------------------------
# unknown format
# ---------------------------------------------------------------------------

def test_unknown_format_raises():
    with pytest.raises(FormatError, match="Unknown format"):
        format_results([_ok("web")], fmt="yaml")


def test_error_message_lists_supported_formats():
    with pytest.raises(FormatError, match="text"):
        format_results([], fmt="xml")
