"""CLI sub-command: print remediation advice for detected drift."""
from __future__ import annotations

import argparse
import sys
from typing import List

from driftcheck.parser import ParseError, load_yaml, extract_service_definitions
from driftcheck.fetcher import FetchError, fetch_docker_service_state
from driftcheck.comparator import compare_service
from driftcheck.remediate import generate_all_advice


def build_remediate_parser(parent: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = parent.add_parser(
        "remediate",
        help="Show remediation advice for drifted services.",
    )
    p.add_argument("config", help="Path to the infrastructure YAML definition.")
    p.add_argument(
        "--services",
        nargs="+",
        metavar="SERVICE",
        help="Limit advice to specific service names.",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable coloured output.",
    )
    return p


def run_remediate(
    args: argparse.Namespace,
    out=sys.stdout,
    err=sys.stderr,
) -> int:
    """Execute the remediate sub-command. Returns an exit code."""
    try:
        raw = load_yaml(args.config)
        declared = extract_service_definitions(raw)
    except ParseError as exc:
        print(f"Parse error: {exc}", file=err)
        return 2

    if args.services:
        declared = {k: v for k, v in declared.items() if k in args.services}

    results = []
    for name, definition in declared.items():
        try:
            live = fetch_docker_service_state(name)
        except FetchError:
            live = {}
        results.append(compare_service(name, definition, live))

    advice_list = generate_all_advice(results)

    if not advice_list:
        print("No remediation needed — all services are in sync.", file=out)
        return 0

    for advice in advice_list:
        print(str(advice), file=out)

    return 1
