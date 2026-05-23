"""Snapshot-diff helpers: compare a live state dict against a saved snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceDiff:
    """Records what changed for a single service between two snapshots."""

    service: str
    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    changed: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def __str__(self) -> str:  # pragma: no cover
        lines = [f"Service '{self.service}':"]
        for k, v in self.added.items():
            lines.append(f"  + {k}: {v!r}")
        for k, v in self.removed.items():
            lines.append(f"  - {k}: {v!r}")
        for k, (old, new) in self.changed.items():
            lines.append(f"  ~ {k}: {old!r} -> {new!r}")
        return "\n".join(lines)


@dataclass
class SnapshotDiff:
    """Aggregate diff between two full state snapshots."""

    new_services: list[str] = field(default_factory=list)
    removed_services: list[str] = field(default_factory=list)
    service_diffs: list[ServiceDiff] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_services
            or self.removed_services
            or any(d.has_changes for d in self.service_diffs)
        )


def diff_snapshots(
    old: dict[str, Any],
    new: dict[str, Any],
) -> SnapshotDiff:
    """Compare *old* snapshot state to *new* snapshot state.

    Both arguments should be the ``services`` mappings returned by
    :func:`driftcheck.snapshot.load_snapshot`.
    """
    result = SnapshotDiff()

    old_keys = set(old)
    new_keys = set(new)

    result.new_services = sorted(new_keys - old_keys)
    result.removed_services = sorted(old_keys - new_keys)

    for service in sorted(old_keys & new_keys):
        diff = _diff_service(service, old[service], new[service])
        if diff.has_changes:
            result.service_diffs.append(diff)

    return result


def _diff_service(
    service: str,
    old_cfg: dict[str, Any],
    new_cfg: dict[str, Any],
) -> ServiceDiff:
    diff = ServiceDiff(service=service)
    all_keys = set(old_cfg) | set(new_cfg)
    for key in all_keys:
        if key not in old_cfg:
            diff.added[key] = new_cfg[key]
        elif key not in new_cfg:
            diff.removed[key] = old_cfg[key]
        elif old_cfg[key] != new_cfg[key]:
            diff.changed[key] = (old_cfg[key], new_cfg[key])
    return diff
