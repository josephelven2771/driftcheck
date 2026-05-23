"""Tests for driftcheck.differ."""

from __future__ import annotations

import pytest

from driftcheck.differ import (
    ServiceDiff,
    SnapshotDiff,
    diff_snapshots,
    _diff_service,
)


_OLD = {
    "web": {"image": "nginx:1.24", "ports": ["80:80"]},
    "db": {"image": "postgres:15", "env": {"PG_DB": "app"}},
}

_NEW = {
    "web": {"image": "nginx:1.25", "ports": ["80:80"]},
    "cache": {"image": "redis:7"},
}


def test_diff_detects_new_service():
    result = diff_snapshots(_OLD, _NEW)
    assert "cache" in result.new_services


def test_diff_detects_removed_service():
    result = diff_snapshots(_OLD, _NEW)
    assert "db" in result.removed_services


def test_diff_detects_changed_field():
    result = diff_snapshots(_OLD, _NEW)
    assert len(result.service_diffs) == 1
    diff = result.service_diffs[0]
    assert diff.service == "web"
    assert "image" in diff.changed
    assert diff.changed["image"] == ("nginx:1.24", "nginx:1.25")


def test_no_changes_when_identical():
    result = diff_snapshots(_OLD, _OLD)
    assert not result.has_changes
    assert result.new_services == []
    assert result.removed_services == []
    assert result.service_diffs == []


def test_empty_old_all_new():
    result = diff_snapshots({}, _OLD)
    assert set(result.new_services) == set(_OLD.keys())
    assert result.removed_services == []


def test_empty_new_all_removed():
    result = diff_snapshots(_OLD, {})
    assert result.new_services == []
    assert set(result.removed_services) == set(_OLD.keys())


def test_diff_service_added_key():
    diff = _diff_service("svc", {"a": 1}, {"a": 1, "b": 2})
    assert diff.added == {"b": 2}
    assert not diff.removed
    assert not diff.changed


def test_diff_service_removed_key():
    diff = _diff_service("svc", {"a": 1, "b": 2}, {"a": 1})
    assert diff.removed == {"b": 2}
    assert not diff.added
    assert not diff.changed


def test_diff_service_no_changes():
    diff = _diff_service("svc", {"x": 42}, {"x": 42})
    assert not diff.has_changes


def test_snapshot_diff_has_changes_true_on_new_service():
    sd = SnapshotDiff(new_services=["alpha"])
    assert sd.has_changes


def test_snapshot_diff_has_changes_false_when_empty():
    sd = SnapshotDiff()
    assert not sd.has_changes


def test_service_diff_has_changes_false_when_empty():
    d = ServiceDiff(service="x")
    assert not d.has_changes
