"""Remediation advice generator for detected drift."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from driftcheck.comparator import DriftResult


class RemediateError(Exception):
    """Raised when remediation advice cannot be generated."""


@dataclass
class RemediationAdvice:
    service: str
    suggestions: List[str] = field(default_factory=list)

    @property
    def has_suggestions(self) -> bool:
        return bool(self.suggestions)

    def __str__(self) -> str:
        if not self.has_suggestions:
            return f"[{self.service}] No remediation needed."
        lines = [f"[{self.service}] Remediation suggestions:"]
        for suggestion in self.suggestions:
            lines.append(f"  - {suggestion}")
        return "\n".join(lines)


def _suggestion_for_key(key: str, declared, live) -> str:
    if live is None:
        return (
            f"Key '{key}' is declared as {declared!r} but missing from live state. "
            f"Ensure the service exposes this configuration."
        )
    return (
        f"Key '{key}' is {live!r} in live state but declared as {declared!r}. "
        f"Update the running service or revise the declaration."
    )


def generate_advice(result: DriftResult) -> RemediationAdvice:
    """Return a RemediationAdvice for a single DriftResult."""
    if not isinstance(result, DriftResult):
        raise RemediateError(f"Expected DriftResult, got {type(result).__name__}")

    suggestions = [
        _suggestion_for_key(key, declared, live)
        for key, declared, live in result.mismatches
    ]
    return RemediationAdvice(service=result.service, suggestions=suggestions)


def generate_all_advice(results: List[DriftResult]) -> List[RemediationAdvice]:
    """Return remediation advice for every result that has drift."""
    return [
        generate_advice(r)
        for r in results
        if r.drifted
    ]
