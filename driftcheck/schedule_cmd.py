"""CLI entry-point for the *schedule* sub-command.

Example usage::

    driftcheck schedule --config services.yaml --interval 120 --max-ticks 5
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from driftcheck.comparator import DriftResult, compare_service
from driftcheck.fetcher import FetchError, fetch_docker_service_state
from driftcheck.parser import ParseError, extract_service_definitions, load_yaml
from driftcheck.scheduler import Scheduler, SchedulerConfig
from driftcheck.sinks import json_file_sink, log_sink, stream_sink

log = logging.getLogger(__name__)


def build_schedule_parser(parent: argparse.ArgumentParser) -> None:
    """Attach *schedule* sub-command arguments to *parent*."""
    parent.add_argument(
        "--config", required=True, metavar="FILE", help="Path to services YAML."
    )
    parent.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Seconds between checks (default: 60).",
    )
    parent.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N ticks (default: run forever).",
    )
    parent.add_argument(
        "--json-log",
        metavar="FILE",
        default=None,
        help="Append JSON records to FILE on every tick.",
    )


def _build_check_fn(config_path: str):
    """Return a zero-argument callable that performs one full drift check."""

    def check() -> List[DriftResult]:
        try:
            raw = load_yaml(config_path)
            services = extract_service_definitions(raw)
        except ParseError as exc:
            log.error("Failed to parse config: %s", exc)
            return []

        results: List[DriftResult] = []
        for name, declared in services.items():
            try:
                live = fetch_docker_service_state(name)
            except FetchError as exc:
                log.warning("Could not fetch state for %s: %s", name, exc)
                continue
            results.append(compare_service(name, declared, live))
        return results

    return check


def run_schedule(args: argparse.Namespace) -> int:
    """Execute the schedule command; return an exit code."""
    sinks = [log_sink, stream_sink(sys.stdout)]
    if args.json_log:
        sinks.append(json_file_sink(Path(args.json_log)))

    cfg = SchedulerConfig(
        interval_seconds=args.interval,
        max_ticks=args.max_ticks,
        sinks=sinks,
    )
    try:
        cfg.validate()
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid scheduler config: {exc}", file=sys.stderr)
        return 2

    scheduler = Scheduler(_build_check_fn(args.config), cfg)
    try:
        scheduler.run()
    except KeyboardInterrupt:
        pass
    return 0
