"""Notification helpers (e-mail alerts for failed jobs)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Dict, Optional

from ..config import settings


async def send_error_email(subject: str, body: str) -> None:
    """Send an error notification if SMTP settings are configured."""

    if not settings.smtp_host or not settings.alert_email:
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_sender or settings.alert_email
    message["To"] = settings.alert_email
    message.set_content(body)

    def _send() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_username and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

    await asyncio.to_thread(_send)


async def notify_failure(context: Dict[str, str]) -> None:
    """High-level helper for job failure notifications."""

    subject = f"[AIO Suite] Job failure for {context.get('keyword', 'unknown keyword')}"
    body = "\n".join(f"{key}: {value}" for key, value in context.items())
    await send_error_email(subject, body)
