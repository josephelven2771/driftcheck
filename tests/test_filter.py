"""Tests for driftcheck.filter."""

from __future__ import annotations

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.filter import (
    FilterError,
    filter_by_name,
    filter_drifted,
    filter_ok,
)


def _make(name: str, drifted: bool = False) -> DriftResult:
    diffs = {"image": ("a", "b")} if drifted else {}
    return DriftResult(service_name=name, diffs=diffs)


# ---------------------------------------------------------------------------
# filter_by_name
# ---------------------------------------------------------------------------

def test_filter_by_name_exact_match():
    results = [_make("web"), _make("db"), _make("cache")]
    filtered = filter_by_name(results, ["db"])
    assert [r.service_name for r in filtered] == ["db"]


def test_filter_by_name_glob_pattern():
    results = [_make("web-1"), _make("web-2"), _make("db")]
    filtered = filter_by_name(results, ["web-*"])
    assert [r.service_name for r in filtered] == ["web-1", "web-2"]


def test_filter_by_name_multiple_patterns():
    results = [_make("web"), _make("db"), _make("cache")]
    filtered = filter_by_name(results, ["web", "cache"])
    assert [r.service_name for r in filtered] == ["web", "cache"]


def test_filter_by_name_no_match_returns_empty():
    results = [_make("web"), _make("db")]
    filtered = filter_by_name(results, ["missing"])
    assert filtered == []


def test_filter_by_name_empty_patterns_returns_all():
    results = [_make("web"), _make("db")]
    filtered = filter_by_name(results, [])
    assert len(filtered) == 2


def test_filter_by_name_blank_pattern_raises():
    results = [_make("web")]
    with pytest.raises(FilterError):
        filter_by_name(results, [""])


def test_filter_by_name_whitespace_pattern_raises():
    results = [_make("web")]
    with pytest.raises(FilterError):
        filter_by_name(results, ["   "])


def test_filter_by_name_preserves_order():
    names = ["alpha", "beta", "gamma"]
    results = [_make(n) for n in names]
    filtered = filter_by_name(results, ["*"])
    assert [r.service_name for r in filtered] == names


# ---------------------------------------------------------------------------
# filter_drifted / filter_ok
# ---------------------------------------------------------------------------

def test_filter_drifted_returns_only_drifted():
    results = [_make("web", drifted=True), _make("db", drifted=False)]
    assert [r.service_name for r in filter_drifted(results)] == ["web"]


def test_filter_ok_returns_only_ok():
    results = [_make("web", drifted=True), _make("db", drifted=False)]
    assert [r.service_name for r in filter_ok(results)] == ["db"]


def test_filter_drifted_empty_input():
    assert filter_drifted([]) == []


def test_filter_ok_empty_input():
    assert filter_ok([]) == []
