"""EOD email notification via Brevo Transactional Email API.

Sends a daily summary to the user's Gmail inbox.
Requires BREVO_API_KEY env var (same value used as SMTP_PASS).
Optionally BREVO_FROM (verified sender email) and BREVO_TO (recipient).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx


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
    """Send email via Brevo Transactional Email API.

    Requires env vars: BREVO_API_KEY (the API key), BREVO_FROM (verified sender email).
    BREVO_TO (recipient) defaults to BREVO_FROM if not set.
    Also falls back to SMTP_HOST/PORT/USER/PASS/BREVO_FROM for backward compat.
    """
    api_key = (
        os.environ.get("BREVO_API_KEY")
        or os.environ.get("SMTP_PASS", "")
    )
    from_email = os.environ.get("BREVO_FROM") or os.environ.get("SMTP_FROM", "")
    to_email = to or os.environ.get("BREVO_TO") or os.environ.get("SMTP_TO", "")

    if not api_key or not from_email or not to_email:
        print(f"  Missing config: api_key={'yes' if api_key else 'no'}, "
              f"from={'yes' if from_email else 'no'}, to={'yes' if to_email else 'no'}")
        return False

    payload = {
        "sender": {"name": "gh-agent", "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    try:
        with httpx.Client() as client:
            resp = client.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                msg_id = resp.json().get("messageId", "")
                print(f"  Email sent to {to_email} (msgId: {msg_id})")
                return True
            else:
                print(f"  Email failed ({resp.status_code}): {resp.text[:300]}")
                return False
    except Exception as e:
        print(f"  Email failed: {e}")
        return False
