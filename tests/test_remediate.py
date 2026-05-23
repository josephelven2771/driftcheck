"""Tests for driftcheck.remediate."""
import pytest

from driftcheck.comparator import DriftResult
from driftcheck.remediate import (
    RemediateError,
    RemediationAdvice,
    generate_advice,
    generate_all_advice,
)


def _ok(name: str = "svc") -> DriftResult:
    return DriftResult(service=name, mismatches=[])


def _drifted(name: str = "svc", mismatches=None) -> DriftResult:
    if mismatches is None:
        mismatches = [("image", "nginx:1.25", "nginx:1.24")]
    return DriftResult(service=name, mismatches=mismatches)


# --- generate_advice ---

def test_generate_advice_no_drift_returns_empty_suggestions():
    advice = generate_advice(_ok("web"))
    assert advice.service == "web"
    assert not advice.has_suggestions


def test_generate_advice_drift_returns_suggestions():
    result = _drifted("api", [("image", "app:2", "app:1")])
    advice = generate_advice(result)
    assert advice.service == "api"
    assert len(advice.suggestions) == 1
    assert "image" in advice.suggestions[0]


def test_generate_advice_missing_live_key():
    result = _drifted("db", [("replicas", 3, None)])
    advice = generate_advice(result)
    assert "missing from live state" in advice.suggestions[0]
    assert "replicas" in advice.suggestions[0]


def test_generate_advice_multiple_mismatches():
    mismatches = [
        ("image", "img:2", "img:1"),
        ("replicas", 3, 1),
    ]
    advice = generate_advice(_drifted("svc", mismatches))
    assert len(advice.suggestions) == 2


def test_generate_advice_raises_on_non_drift_result():
    with pytest.raises(RemediateError):
        generate_advice("not a result")  # type: ignore


# --- RemediationAdvice.__str__ ---

def test_str_no_suggestions():
    advice = RemediationAdvice(service="svc", suggestions=[])
    assert "No remediation needed" in str(advice)


def test_str_with_suggestions():
    advice = RemediationAdvice(service="svc", suggestions=["fix image"])
    text = str(advice)
    assert "svc" in text
    assert "fix image" in text


# --- generate_all_advice ---

def test_generate_all_advice_skips_ok_results():
    results = [_ok("a"), _ok("b")]
    advice_list = generate_all_advice(results)
    assert advice_list == []


def test_generate_all_advice_includes_drifted():
    results = [_ok("a"), _drifted("b"), _drifted("c")]
    advice_list = generate_all_advice(results)
    assert len(advice_list) == 2
    assert {a.service for a in advice_list} == {"b", "c"}


def test_generate_all_advice_empty_input():
    assert generate_all_advice([]) == []
