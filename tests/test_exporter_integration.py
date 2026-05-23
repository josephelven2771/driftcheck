"""Integration-style tests: exporter round-trips through all three formats."""

from __future__ import annotations

import csv
import io
import json

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.exporter import export_results


_RESULTS = [
    DriftResult(service_name="alpha", drifted=False, mismatches=[]),
    DriftResult(
        service_name="beta",
        drifted=True,
        mismatches=[
            ("image", "redis:7", "redis:6"),
            ("replicas", 3, 2),
        ],
    ),
]


def test_json_round_trip_service_names():
    data = json.loads(export_results(_RESULTS, "json"))
    names = [d["service"] for d in data]
    assert names == ["alpha", "beta"]


def test_json_round_trip_mismatch_count():
    data = json.loads(export_results(_RESULTS, "json"))
    beta = next(d for d in data if d["service"] == "beta")
    assert len(beta["mismatches"]) == 2


def test_csv_row_count_matches_total_mismatches_plus_ok_rows():
    # alpha → 1 row (no mismatches), beta → 2 rows (one per mismatch)
    out = export_results(_RESULTS, "csv")
    reader = csv.reader(io.StringIO(out))
    rows = list(reader)
    # header + 1 (alpha) + 2 (beta)
    assert len(rows) == 4


def test_csv_service_column_present_for_every_mismatch_row():
    out = export_results(_RESULTS, "csv")
    reader = csv.reader(io.StringIO(out))
    next(reader)  # skip header
    for row in reader:
        assert row[0] in ("alpha", "beta")


def test_text_contains_all_service_names():
    out = export_results(_RESULTS, "text")
    assert "alpha" in out
    assert "beta" in out


def test_text_contains_mismatch_keys():
    out = export_results(_RESULTS, "text")
    assert "image" in out
    assert "replicas" in out


def test_all_formats_produce_non_empty_output():
    for fmt in ("json", "csv", "text"):
        assert export_results(_RESULTS, fmt).strip() != ""
