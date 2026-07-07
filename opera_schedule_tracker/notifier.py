"""Compose and send the update email."""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from opera_schedule_tracker.models import Performance
from opera_schedule_tracker.state import Diff

logger = logging.getLogger(__name__)

DEFAULT_RECIPIENT = "shinmotoi2000@gmail.com"


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    sender: str | None = None

    @classmethod
    def from_env(cls) -> "SmtpConfig | None":
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        username = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        if not username or not password:
            return None
        return cls(
            host=host,
            port=int(os.environ.get("SMTP_PORT", "465")),
            username=username,
            password=password,
            use_ssl=os.environ.get("SMTP_USE_SSL", "true").lower() != "false",
            sender=os.environ.get("SMTP_SENDER", username),
        )


def _format_performance(p: Performance) -> str:
    line = f"  - [{p.opera_house}] {p.title} — {p.start_date}"
    if p.venue:
        line += f" ({p.venue})"
    if p.url:
        line += f"\n    {p.url}"
    return line


def build_email_body(diff: Diff) -> str:
    lines: list[str] = []
    lines.append("オペラハウス公演スケジュール更新のお知らせ")
    lines.append("=" * 40)
    lines.append("")

    if diff.added:
        lines.append(f"■ 新規追加された公演 ({len(diff.added)}件)")
        for p in sorted(diff.added, key=lambda p: (p.opera_house, p.start_date)):
            lines.append(_format_performance(p))
        lines.append("")

    if diff.removed:
        lines.append(f"■ 削除・中止された公演 ({len(diff.removed)}件)")
        for p in sorted(diff.removed, key=lambda p: (p.opera_house, p.start_date)):
            lines.append(_format_performance(p))
        lines.append("")

    if diff.changed:
        lines.append(f"■ 内容が変更された公演 ({len(diff.changed)}件)")
        for old, new in sorted(
            diff.changed, key=lambda pair: (pair[1].opera_house, pair[1].start_date)
        ):
            lines.append(f"  - [{new.opera_house}] {new.title} — {new.start_date}")
            if old.venue != new.venue:
                lines.append(f"    会場: {old.venue} -> {new.venue}")
            if old.url != new.url:
                lines.append(f"    URL: {old.url} -> {new.url}")
        lines.append("")

    return "\n".join(lines)


def send_update_email(diff: Diff, recipient: str | None = None) -> bool:
    """Send the diff email. Returns True if an email was sent."""
    if diff.is_empty:
        logger.info("No schedule changes detected; skipping email.")
        return False

    config = SmtpConfig.from_env()
    if config is None:
        logger.warning(
            "SMTP_USER / SMTP_PASSWORD not set; not sending email. "
            "Change summary:\n%s",
            build_email_body(diff),
        )
        return False

    recipient = recipient or os.environ.get("RECIPIENT_EMAIL", DEFAULT_RECIPIENT)

    message = EmailMessage()
    total = len(diff.added) + len(diff.removed) + len(diff.changed)
    message["Subject"] = f"[オペラ公演スケジュール] 更新あり ({total}件)"
    message["From"] = config.sender
    message["To"] = recipient
    message.set_content(build_email_body(diff))

    if config.use_ssl:
        smtp_cls = smtplib.SMTP_SSL
    else:
        smtp_cls = smtplib.SMTP

    with smtp_cls(config.host, config.port) as smtp:
        if not config.use_ssl:
            smtp.starttls()
        smtp.login(config.username, config.password)
        smtp.send_message(message)

    logger.info("Sent update email to %s (%d changes).", recipient, total)
    return True
