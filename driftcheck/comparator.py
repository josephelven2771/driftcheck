"""Compares declared service definitions against live service state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftResult:
    """Holds the result of a drift comparison for a single service."""

    service_name: str
    drifted: bool = False
    missing_keys: list[str] = field(default_factory=list)
    mismatches: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.drifted:
            return f"[OK] {self.service_name}: no drift detected."
        lines = [f"[DRIFT] {self.service_name}:"]
        for key in self.missing_keys:
            lines.append(f"  - missing key in live state: '{key}'")
        for key, diff in self.mismatches.items():
            lines.append(
                f"  - '{key}': declared={diff['declared']!r}, "
                f"live={diff['live']!r}"
            )
        return "\n".join(lines)


def compare_service(
    service_name: str,
    declared: dict[str, Any],
    live: dict[str, Any],
) -> DriftResult:
    """Compare a declared service definition against its live state.

    Only keys present in *declared* are checked; extra keys in *live* are
    ignored (live services may expose additional runtime metadata).

    Args:
        service_name: Human-readable name for reporting.
        declared: The definition from the infrastructure YAML.
        live: The normalised live state from the fetcher.

    Returns:
        A DriftResult describing any detected drift.
    """
    result = DriftResult(service_name=service_name)

    for key, declared_value in declared.items():
        if key not in live:
            result.missing_keys.append(key)
            result.drifted = True
            continue

        live_value = live[key]

        if not _values_match(declared_value, live_value):
            result.mismatches[key] = {"declared": declared_value, "live": live_value}
            result.drifted = True

    return result


def _values_match(declared: Any, live: Any) -> bool:
    """Return True if declared and live values are considered equivalent."""
    if isinstance(declared, list) and isinstance(live, list):
        return sorted(str(i) for i in declared) == sorted(str(i) for i in live)
    if isinstance(declared, dict) and isinstance(live, dict):
        return all(
            k in live and _values_match(v, live[k]) for k, v in declared.items()
        )
    return declared == live
