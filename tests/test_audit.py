"""Tests for driftcheck.audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftcheck.audit import (
    AUDIT_VERSION,
    AuditError,
    append_audit_entry,
    load_audit_log,
)
from driftcheck.comparator import DriftResult


def _ok(name: str) -> DriftResult:
    return DriftResult(service_name=name, drifted=False, mismatches={})


def _drifted(name: str) -> DriftResult:
    return DriftResult(
        service_name=name, drifted=True, mismatches={"image": ("a:1", "a:2")}
    )


# ---------------------------------------------------------------------------
# append_audit_entry
# ---------------------------------------------------------------------------

def test_append_creates_file(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    assert log.exists()


def test_append_writes_valid_json_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["version"] == AUDIT_VERSION
    assert "recorded_at" in entry


def test_append_multiple_calls_produce_multiple_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    append_audit_entry(log, [_drifted("api")])
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_drifted_count_is_correct(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web"), _drifted("api"), _drifted("db")])
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["drifted_count"] == 2
    assert entry["total_services"] == 3


def test_run_id_stored(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")], run_id="run-42")
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["run_id"] == "run-42"


def test_run_id_defaults_to_none(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["run_id"] is None


def test_creates_parent_directories(tmp_path):
    log = tmp_path / "nested" / "dir" / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    assert log.exists()


# ---------------------------------------------------------------------------
# load_audit_log
# ---------------------------------------------------------------------------

def test_load_returns_all_entries(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    append_audit_entry(log, [_drifted("api")])
    entries = load_audit_log(log)
    assert len(entries) == 2


def test_load_file_not_found_raises(tmp_path):
    with pytest.raises(AuditError, match="not found"):
        load_audit_log(tmp_path / "missing.jsonl")


def test_load_invalid_json_raises(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text("not-json\n")
    with pytest.raises(AuditError, match="Invalid JSON"):
        load_audit_log(log)


def test_load_skips_blank_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    append_audit_entry(log, [_ok("web")])
    with log.open("a") as fh:
        fh.write("\n\n")
    entries = load_audit_log(log)
    assert len(entries) == 1
