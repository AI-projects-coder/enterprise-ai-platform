

import asyncio
import logging
import os

import resend

logger = logging.getLogger("app.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")


def _is_configured() -> bool:
    return bool(RESEND_API_KEY)


def _send_sync(to: str, subject: str, html: str) -> None:
    resend.api_key = RESEND_API_KEY
    resend.Emails.send({"from": RESEND_FROM_EMAIL, "to": to, "subject": subject, "html": html})


async def _send(to: str, subject: str, html: str) -> None:
    """Resend's SDK is synchronous under the hood (like google-cloud-storage's
    client) — run it in a thread so it doesn't block the event loop. Degrades
    gracefully (logs and returns) if RESEND_API_KEY isn't set OR if the send
    itself fails — same reasoning as Jira: a broken email provider shouldn't
    take down ticket creation."""
    if not _is_configured():
        logger.warning("resend_not_configured", extra={"to": to, "subject": subject})
        return
    try:
        await asyncio.to_thread(_send_sync, to, subject, html)
    except Exception:
        logger.exception("email_send_failed", extra={"to": to, "subject": subject})


async def send_ticket_raised_email(to: str, ticket_id: str) -> None:
    await _send(
        to,
        "We've received your issue",
        f"<p>Thanks for raising this — your ticket ID is <strong>{ticket_id}</strong>.</p>"
        f"<p>You'll get an email once it's resolved.</p>",
    )


async def send_ticket_resolved_email(to: str, ticket_id: str) -> None:
    await _send(
        to,
        "Your issue has been resolved",
        f"<p>The issue you raised (ticket <strong>{ticket_id}</strong>) has been resolved.</p>"
        f"<p>Please log in and check.</p>",
    )