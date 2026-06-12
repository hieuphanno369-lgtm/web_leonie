import json as json_lib
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from automation.models import JobConfig, RunResult


def _discord(message: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set")
    payload = json_lib.dumps({"content": message}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10):
        pass


def _email(subject: str, body: str, recipients: list[str], attachments: list[str]) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST not set")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pw = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", user or "")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    for path in attachments:
        with open(path, "rb") as fh:
            data = fh.read()
        msg.add_attachment(data, maintype="application", subtype="octet-stream",
                           filename=os.path.basename(path))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if user and pw:
            s.login(user, pw)
        s.send_message(msg)


def _format(config: JobConfig, result: RunResult) -> tuple[str, str]:
    status = result.status.upper()
    subject = f"[Automation] {config.name} — {status}"
    lines = [f"Job: {config.name}", f"Status: {status}",
             f"Rows: {result.rows}", f"Duration: {result.duration_seconds:.1f}s"]
    if result.output_files:
        lines.append("Files:\n" + "\n".join(result.output_files))
    if result.error:
        lines.append(f"Detail: {result.error}")
    return subject, "\n".join(lines)


def send(config: JobConfig, result: RunResult) -> list[str]:
    """Send Discord + Email notifications. Never raises; returns warnings."""
    warnings: list[str] = []
    subject, body = _format(config, result)
    if config.notify.discord_enabled:
        try:
            _discord(body)
        except Exception as e:
            warnings.append(f"Discord notify failed: {e}")
    email = config.notify.email
    if email.enabled and email.recipients:
        attachments = []
        for f in result.output_files:
            try:
                if os.path.getsize(f) <= email.attach_max_bytes:
                    attachments.append(f)
            except OSError:
                pass
        try:
            _email(subject, body, email.recipients, attachments)
        except Exception as e:
            warnings.append(f"Email notify failed: {e}")
    return warnings
