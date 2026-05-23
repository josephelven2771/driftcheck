"""CLI sub-command: notify — dispatch drift notifications."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from driftcheck.parser import ParseError, load_yaml, extract_service_definitions
from driftcheck.fetcher import FetchError, fetch_docker_service_state
from driftcheck.comparator import compare_service
from driftcheck.notifier import NotifyError, email_notifier, webhook_notifier


def build_notify_parser(parent: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    kwargs = dict(
        description="Check for drift and dispatch notifications.",
    )
    if parent is not None:
        parser = parent.add_parser("notify", **kwargs)
    else:
        parser = argparse.ArgumentParser(prog="driftcheck notify", **kwargs)

    parser.add_argument("config", help="Path to the YAML service definition file.")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--email",
        nargs="+",
        metavar="RECIPIENT",
        help="Send e-mail to one or more addresses.",
    )
    mode.add_argument(
        "--webhook",
        metavar="URL",
        help="POST a JSON payload to this URL.",
    )

    parser.add_argument("--smtp-host", default="localhost", metavar="HOST")
    parser.add_argument("--smtp-port", type=int, default=25, metavar="PORT")
    parser.add_argument("--smtp-sender", default="driftcheck@localhost", metavar="ADDR")
    parser.add_argument("--smtp-user", default=None, metavar="USER")
    parser.add_argument("--smtp-password", default=None, metavar="PASS")
    parser.add_argument(
        "--webhook-timeout", type=int, default=10, metavar="SEC"
    )
    return parser


def run_notify(args: argparse.Namespace) -> int:
    # --- load & compare ---
    try:
        raw = load_yaml(args.config)
        declared = extract_service_definitions(raw)
    except ParseError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    results = []
    for name, definition in declared.items():
        try:
            live = fetch_docker_service_state(name)
        except FetchError as exc:
            print(f"[warn] {name}: {exc}", file=sys.stderr)
            continue
        results.append(compare_service(name, definition, live))

    if not results:
        print("No services checked.", file=sys.stderr)
        return 2

    # --- build notifier ---
    try:
        if args.email:
            notifier = email_notifier(
                host=args.smtp_host,
                port=args.smtp_port,
                sender=args.smtp_sender,
                recipients=args.email,
                username=args.smtp_user,
                password=args.smtp_password,
            )
        else:
            notifier = webhook_notifier(
                args.webhook, timeout=args.webhook_timeout
            )
    except NotifyError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    # --- dispatch ---
    try:
        notifier(results)
    except NotifyError as exc:
        print(f"[error] notification failed: {exc}", file=sys.stderr)
        return 3

    drifted = [r for r in results if r.drifted]
    return 1 if drifted else 0
