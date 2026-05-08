"""Simple SMTP email sender. Falls back to stdout if SMTP env vars aren't set."""
import os
import smtplib
from email.message import EmailMessage


def send_email(to: str, subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"[EMAIL FALLBACK] To: {to}\n  Subject: {subject}\n  Body: {body}")
        return False

    user = os.environ.get("SMTP_USER")
    pwd  = os.environ.get("SMTP_PASS")
    from_addr = os.environ.get("FROM_EMAIL", user or "noreply@habitflow.app")
    port = int(os.environ.get("SMTP_PORT", "587"))

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}  To: {to}  Subject: {subject}")
        return False
