"""Filter utilities for narrowing drift check results by service name or tag."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Iterable, List, Sequence

from driftcheck.comparator import DriftResult


class FilterError(Exception):
    """Raised when a filter pattern is invalid."""


def _validate_patterns(patterns: Sequence[str]) -> None:
    for p in patterns:
        if not p or p.isspace():
            raise FilterError(f"Invalid filter pattern: {p!r}")


def filter_by_name(
    results: Iterable[DriftResult],
    patterns: Sequence[str],
) -> List[DriftResult]:
    """Return only results whose service name matches at least one glob pattern.

    Args:
        results:  Iterable of DriftResult objects to filter.
        patterns: One or more glob-style patterns (e.g. ``"web*"``, ``"db"``).  An
                  empty sequence returns all results unchanged.

    Returns:
        Filtered list of DriftResult objects.

    Raises:
        FilterError: If any pattern is blank or whitespace-only.
    """
    patterns = list(patterns)
    if not patterns:
        return list(results)

    _validate_patterns(patterns)

    return [
        r for r in results
        if any(fnmatch(r.service_name, p) for p in patterns)
    ]


def filter_drifted(results: Iterable[DriftResult]) -> List[DriftResult]:
    """Return only results that have detected drift."""
    return [r for r in results if r.drifted]


def filter_ok(results: Iterable[DriftResult]) -> List[DriftResult]:
    """Return only results with no drift."""
    return [r for r in results if not r.drifted]
