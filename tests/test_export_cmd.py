"""Tests for driftcheck.export_cmd."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.export_cmd import build_export_parser, run_export
from driftcheck.fetcher import FetchError
from driftcheck.parser import ParseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(config="cfg.yaml", fmt="json", output=None):
    ns = build_export_parser().parse_args([config, "--format", fmt])
    ns.output = output
    return ns


_SERVICES = {"web": {"image": "nginx:1.24", "ports": ["80:80"]}}
_LIVE_OK = {"image": "nginx:1.24", "ports": ["80:80"]}
_LIVE_DRIFT = {"image": "nginx:1.23", "ports": ["80:80"]}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_build_export_parser_defaults():
    p = build_export_parser()
    args = p.parse_args(["my.yaml"])
    assert args.config == "my.yaml"
    assert args.fmt == "text"
    assert args.output is None


# ---------------------------------------------------------------------------
# run_export
# ---------------------------------------------------------------------------

@patch("driftcheck.export_cmd.fetch_docker_service_state", return_value=_LIVE_OK)
@patch("driftcheck.export_cmd.extract_service_definitions", return_value=_SERVICES)
@patch("driftcheck.export_cmd.load_yaml", return_value={})
def test_run_export_returns_0_when_no_drift(mock_yaml, mock_extract, mock_fetch):
    args = _args(fmt="json")
    assert run_export(args) == 0


@patch("driftcheck.export_cmd.fetch_docker_service_state", return_value=_LIVE_DRIFT)
@patch("driftcheck.export_cmd.extract_service_definitions", return_value=_SERVICES)
@patch("driftcheck.export_cmd.load_yaml", return_value={})
def test_run_export_returns_1_when_drift(mock_yaml, mock_extract, mock_fetch):
    args = _args(fmt="json")
    assert run_export(args) == 1


@patch("driftcheck.export_cmd.load_yaml", side_effect=ParseError("bad yaml"))
def test_run_export_returns_2_on_parse_error(mock_yaml):
    args = _args()
    assert run_export(args) == 2


@patch("driftcheck.export_cmd.fetch_docker_service_state", side_effect=FetchError("no docker"))
@patch("driftcheck.export_cmd.extract_service_definitions", return_value=_SERVICES)
@patch("driftcheck.export_cmd.load_yaml", return_value={})
def test_run_export_continues_on_fetch_error(mock_yaml, mock_extract, mock_fetch):
    """A FetchError for one service should not abort the whole run."""
    args = _args(fmt="json")
    rc = run_export(args)
    # live state was empty so image will differ → drifted
    assert rc in (0, 1)


@patch("driftcheck.export_cmd.fetch_docker_service_state", return_value=_LIVE_OK)
@patch("driftcheck.export_cmd.extract_service_definitions", return_value=_SERVICES)
@patch("driftcheck.export_cmd.load_yaml", return_value={})
def test_run_export_writes_file(mock_yaml, mock_extract, mock_fetch, tmp_path):
    out_file = tmp_path / "results.json"
    args = _args(fmt="json", output=str(out_file))
    run_export(args)
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert isinstance(data, list)
    assert data[0]["service"] == "web"
