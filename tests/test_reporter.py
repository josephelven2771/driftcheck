"""Tests for driftcheck.reporter."""

import io
import pytest
from driftcheck.comparator import DriftResult
from driftcheck.reporter import print_report, format_summary


def _make_ok(name: str = "web") -> DriftResult:
    return DriftResult(service_name=name, drifted=False)


def _make_drifted(name: str = "api") -> DriftResult:
    return DriftResult(
        service_name=name,
        drifted=True,
        mismatches={"image": {"declared": "v1", "live": "v2"}},
    )


def test_print_report_returns_0_when_no_drift():
    out, err = io.StringIO(), io.StringIO()
    code = print_report([_make_ok()], out=out, err=err)
    assert code == 0


def test_print_report_returns_1_when_drift():
    out, err = io.StringIO(), io.StringIO()
    code = print_report([_make_drifted()], out=out, err=err)
    assert code == 1


def test_ok_services_go_to_stdout():
    out, err = io.StringIO(), io.StringIO()
    print_report([_make_ok("web")], out=out, err=err)
    assert "web" in out.getvalue()
    assert "web" not in err.getvalue()


def test_drifted_services_go_to_stderr():
    out, err = io.StringIO(), io.StringIO()
    print_report([_make_drifted("api")], out=out, err=err)
    assert "api" in err.getvalue()
    assert "api" not in out.getvalue()


def test_summary_line_all_ok():
    out, err = io.StringIO(), io.StringIO()
    print_report([_make_ok(), _make_ok("db")], out=out, err=err)
    assert "All 2 service(s) are in sync" in out.getvalue()


def test_summary_line_with_drift():
    out, err = io.StringIO(), io.StringIO()
    print_report([_make_ok(), _make_drifted()], out=out, err=err)
    assert "1/2" in err.getvalue()


def test_format_summary_all_ok():
    results = [_make_ok("a"), _make_ok("b")]
    summary = format_summary(results)
    assert "2" in summary
    assert "Drifted: 0" in summary


def test_format_summary_mixed():
    results = [_make_ok(), _make_drifted()]
    summary = format_summary(results)
    assert "OK: 1" in summary
    assert "Drifted: 1" in summary
