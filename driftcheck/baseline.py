"""Baseline management: record and compare against a known-good state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

BASELINE_VERSION = 1


class BaselineError(Exception):
    """Raised when baseline operations fail."""


def save_baseline(services: dict[str, Any], path: str) -> None:
    """Persist a baseline snapshot to *path* as JSON.

    Args:
        services: Mapping of service name -> normalised state dict.
        path: Filesystem path to write the baseline file.

    Raises:
        BaselineError: If the file cannot be written.
    """
    payload = {
        "version": BASELINE_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except OSError as exc:
        raise BaselineError(f"Could not write baseline to {path!r}: {exc}") from exc


def load_baseline(path: str) -> dict[str, Any]:
    """Load a previously saved baseline from *path*.

    Returns:
        The ``services`` mapping stored in the baseline file.

    Raises:
        BaselineError: If the file is missing, unreadable, or malformed.
    """
    if not os.path.exists(path):
        raise BaselineError(f"Baseline file not found: {path!r}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"Invalid JSON in baseline {path!r}: {exc}") from exc
    except OSError as exc:
        raise BaselineError(f"Could not read baseline {path!r}: {exc}") from exc

    if not isinstance(data, dict) or "services" not in data:
        raise BaselineError(
            f"Baseline {path!r} is missing required 'services' key."
        )
    return data["services"]


def baseline_metadata(path: str) -> dict[str, Any]:
    """Return metadata (version, recorded_at) from a baseline file without
    loading the full service payload.

    Raises:
        BaselineError: If the file cannot be read or parsed.
    """
    if not os.path.exists(path):
        raise BaselineError(f"Baseline file not found: {path!r}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        raise BaselineError(f"Could not read baseline metadata from {path!r}: {exc}") from exc
    return {
        "version": data.get("version"),
        "recorded_at": data.get("recorded_at"),
    }
