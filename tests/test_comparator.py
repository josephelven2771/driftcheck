"""Tests for driftcheck.comparator."""

import pytest
from driftcheck.comparator import compare_service, DriftResult, _values_match


SAMPLE_LIVE = {
    "image": "nginx:1.25",
    "ports": ["80:80", "443:443"],
    "env": {"ENV": "production", "LOG_LEVEL": "info"},
    "labels": {"team": "platform"},
    "restart_policy": "always",
}


def test_no_drift_when_declared_matches_live():
    declared = {"image": "nginx:1.25", "restart_policy": "always"}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert not result.drifted
    assert result.missing_keys == []
    assert result.mismatches == {}


def test_drift_detected_on_image_mismatch():
    declared = {"image": "nginx:1.24"}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert result.drifted
    assert "image" in result.mismatches
    assert result.mismatches["image"]["declared"] == "nginx:1.24"
    assert result.mismatches["image"]["live"] == "nginx:1.25"


def test_drift_detected_on_missing_key_in_live():
    declared = {"image": "nginx:1.25", "cpu_limit": "0.5"}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert result.drifted
    assert "cpu_limit" in result.missing_keys


def test_extra_keys_in_live_are_ignored():
    declared = {"image": "nginx:1.25"}
    live = {**SAMPLE_LIVE, "unexpected_runtime_field": "somevalue"}
    result = compare_service("web", declared, live)
    assert not result.drifted


def test_port_list_order_independent():
    declared = {"ports": ["443:443", "80:80"]}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert not result.drifted


def test_env_dict_partial_match():
    declared = {"env": {"ENV": "production"}}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert not result.drifted


def test_env_dict_mismatch():
    declared = {"env": {"ENV": "staging"}}
    result = compare_service("web", declared, SAMPLE_LIVE)
    assert result.drifted
    assert "env" in result.mismatches


def test_drift_result_str_ok():
    result = DriftResult(service_name="web")
    assert "[OK]" in str(result)
    assert "web" in str(result)


def test_drift_result_str_drifted():
    result = DriftResult(
        service_name="api",
        drifted=True,
        missing_keys=["cpu_limit"],
        mismatches={"image": {"declared": "old", "live": "new"}},
    )
    output = str(result)
    assert "[DRIFT]" in output
    assert "cpu_limit" in output
    assert "image" in output


def test_values_match_scalars():
    assert _values_match("nginx:1.25", "nginx:1.25")
    assert not _values_match("nginx:1.24", "nginx:1.25")


def test_values_match_lists_order_independent():
    assert _values_match(["a", "b"], ["b", "a"])
    assert not _values_match(["a", "b"], ["a", "c"])
