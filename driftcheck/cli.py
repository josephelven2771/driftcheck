"""Command-line interface for driftcheck."""

import argparse
import sys
from typing import List, Optional

from driftcheck.parser import load_yaml, extract_service_definitions, ParseError
from driftcheck.fetcher import fetch_docker_service_state, FetchError
from driftcheck.comparator import compare_service
from driftcheck.reporter import print_report, format_summary


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="driftcheck",
        description="Detect configuration drift between running services and declared infrastructure.",
    )
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to the YAML infrastructure definition file.",
    )
    parser.add_argument(
        "--service",
        metavar="NAME",
        action="append",
        dest="services",
        help="Limit checks to specific service(s). Can be repeated.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-service output; only print the summary.",
    )
    return parser


def run(argv: Optional[List[str]] = None) -> int:
    """Main entry point. Returns an exit code (0 = no drift, 1 = drift, 2 = error)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw = load_yaml(args.config)
    except ParseError as exc:
        print(f"driftcheck: error reading config: {exc}", file=sys.stderr)
        return 2

    try:
        service_defs = extract_service_definitions(raw)
    except ParseError as exc:
        print(f"driftcheck: error parsing service definitions: {exc}", file=sys.stderr)
        return 2

    if args.services:
        unknown = set(args.services) - set(service_defs)
        if unknown:
            print(
                f"driftcheck: unknown service(s): {', '.join(sorted(unknown))}",
                file=sys.stderr,
            )
            return 2
        service_defs = {k: v for k, v in service_defs.items() if k in args.services}

    results = []
    for name, declared in service_defs.items():
        try:
            live = fetch_docker_service_state(name)
        except FetchError as exc:
            print(f"driftcheck: could not fetch state for '{name}': {exc}", file=sys.stderr)
            return 2
        results.append(compare_service(name, declared, live))

    exit_code = print_report(results, quiet=args.quiet)
    print(format_summary(results))
    return exit_code


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
