"""CLI sub-command: audit  — view the drift audit log."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from driftcheck.audit import AuditError, load_audit_log


def build_audit_parser(subparsers=None) -> argparse.ArgumentParser:
    description = "Display entries from the drift audit log."
    if subparsers is not None:
        parser = subparsers.add_parser("audit", help=description, description=description)
    else:
        parser = argparse.ArgumentParser(prog="driftcheck audit", description=description)

    parser.add_argument(
        "log_file",
        help="Path to the JSONL audit log file.",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=None,
        metavar="N",
        help="Show only the last N entries.",
    )
    parser.add_argument(
        "--drifted-only",
        action="store_true",
        default=False,
        help="Only show entries where drift was detected.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    return parser


def run_audit(
    args: argparse.Namespace,
    *,
    stdout=None,
    stderr=None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr

    try:
        entries = load_audit_log(args.log_file)
    except AuditError as exc:
        print(f"audit error: {exc}", file=err)
        return 2

    if args.drifted_only:
        entries = [e for e in entries if e.get("drifted_count", 0) > 0]

    if args.last is not None:
        entries = entries[-args.last :]

    if not entries:
        print("No audit entries found.", file=out)
        return 0

    if args.output_format == "json":
        print(json.dumps(entries, indent=2), file=out)
        return 0

    # text format
    for entry in entries:
        recorded = entry.get("recorded_at", "unknown")
        total = entry.get("total_services", 0)
        drifted = entry.get("drifted_count", 0)
        run_id = entry.get("run_id") or "-"
        status = "DRIFT" if drifted else "OK"
        print(
            f"[{recorded}] run={run_id} status={status} "
            f"services={total} drifted={drifted}",
            file=out,
        )

    return 1 if any(e.get("drifted_count", 0) for e in entries) else 0
