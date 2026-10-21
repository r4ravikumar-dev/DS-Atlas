"""Email delivery adapters. SMTP for real delivery; `outbox` (development only) writes messages to a private local folder.
Message bodies containing links/codes are never written to application logs."""
from __future__ import annotations

import json
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from ..core.config import get_settings


class DeliveryError(Exception):
    pass


class NotConfigured(DeliveryError):
    pass


def transport_name() -> str:
    s = get_settings()
    if s.email_transport == "smtp" and s.smtp_host and s.smtp_from:
        return "smtp"
    if s.email_transport == "outbox" and s.environment != "production":
        return "outbox"
    return "disabled"


def send(to: str, subject: str, body: str) -> str:
    s = get_settings()
    t = transport_name()
    if t == "smtp":
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
                if s.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if s.smtp_username and s.smtp_password:
                    smtp.login(s.smtp_username, s.smtp_password.get_secret_value())
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as e:
            raise DeliveryError(f"SMTP delivery failed: {type(e).__name__}") from None
        return "sent"
    if t == "outbox":
        d = Path(s.storage_dir) / "outbox"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
        f.write_text(json.dumps({"to": to, "subject": subject, "body": body, "transport": "outbox (development only)"}, indent=2))
        f.chmod(0o600)
        return "sent"
    raise NotConfigured("No email transport is configured (set EMAIL_TRANSPORT=smtp and SMTP_* settings).")
