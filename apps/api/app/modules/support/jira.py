import logging
import os

import httpx

logger = logging.getLogger("app.jira")

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY")

# Jira's default priority scheme names — capitalized, exact match required
# by their API. NOTE: unverified against a real Jira site yet — some
# projects use a different scheme entirely (P1-P4, Blocker/Critical/Major/
# Minor/Trivial, etc.). Confirm this mapping against your actual project's
# configured priority scheme once you have real credentials, the same way
# the GCS signing permission needed live verification before it could be
# trusted — this is that same category of "looks right on paper" risk.
PRIORITY_MAP = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "highest": "Highest",
}


def _is_configured() -> bool:
    return bool(JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN and JIRA_PROJECT_KEY)


async def create_jira_issue(
    summary: str, description: str, priority: str, reporter_email: str
) -> str | None:
    """Returns the created issue's key (e.g. "SUPPORT-42"), or None if Jira
    isn't configured. This runs inside a background task, not a live
    request a user is waiting on — so a missing or broken Jira integration
    should degrade gracefully, not crash the whole ticket-creation pipeline.
    A None jira_issue_key just means the ticket exists in our system
    without a Jira counterpart yet.

    reporter_email is NOT set as Jira's system Reporter field — that field
    can only reference a real, licensed Atlassian user, and our app's users
    aren't Jira users at all. Every issue this creates is authored by the
    one shared JIRA_EMAIL/JIRA_API_TOKEN identity, structurally, no matter
    who raised it in the app. The real reporter is written into the
    description body instead, which is the only place we can actually
    surface it."""
    if not _is_configured():
        logger.warning("jira_not_configured", extra={"summary": summary})
        return None

    # Jira Cloud's v3 API requires `description` in Atlassian Document
    # Format (ADF) — a structured JSON document, NOT a plain string. This is
    # the single most common mistake people make against this API; a bare
    # string here gets rejected outright by Jira.
    body = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Reported by: ", "marks": [{"type": "strong"}]},
                            {"type": "text", "text": reporter_email},
                        ],
                    },
                    {"type": "paragraph", "content": [{"type": "text", "text": description}]},
                ],
            },
            "issuetype": {"name": "Support"},
            "priority": {"name": PRIORITY_MAP[priority]},
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/issue",
                json=body,
                auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("jira_create_issue_failed", extra={"summary": summary})
            return None

    return response.json()["key"]


async def attach_files_to_issue(issue_key: str, files: list[tuple[str, bytes, str]]) -> None:
    """files: list of (filename, content, content_type). Attaching a file is
    a SEPARATE Jira API call from creating the issue — issue creation only
    ever accepts plain field values (text/JSON), never binary content, so
    this always needs its own request against the issue that already
    exists. Two things this endpoint specifically requires that the issue-
    creation call doesn't: multipart/form-data instead of JSON, and the
    `X-Atlassian-Token: no-check` header — Jira's attachment endpoint has
    its own CSRF check that assumes a browser session by default and
    rejects plain API calls without this header, even with valid auth."""
    if not _is_configured() or not files:
        return

    multipart_files = [("file", (filename, content, content_type)) for filename, content, content_type in files]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/attachments",
                files=multipart_files,
                headers={"X-Atlassian-Token": "no-check"},
                auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("jira_attach_files_failed", extra={"issue_key": issue_key})


async def get_jira_issue_status(issue_key: str) -> str | None:
    """Returns the issue's statusCategory KEY — always one of exactly three
    fixed values across any Jira project/workflow: 'new', 'indeterminate',
    or 'done' (verified live against KAN-7/KAN-8 before writing this) — NOT
    the literal status name ('To Do', 'Done', etc.), which varies per
    project and would be fragile to match against directly. Returns None if
    the lookup fails or Jira isn't configured."""
    if not _is_configured():
        return None

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}?fields=status",
                auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("jira_get_status_failed", extra={"issue_key": issue_key})
            return None

    return response.json()["fields"]["status"]["statusCategory"]["key"]