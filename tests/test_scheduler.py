"""Tests for driftcheck.scheduler."""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.scheduler import Scheduler, SchedulerConfig, SchedulerError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_result(name: str = "svc") -> DriftResult:
    return DriftResult(service_name=name, drifted=False, drifted_fields={})


def _make_check_fn(results: List[DriftResult]):
    return MagicMock(return_value=results)


# ---------------------------------------------------------------------------
# SchedulerConfig.validate
# ---------------------------------------------------------------------------

def test_validate_raises_on_zero_interval():
    with pytest.raises(SchedulerError, match="interval_seconds"):
        SchedulerConfig(interval_seconds=0).validate()


def test_validate_raises_on_negative_interval():
    with pytest.raises(SchedulerError):
        SchedulerConfig(interval_seconds=-5).validate()


def test_validate_raises_on_zero_max_ticks():
    with pytest.raises(SchedulerError, match="max_ticks"):
        SchedulerConfig(interval_seconds=1, max_ticks=0).validate()


def test_validate_passes_with_none_max_ticks():
    SchedulerConfig(interval_seconds=10, max_ticks=None).validate()  # no exception


# ---------------------------------------------------------------------------
# Scheduler.run — tick count
# ---------------------------------------------------------------------------

@patch("driftcheck.scheduler.time.sleep")
def test_run_executes_correct_number_of_ticks(mock_sleep):
    check_fn = _make_check_fn([_ok_result()])
    cfg = SchedulerConfig(interval_seconds=1, max_ticks=3)
    sched = Scheduler(check_fn, cfg)
    sched.run()
    assert sched.tick_count == 3
    assert check_fn.call_count == 3


@patch("driftcheck.scheduler.time.sleep")
def test_run_calls_sleep_between_ticks(mock_sleep):
    check_fn = _make_check_fn([_ok_result()])
    cfg = SchedulerConfig(interval_seconds=30, max_ticks=2)
    sched = Scheduler(check_fn, cfg)
    sched.run()
    # sleep called once (between tick 1 and tick 2; not after last tick)
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(30)


# ---------------------------------------------------------------------------
# Scheduler — sink interaction
# ---------------------------------------------------------------------------

@patch("driftcheck.scheduler.time.sleep")
def test_sink_receives_results(mock_sleep):
    results = [_ok_result("web")]
    check_fn = _make_check_fn(results)
    sink = MagicMock()
    cfg = SchedulerConfig(interval_seconds=1, max_ticks=1, sinks=[sink])
    Scheduler(check_fn, cfg).run()
    sink.assert_called_once_with(results)


@patch("driftcheck.scheduler.time.sleep")
def test_failing_check_fn_does_not_crash_scheduler(mock_sleep):
    check_fn = MagicMock(side_effect=RuntimeError("boom"))
    cfg = SchedulerConfig(interval_seconds=1, max_ticks=2)
    sched = Scheduler(check_fn, cfg)
    sched.run()  # should not raise
    assert sched.tick_count == 2


@patch("driftcheck.scheduler.time.sleep")
def test_failing_sink_does_not_crash_scheduler(mock_sleep):
    check_fn = _make_check_fn([_ok_result()])
    bad_sink = MagicMock(side_effect=OSError("disk full"))
    cfg = SchedulerConfig(interval_seconds=1, max_ticks=1, sinks=[bad_sink])
    sched = Scheduler(check_fn, cfg)
    sched.run()  # should not raise
    assert sched.tick_count == 1
