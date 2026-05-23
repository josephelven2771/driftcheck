"""Tests for driftcheck.snapshot."""

from __future__ import annotations

import json
import os
import pytest

from driftcheck.snapshot import (
    SnapshotError,
    load_snapshot,
    save_snapshot,
    snapshot_metadata,
    _SNAPSHOT_VERSION,
)


_SAMPLE_STATE = {
    "web": {"image": "nginx:1.25", "ports": ["80:80"]},
    "api": {"image": "myapp:v2", "env": {"DEBUG": "false"}},
}


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "snap.json")
    save_snapshot(path, _SAMPLE_STATE)
    loaded = load_snapshot(path)
    assert loaded == _SAMPLE_STATE


def test_saved_file_contains_version_and_timestamp(tmp_path):
    path = str(tmp_path / "snap.json")
    save_snapshot(path, _SAMPLE_STATE)
    with open(path) as fh:
        raw = json.load(fh)
    assert raw["version"] == _SNAPSHOT_VERSION
    assert "captured_at" in raw
    assert raw["captured_at"].endswith("+00:00")


def test_load_snapshot_file_not_found_raises(tmp_path):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(str(tmp_path / "missing.json"))


def test_load_snapshot_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json at all", encoding="utf-8")
    with pytest.raises(SnapshotError, match="not valid JSON"):
        load_snapshot(str(path))


def test_load_snapshot_missing_services_key_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"version": _SNAPSHOT_VERSION, "captured_at": "x"}), encoding="utf-8")
    with pytest.raises(SnapshotError, match="'services'"):
        load_snapshot(str(path))


def test_load_snapshot_wrong_version_raises(tmp_path):
    path = tmp_path / "old.json"
    payload = {"version": 99, "captured_at": "x", "services": {}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SnapshotError, match="Unsupported snapshot version"):
        load_snapshot(str(path))


def test_save_snapshot_creates_file(tmp_path):
    path = str(tmp_path / "snap.json")
    assert not os.path.exists(path)
    save_snapshot(path, {})
    assert os.path.exists(path)


def test_no_tmp_file_left_after_save(tmp_path):
    path = str(tmp_path / "snap.json")
    save_snapshot(path, _SAMPLE_STATE)
    assert not os.path.exists(path + ".tmp")


def test_snapshot_metadata_returns_version_and_timestamp(tmp_path):
    path = str(tmp_path / "snap.json")
    save_snapshot(path, _SAMPLE_STATE)
    meta = snapshot_metadata(path)
    assert "version" in meta
    assert "captured_at" in meta
    assert "services" not in meta


def test_snapshot_metadata_raises_on_missing_file(tmp_path):
    with pytest.raises(SnapshotError):
        snapshot_metadata(str(tmp_path / "nope.json"))
