"""Tests for driftcheck.exporter."""

from __future__ import annotations

import csv
import io
import json

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.exporter import ExportError, export_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(name: str = "web") -> DriftResult:
    return DriftResult(service_name=name, drifted=False, mismatches=[])


def _drifted(name: str = "api") -> DriftResult:
    return DriftResult(
        service_name=name,
        drifted=True,
        mismatches=[("image", "nginx:1.24", "nginx:1.23")],
    )


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def test_json_ok_service():
    out = export_results([_ok()], "json")
    data = json.loads(out)
    assert data[0]["service"] == "web"
    assert data[0]["drifted"] is False
    assert data[0]["mismatches"] == []


def test_json_drifted_service():
    out = export_results([_drifted()], "json")
    data = json.loads(out)
    assert data[0]["drifted"] is True
    assert data[0]["mismatches"][0]["key"] == "image"
    assert data[0]["mismatches"][0]["declared"] == "nginx:1.24"
    assert data[0]["mismatches"][0]["live"] == "nginx:1.23"


def test_json_multiple_services():
    out = export_results([_ok(), _drifted()], "json")
    data = json.loads(out)
    assert len(data) == 2


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def test_csv_headers():
    out = export_results([_ok()], "csv")
    reader = csv.reader(io.StringIO(out))
    headers = next(reader)
    assert headers == ["service", "drifted", "key", "declared", "live"]


def test_csv_ok_row_has_empty_mismatch_columns():
    out = export_results([_ok("svc")], "csv")
    reader = csv.reader(io.StringIO(out))
    next(reader)  # skip header
    row = next(reader)
    assert row[0] == "svc"
    assert row[2] == ""  # key column empty


def test_csv_drifted_row_contains_mismatch():
    out = export_results([_drifted("api")], "csv")
    reader = csv.reader(io.StringIO(out))
    next(reader)
    row = next(reader)
    assert row[0] == "api"
    assert row[2] == "image"
    assert row[3] == "nginx:1.24"
    assert row[4] == "nginx:1.23"


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def test_text_ok_service():
    out = export_results([_ok("web")], "text")
    assert "[OK] web" in out


def test_text_drifted_service():
    out = export_results([_drifted("api")], "text")
    assert "[DRIFT] api" in out
    assert "image" in out


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_unsupported_format_raises():
    with pytest.raises(ExportError, match="Unsupported export format"):
        export_results([_ok()], "xml")


def test_empty_results_json():
    out = export_results([], "json")
    assert json.loads(out) == []


def test_empty_results_csv():
    out = export_results([], "csv")
    lines = [l for l in out.splitlines() if l]
    assert len(lines) == 1  # only the header


def test_empty_results_text():
    out = export_results([], "text")
    assert out == ""
