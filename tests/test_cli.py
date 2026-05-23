"""Tests for the driftcheck CLI entry point."""

import pytest
from unittest.mock import patch, MagicMock

from driftcheck.cli import run, build_parser
from driftcheck.comparator import DriftResult
from driftcheck.parser import ParseError
from driftcheck.fetcher import FetchError


SAMPLE_DEFS = {"web": {"image": "nginx:latest", "ports": ["80:80"]}}
SAMPLE_LIVE = {"image": "nginx:latest", "ports": ["80:80"]}


def _ok_result(name="web"):
    return DriftResult(service=name, drifted=False, differences={})


def _drifted_result(name="web"):
    return DriftResult(
        service=name,
        drifted=True,
        differences={"image": {"declared": "nginx:latest", "live": "nginx:1.19"}},
    )


@patch("driftcheck.cli.print_report", return_value=0)
@patch("driftcheck.cli.format_summary", return_value="Summary: all good")
@patch("driftcheck.cli.compare_service", return_value=_ok_result())
@patch("driftcheck.cli.fetch_docker_service_state", return_value=SAMPLE_LIVE)
@patch("driftcheck.cli.extract_service_definitions", return_value=SAMPLE_DEFS)
@patch("driftcheck.cli.load_yaml", return_value={})
def test_run_returns_0_when_no_drift(mock_load, mock_extract, mock_fetch, mock_compare, mock_summary, mock_report):
    assert run(["infra.yml"]) == 0


@patch("driftcheck.cli.print_report", return_value=1)
@patch("driftcheck.cli.format_summary", return_value="Summary: drift detected")
@patch("driftcheck.cli.compare_service", return_value=_drifted_result())
@patch("driftcheck.cli.fetch_docker_service_state", return_value=SAMPLE_LIVE)
@patch("driftcheck.cli.extract_service_definitions", return_value=SAMPLE_DEFS)
@patch("driftcheck.cli.load_yaml", return_value={})
def test_run_returns_1_when_drift(mock_load, mock_extract, mock_fetch, mock_compare, mock_summary, mock_report):
    assert run(["infra.yml"]) == 1


@patch("driftcheck.cli.load_yaml", side_effect=ParseError("bad file"))
def test_run_returns_2_on_parse_error(mock_load):
    assert run(["infra.yml"]) == 2


@patch("driftcheck.cli.fetch_docker_service_state", side_effect=FetchError("timeout"))
@patch("driftcheck.cli.extract_service_definitions", return_value=SAMPLE_DEFS)
@patch("driftcheck.cli.load_yaml", return_value={})
def test_run_returns_2_on_fetch_error(mock_load, mock_extract, mock_fetch):
    assert run(["infra.yml"]) == 2


@patch("driftcheck.cli.print_report", return_value=0)
@patch("driftcheck.cli.format_summary", return_value="")
@patch("driftcheck.cli.compare_service", return_value=_ok_result())
@patch("driftcheck.cli.fetch_docker_service_state", return_value=SAMPLE_LIVE)
@patch("driftcheck.cli.extract_service_definitions", return_value=SAMPLE_DEFS)
@patch("driftcheck.cli.load_yaml", return_value={})
def test_run_filters_by_service_flag(mock_load, mock_extract, mock_fetch, mock_compare, mock_summary, mock_report):
    run(["infra.yml", "--service", "web"])
    mock_fetch.assert_called_once_with("web")


@patch("driftcheck.cli.extract_service_definitions", return_value=SAMPLE_DEFS)
@patch("driftcheck.cli.load_yaml", return_value={})
def test_run_returns_2_for_unknown_service(mock_load, mock_extract):
    assert run(["infra.yml", "--service", "nonexistent"]) == 2


def test_build_parser_requires_config():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_parser_accepts_quiet_flag():
    parser = build_parser()
    args = parser.parse_args(["infra.yml", "--quiet"])
    assert args.quiet is True
    assert args.config == "infra.yml"
