"""Built-in result sinks for the scheduler.

A *sink* is any callable that accepts a list of :class:`~driftcheck.comparator.DriftResult`
objects and performs some side-effect (logging, writing a file, etc.).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import List, TextIO

from driftcheck.comparator import DriftResult

log = logging.getLogger(__name__)


def log_sink(results: List[DriftResult]) -> None:
    """Write drift results to the Python logging system."""
    drifted = [r for r in results if r.drifted]
    if not drifted:
        log.info("No drift detected across %d service(s).", len(results))
        return
    log.warning("Drift detected in %d / %d service(s).", len(drifted), len(results))
    for result in drifted:
        log.warning("  %s", result)


def stream_sink(stream: TextIO = sys.stdout) -> "_StreamSink":
    """Return a sink that writes a human-readable report to *stream*."""
    return _StreamSink(stream)


class _StreamSink:
    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def __call__(self, results: List[DriftResult]) -> None:
        drifted = [r for r in results if r.drifted]
        if not drifted:
            self._stream.write(f"[driftcheck] OK — {len(results)} service(s) in sync.\n")
            return
        self._stream.write(
            f"[driftcheck] DRIFT in {len(drifted)}/{len(results)} service(s):\n"
        )
        for r in drifted:
            self._stream.write(f"  {r}\n")


def json_file_sink(path: Path) -> "_JsonFileSink":
    """Return a sink that appends a JSON record per tick to *path*."""
    return _JsonFileSink(path)


class _JsonFileSink:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def __call__(self, results: List[DriftResult]) -> None:
        import datetime

        record = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "total": len(results),
            "drifted": [
                {"service": r.service_name, "fields": r.drifted_fields}
                for r in results
                if r.drifted
            ],
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
