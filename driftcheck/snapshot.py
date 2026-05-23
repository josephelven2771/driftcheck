"""Snapshot management: save and load drift-check state snapshots to/from disk."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


class SnapshotError(Exception):
    """Raised when a snapshot cannot be saved or loaded."""


_SNAPSHOT_VERSION = 1


def save_snapshot(path: str, state: dict[str, Any]) -> None:
    """Persist *state* as a JSON snapshot file at *path*.

    The file is written atomically (write to a temp file, then rename)
    so a crash mid-write does not corrupt an existing snapshot.
    """
    payload = {
        "version": _SNAPSHOT_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "services": state,
    }
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, path)
    except OSError as exc:
        raise SnapshotError(f"Could not write snapshot to '{path}': {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def load_snapshot(path: str) -> dict[str, Any]:
    """Load a previously saved snapshot from *path*.

    Returns the ``services`` mapping stored inside the snapshot.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except FileNotFoundError as exc:
        raise SnapshotError(f"Snapshot file not found: '{path}'") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"Snapshot file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SnapshotError(f"Could not read snapshot '{path}': {exc}") from exc

    if not isinstance(payload, dict) or "services" not in payload:
        raise SnapshotError("Snapshot file is missing the 'services' key.")

    version = payload.get("version", 0)
    if version != _SNAPSHOT_VERSION:
        raise SnapshotError(
            f"Unsupported snapshot version {version!r} (expected {_SNAPSHOT_VERSION})."
        )

    return payload["services"]


def snapshot_metadata(path: str) -> dict[str, Any]:
    """Return the top-level metadata (version, captured_at) without the full state."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Could not read snapshot metadata: {exc}") from exc
    return {k: v for k, v in payload.items() if k != "services"}
