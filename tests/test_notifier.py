"""Tests for driftcheck.notifier."""
from __future__ import annotations

import json
import smtplib
from io import BytesIO
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.comparator import DriftResult
from driftcheck.notifier import (
    NotifyError,
    email_notifier,
    webhook_notifier,
)


def _ok(name: str = "svc") -> DriftResult:
    return DriftResult(service_name=name, drifted=False, mismatches={})


def _drifted(name: str = "svc") -> DriftResult:
    return DriftResult(service_name=name, drifted=True, mismatches={"image": ("a", "b")})


# ---------------------------------------------------------------------------
# email_notifier
# ---------------------------------------------------------------------------

def test_email_notifier_raises_on_empty_recipients():
    with pytest.raises(NotifyError, match="recipient"):
        email_notifier(host="localhost", sender="a@b.com", recipients=[])


def test_email_notifier_does_not_send_when_no_drift():
    notifier = email_notifier(host="localhost", sender="a@b.com", recipients=["x@y.com"])
    with patch("smtplib.SMTP") as mock_smtp:
        notifier([_ok("web"), _ok("db")])
        mock_smtp.assert_not_called()


def test_email_notifier_sends_on_drift():
    notifier = email_notifier(host="localhost", sender="a@b.com", recipients=["x@y.com"])
    mock_smtp_instance = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp_instance) as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp_instance
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        notifier([_drifted("web")])
        mock_smtp_instance.send_message.assert_called_once()


def test_email_notifier_raises_notify_error_on_smtp_failure():
    notifier = email_notifier(host="localhost", sender="a@b.com", recipients=["x@y.com"])
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = smtplib.SMTPException("conn refused")
        with pytest.raises(NotifyError, match="Failed to send"):
            notifier([_drifted("web")])


def test_email_notifier_logs_in_when_credentials_provided():
    notifier = email_notifier(
        host="smtp.example.com",
        sender="a@b.com",
        recipients=["x@y.com"],
        username="user",
        password="pass",
    )
    mock_smtp_instance = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp_instance
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        notifier([_drifted()])
        mock_smtp_instance.login.assert_called_once_with("user", "pass")


# ---------------------------------------------------------------------------
# webhook_notifier
# ---------------------------------------------------------------------------

def test_webhook_notifier_does_not_post_when_no_drift():
    notifier = webhook_notifier("http://example.com/hook")
    with patch("urllib.request.urlopen") as mock_open:
        notifier([_ok()])
        mock_open.assert_not_called()


def test_webhook_notifier_posts_json_on_drift():
    notifier = webhook_notifier("http://example.com/hook")
    captured: list = []

    def fake_urlopen(req, timeout):
        captured.append(req)
        return MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        notifier([_drifted("api"), _ok("db")])

    assert len(captured) == 1
    payload = json.loads(captured[0].data)
    assert payload["drift_count"] == 1
    assert payload["services"][0]["name"] == "api"


def test_webhook_notifier_raises_on_request_failure():
    notifier = webhook_notifier("http://example.com/hook")
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(NotifyError, match="Webhook POST failed"):
            notifier([_drifted()])
