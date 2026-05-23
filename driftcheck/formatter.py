"""Output formatters for drift results (JSON, plain text, etc.)."""
from __future__ import annotations

import json
from typing import List

from driftcheck.comparator import DriftResult


class FormatError(Exception):
    """Raised when an unknown format is requested."""


_SUPPORTED_FORMATS = ("text", "json")


def format_results(results: List[DriftResult], fmt: str = "text") -> str:
    """Return *results* serialised in the requested *fmt*.

    Parameters
    ----------
    results:
        List of :class:`~driftcheck.comparator.DriftResult` instances.
    fmt:
        One of ``"text"`` or ``"json"``.

    Raises
    ------
    FormatError
        If *fmt* is not a recognised format name.
    """
    if fmt not in _SUPPORTED_FORMATS:
        raise FormatError(
            f"Unknown format {fmt!r}. Supported formats: {', '.join(_SUPPORTED_FORMATS)}"
        )
    if fmt == "json":
        return _format_json(results)
    return _format_text(results)


def _format_text(results: List[DriftResult]) -> str:
    lines: List[str] = []
    for r in results:
        if r.drifted:
            lines.append(f"[DRIFT]  {r.service_name}")
            for field, (declared, live) in r.differences.items():
                lines.append(f"         {field}: declared={declared!r} live={live!r}")
        else:
            lines.append(f"[OK]     {r.service_name}")
    return "\n".join(lines)


def _format_json(results: List[DriftResult]) -> str:
    payload = []
    for r in results:
        entry: dict = {"service": r.service_name, "drifted": r.drifted}
        if r.drifted:
            entry["differences"] = {
                field: {"declared": declared, "live": live}
                for field, (declared, live) in r.differences.items()
            }
        payload.append(entry)
    return json.dumps(payload, indent=2)
