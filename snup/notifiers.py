from __future__ import annotations

import os
import shutil
import smtplib
import subprocess
from email.message import EmailMessage


class EmailNotifier:
    """Send notification emails."""

    def __init__(self, config: dict):
        self.config = config

    def send(self, event: dict) -> None:
        to_address = self.config.get("to")
        if not to_address:
            return

        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        if not smtp_host:
            return

        msg = EmailMessage()
        msg["Subject"] = self.config.get(
            "subject") or f"Backup event: {event.get('job_id', 'unknown')}"
        msg["From"] = os.getenv("SMTP_FROM", smtp_user or "backup@example.com")
        msg["To"] = to_address
        msg.set_content(event.get("message", "Backup event"))

        try:
            with smtplib.SMTP(smtp_host, 587) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception:
            pass


class DesktopNotifier:
    """Send a local desktop notification if a graphical session is available."""

    def __init__(self, config: dict):
        self.config = config

    def send(self, event: dict) -> None:
        if not os.getenv("DISPLAY"):
            return

        notify_bin = shutil.which("notify-send")
        if not notify_bin:
            return

        title = self.config.get("title") or "Backup status"
        message = event.get("message", "Backup finished")
        subprocess.run([notify_bin, title, message], check=False)


def build_notifier(notifier_config: dict):
    notifier_type = (notifier_config.get("type") or "").lower()
    if notifier_type == "email":
        return EmailNotifier(notifier_config)
    if notifier_type == "desktop":
        return DesktopNotifier(notifier_config)
    return None
