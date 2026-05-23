"""Tests for driftcheck.baseline."""

from __future__ import annotations

import json
import os

import pytest

from driftcheck.baseline import (
    BaselineError,
    baseline_metadata,
    load_baseline,
    save_baseline,
)

_SERVICES = {
    "web": {"image": "nginx:1.25", "ports": ["80:80"]},
    "db": {"image": "postgres:15", "env": {"POSTGRES_DB": "app"}},
}


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "baseline.json")
    save_baseline(_SERVICES, path)
    loaded = load_baseline(path)
    assert loaded == _SERVICES


def test_saved_file_contains_version_and_recorded_at(tmp_path):
    path = str(tmp_path / "baseline.json")
    save_baseline(_SERVICES, path)
    with open(path) as fh:
        raw = json.load(fh)
    assert raw["version"] == 1
    assert "recorded_at" in raw
    assert raw["recorded_at"].endswith("+00:00")


def test_save_creates_file(tmp_path):
    path = str(tmp_path / "baseline.json")
    assert not os.path.exists(path)
    save_baseline({}, path)
    assert os.path.exists(path)


def test_load_baseline_file_not_found_raises(tmp_path):
    with pytest.raises(BaselineError, match="not found"):
        load_baseline(str(tmp_path / "missing.json"))


def test_load_baseline_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not-json{{{")
    with pytest.raises(BaselineError, match="Invalid JSON"):
        load_baseline(str(path))


def test_load_baseline_missing_services_key_raises(tmp_path):
    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps({"version": 1}))
    with pytest.raises(BaselineError, match="'services'"):
        load_baseline(str(path))


def test_save_baseline_bad_path_raises():
    with pytest.raises(BaselineError, match="Could not write"):
        save_baseline(_SERVICES, "/no/such/directory/baseline.json")


def test_baseline_metadata_returns_version_and_timestamp(tmp_path):
    path = str(tmp_path / "baseline.json")
    save_baseline(_SERVICES, path)
    meta = baseline_metadata(path)
    assert meta["version"] == 1
    assert meta["recorded_at"] is not None


def test_baseline_metadata_file_not_found_raises(tmp_path):
    with pytest.raises(BaselineError, match="not found"):
        baseline_metadata(str(tmp_path / "ghost.json"))


def test_load_baseline_empty_services(tmp_path):
    path = str(tmp_path / "empty.json")
    save_baseline({}, path)
    assert load_baseline(path) == {}
