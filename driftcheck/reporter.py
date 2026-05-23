"""Formats and outputs drift check results."""

from __future__ import annotations

import sys
from typing import IO

from driftcheck.comparator import DriftResult


def print_report(
    results: list[DriftResult],
    out: IO[str] = sys.stdout,
    err: IO[str] = sys.stderr,
) -> int:
    """Print a human-readable drift report and return an exit code.

    Args:
        results: List of DriftResult objects to report on.
        out: Output stream for passing services (default: stdout).
        err: Output stream for drifted services (default: stderr).

    Returns:
        0 if no drift detected across all services, 1 otherwise.
    """
    any_drift = False

    for result in results:
        if result.drifted:
            print(str(result), file=err)
            any_drift = True
        else:
            print(str(result), file=out)

    if any_drift:
        print(
            f"\nDrift detected in {sum(r.drifted for r in results)}/"
            f"{len(results)} service(s).",
            file=err,
        )
    else:
        print(f"\nAll {len(results)} service(s) are in sync.", file=out)

    return 1 if any_drift else 0


def format_summary(results: list[DriftResult]) -> str:
    """Return a compact one-line summary string for all results."""
    total = len(results)
    drifted = sum(r.drifted for r in results)
    ok = total - drifted
    return f"Services checked: {total} | OK: {ok} | Drifted: {drifted}"
