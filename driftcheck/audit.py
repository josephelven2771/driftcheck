"""Audit log: records drift-check events to a structured JSONL file."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from driftcheck.comparator import DriftResult


class AuditError(Exception):
    """Raised when an audit operation fails."""


AUDIT_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit_entry(
    path: str | os.PathLike,
    results: List[DriftResult],
    *,
    run_id: Optional[str] = None,
) -> None:
    """Append a single audit entry (one line of JSONL) to *path*.

    Each entry records the timestamp, an optional run_id, a summary count,
    and per-service drift details.
    """
    drifted = [r for r in results if r.drifted]
    entry = {
        "version": AUDIT_VERSION,
        "recorded_at": _utc_now(),
        "run_id": run_id,
        "total_services": len(results),
        "drifted_count": len(drifted),
        "services": [
            {
                "name": r.service_name,
                "drifted": r.drifted,
                "mismatches": r.mismatches,
            }
            for r in results
        ],
    }
    try:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        raise AuditError(f"Failed to write audit log to {path!r}: {exc}") from exc


def load_audit_log(path: str | os.PathLike) -> List[dict]:
    """Read all entries from a JSONL audit log and return them as a list."""
    dest = Path(path)
    if not dest.exists():
        raise AuditError(f"Audit log not found: {path!r}")
    entries: List[dict] = []
    try:
        with dest.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise AuditError(
                        f"Invalid JSON on line {lineno} of {path!r}: {exc}"
                    ) from exc
    except OSError as exc:
        raise AuditError(f"Failed to read audit log {path!r}: {exc}") from exc
    return entries
