"""Optional SMTP e-mail. Every attempt is logged in the database."""
import os
import smtplib
from email.mime.text import MIMEText

from .. import db


def send_email(to_addr, subject, body, user_id=None):
    """Send email via SMTP if configured; always log the attempt."""
    host = os.environ.get("SMTP_HOST", "").strip()
    status = "skipped_no_smtp"
    if host:
        try:
            port = int(os.environ.get("SMTP_PORT", "587"))
            user = os.environ.get("SMTP_USER", "")
            password = os.environ.get("SMTP_PASSWORD", "")
            from_addr = os.environ.get("SMTP_FROM", user or "noreply@signalsleuth.local")
            use_tls = os.environ.get("SMTP_USE_TLS", "1") == "1"
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = to_addr
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                if use_tls:
                    smtp.starttls()
                if user:
                    smtp.login(user, password)
                smtp.sendmail(from_addr, [to_addr], msg.as_string())
            status = "sent"
        except Exception as e:
            status = f"error:{e}"
    try:
        db.log_email(user_id, to_addr, subject, body, status)
    except Exception:
        pass
    return status.startswith("sent") or status == "skipped_no_smtp"
