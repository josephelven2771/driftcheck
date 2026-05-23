"""Export drift results to various output formats (JSON, CSV, text)."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from driftcheck.comparator import DriftResult


class ExportError(Exception):
    """Raised when an export operation fails."""


SUPPORTED_FORMATS = ("json", "csv", "text")


def export_results(results: List[DriftResult], fmt: str) -> str:
    """Serialise *results* to the requested format string.

    Args:
        results: List of DriftResult objects to export.
        fmt: One of ``'json'``, ``'csv'``, or ``'text'``.

    Returns:
        A string representation of the results.

    Raises:
        ExportError: If *fmt* is not supported.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ExportError(
            f"Unsupported export format {fmt!r}. "
            f"Choose one of: {', '.join(SUPPORTED_FORMATS)}"
        )
    if fmt == "json":
        return _to_json(results)
    if fmt == "csv":
        return _to_csv(results)
    return _to_text(results)


def _to_json(results: List[DriftResult]) -> str:
    records = [
        {
            "service": r.service_name,
            "drifted": r.drifted,
            "mismatches": [
                {"key": k, "declared": d, "live": l}
                for k, d, l in r.mismatches
            ],
        }
        for r in results
    ]
    return json.dumps(records, indent=2)


def _to_csv(results: List[DriftResult]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["service", "drifted", "key", "declared", "live"])
    for r in results:
        if not r.mismatches:
            writer.writerow([r.service_name, r.drifted, "", "", ""])
        else:
            for key, declared, live in r.mismatches:
                writer.writerow([r.service_name, r.drifted, key, declared, live])
    return buf.getvalue()


def _to_text(results: List[DriftResult]) -> str:
    lines: List[str] = []
    for r in results:
        status = "DRIFT" if r.drifted else "OK"
        lines.append(f"[{status}] {r.service_name}")
        for key, declared, live in r.mismatches:
            lines.append(f"  {key}: declared={declared!r}  live={live!r}")
    return "\n".join(lines)
