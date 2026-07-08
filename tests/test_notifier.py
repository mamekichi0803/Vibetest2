import os

import pytest

from opera_schedule_tracker.models import Performance
from opera_schedule_tracker.notifier import (
    DEFAULT_RECIPIENT,
    SmtpConfig,
    build_email_body,
    send_update_email,
)
from opera_schedule_tracker.state import Diff


def make_performance(title="Carmen"):
    return Performance(
        opera_house="Test Opera",
        title=title,
        start_date="2026-09-01",
        venue="Main Hall",
        url="https://x/1",
    )


def test_build_email_body_includes_all_sections():
    diff = Diff(
        added=[make_performance("New Show")],
        removed=[make_performance("Old Show")],
        changed=[(make_performance("Changed Show"), make_performance("Changed Show"))],
    )
    body = build_email_body(diff)
    assert "New Show" in body
    assert "Old Show" in body
    assert "Changed Show" in body
    assert "新規追加された公演" in body
    assert "削除・中止された公演" in body
    assert "内容が変更された公演" in body


def test_smtp_config_from_env_returns_none_without_credentials(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert SmtpConfig.from_env() is None


def test_smtp_config_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USE_SSL", "false")

    config = SmtpConfig.from_env()

    assert config.host == "smtp.example.com"
    assert config.port == 587
    assert config.username == "user@example.com"
    assert config.password == "secret"
    assert config.use_ssl is False
    assert config.sender == "user@example.com"


def test_smtp_config_from_env_treats_empty_string_as_unset(monkeypatch):
    # GitHub Actions sets `env: SMTP_PORT: ${{ secrets.SMTP_PORT }}` to ""
    # (not omitted) when that secret isn't configured, so `.get(key,
    # default)` alone wouldn't fall back — this reproduces that and
    # guards against the ValueError it used to cause in int(...).
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("SMTP_USE_SSL", "")
    monkeypatch.setenv("SMTP_SENDER", "")

    config = SmtpConfig.from_env()

    assert config.host == "smtp.gmail.com"
    assert config.port == 465
    assert config.use_ssl is True
    assert config.sender == "user@example.com"


def test_send_update_email_uses_default_recipient_when_env_var_is_empty_string(
    monkeypatch,
):
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("RECIPIENT_EMAIL", "")

    import opera_schedule_tracker.notifier as notifier_module

    class FakeSmtp:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, username, password):
            pass

        def send_message(self, message):
            self.sent = message

    fake = FakeSmtp(None, None)
    monkeypatch.setattr(notifier_module.smtplib, "SMTP_SSL", lambda host, port: fake)

    diff = Diff(added=[make_performance()], removed=[], changed=[])
    send_update_email(diff)

    assert fake.sent["To"] == DEFAULT_RECIPIENT


def test_send_update_email_skips_when_diff_empty(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    sent = send_update_email(Diff(added=[], removed=[], changed=[]))
    assert sent is False


def test_send_update_email_skips_without_smtp_credentials(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    diff = Diff(added=[make_performance()], removed=[], changed=[])
    sent = send_update_email(diff)
    assert sent is False


def test_send_update_email_sends_via_smtp(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    sent_messages = []

    class FakeSmtp:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, username, password):
            pass

        def send_message(self, message):
            sent_messages.append(message)

    import opera_schedule_tracker.notifier as notifier_module

    monkeypatch.setattr(notifier_module.smtplib, "SMTP_SSL", FakeSmtp)

    diff = Diff(added=[make_performance()], removed=[], changed=[])
    sent = send_update_email(diff)

    assert sent is True
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == DEFAULT_RECIPIENT
