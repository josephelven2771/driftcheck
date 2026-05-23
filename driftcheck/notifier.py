"""Notification dispatch for drift detection results."""
from __future__ import annotations

import smtplib
import json
from email.message import EmailMessage
from typing import Callable, List, Optional

from driftcheck.comparator import DriftResult


class NotifyError(Exception):
    """Raised when a notification cannot be dispatched."""


NotifyFn = Callable[[List[DriftResult]], None]


def _drifted(results: List[DriftResult]) -> List[DriftResult]:
    return [r for r in results if r.drifted]


def email_notifier(
    *,
    host: str,
    port: int = 25,
    sender: str,
    recipients: List[str],
    subject_prefix: str = "[driftcheck]",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> NotifyFn:
    """Return a notifier that sends an e-mail summary when drift is found."""

    if not recipients:
        raise NotifyError("email_notifier requires at least one recipient")

    def _notify(results: List[DriftResult]) -> None:
        drifted = _drifted(results)
        if not drifted:
            return

        lines = [f"Drift detected in {len(drifted)} service(s):\n"]
        for r in drifted:
            lines.append(str(r))

        body = "\n".join(lines)
        subject = f"{subject_prefix} {len(drifted)} service(s) drifted"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        try:
            with smtplib.SMTP(host, port) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
        except smtplib.SMTPException as exc:
            raise NotifyError(f"Failed to send e-mail: {exc}") from exc

    return _notify


def webhook_notifier(url: str, *, timeout: int = 10) -> NotifyFn:
    """Return a notifier that POSTs a JSON payload to *url* when drift is found."""
    try:
        import urllib.request
    except ImportError as exc:  # pragma: no cover
        raise NotifyError("urllib is unavailable") from exc

    def _notify(results: List[DriftResult]) -> None:
        drifted = _drifted(results)
        if not drifted:
            return

        payload = json.dumps(
            {
                "drift_count": len(drifted),
                "services": [
                    {
                        "name": r.service_name,
                        "mismatches": r.mismatches,
                    }
                    for r in drifted
                ],
            }
        ).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout):
                pass
        except Exception as exc:
            raise NotifyError(f"Webhook POST failed: {exc}") from exc

    return _notify
