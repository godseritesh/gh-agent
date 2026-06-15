"""EOD email notification via SMTP.

Sends a markdown-formatted daily summary to the user's Gmail inbox.
Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars.

Gmail setup: enable 2FA, create App Password at
https://myaccount.google.com/apppasswords
"""

from __future__ import annotations

import os
import smtplib
from datetime import UTC, datetime
from email.mime.text import MIMEText
from typing import Any


def build_summary(state: dict[str, Any]) -> str:
    """Build markdown email body from agent state."""
    shipped = state.get("shipped_today", [])
    repos_seen = state.get("repos_seen_today", [])
    date = datetime.now(UTC).strftime("%Y-%m-%d")

    lines = [f"# Agent Daily Summary — {date}", ""]

    if not shipped:
        lines.append("_No changes shipped today._")
        lines.append("")
        if repos_seen:
            lines.append(f"Repos researched: {', '.join(repos_seen)}.")
    else:
        lines.append(f"**{len(shipped)} change(s) shipped today:**")
        lines.append("")
        for entry in shipped:
            lines.append(f"- **{entry.get('title', 'Change')}**")
            lines.append(f"  - Repo: `{entry.get('repo', '?')}`")
            lines.append(f"  - Category: {entry.get('category', 'improvement')}")
            lines.append(f"  - PR: {entry.get('pr_url', 'N/A')}")
            lines.append("")

    budget = state.get("token_budget", {})
    tokens_used = budget.get("tokens_used", 0)
    daily_limit = budget.get("daily_limit", 30000)
    pct = 100 * tokens_used // daily_limit if daily_limit else 0
    lines.append(f"**Token usage:** {tokens_used}/{daily_limit} ({pct}%)")
    lines.append("")
    lines.append("---")
    lines.append(f"Sent by gh-agent at {datetime.now(UTC).strftime('%H:%M:%S UTC')}")

    return "\n".join(lines)


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Send email via SMTP. Requires env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    recipient = to or os.environ.get("SMTP_TO", user)
    sender_email = os.environ.get("SMTP_FROM", recipient)

    if not user or not password:
        print("  SMTP credentials not configured, skipping email")
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"gh-agent <{sender_email}>"
    msg["To"] = recipient

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        print(f"  Email sent to {recipient}")
        return True
    except smtplib.SMTPException as e:
        print(f"  Email failed: {e}")
        return False
