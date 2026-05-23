"""CLI sub-command: export drift results to a file or stdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from driftcheck.comparator import DriftResult, compare_service
from driftcheck.exporter import ExportError, export_results, SUPPORTED_FORMATS
from driftcheck.fetcher import FetchError, fetch_docker_service_state
from driftcheck.parser import ParseError, load_yaml, extract_service_definitions


def build_export_parser(parent: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:  # noqa: E501
    kwargs = dict(
        description="Export drift-check results to JSON, CSV, or text.",
    )
    if parent is not None:
        parser = parent.add_parser("export", **kwargs)
    else:
        parser = argparse.ArgumentParser(prog="driftcheck export", **kwargs)

    parser.add_argument("config", help="Path to the service definition YAML file.")
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=SUPPORTED_FORMATS,
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output",
        default=None,
        help="Write output to this file instead of stdout.",
    )
    return parser


def run_export(args: argparse.Namespace) -> int:
    """Execute the export sub-command.

    Returns:
        0 — no drift detected.
        1 — drift detected.
        2 — configuration / fetch error.
    """
    try:
        raw = load_yaml(args.config)
        services = extract_service_definitions(raw)
    except (ParseError, FileNotFoundError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    results: List[DriftResult] = []
    for name, declared in services.items():
        try:
            live = fetch_docker_service_state(name)
        except FetchError as exc:
            print(f"[warn] {exc}", file=sys.stderr)
            live = {}
        results.append(compare_service(name, declared, live))

    try:
        output = export_results(results, args.fmt)
    except ExportError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    return 1 if any(r.drifted for r in results) else 0
