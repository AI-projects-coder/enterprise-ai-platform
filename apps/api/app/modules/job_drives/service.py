import re
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_gateway.service import Citation, generate_grounded
from app.modules.job_drives.models import JobDrive

ENTRY_LINE_RE = re.compile(r"^\d+\.\s", re.MULTILINE)


def _build_prompt(role: str, city: str, experience_band: str) -> str:
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return (
        f"Today's date is {today}. Using real, current web search results, find campus "
        f"recruitment drives and active hiring for the role '{role}' in {city}, for candidates "
        f"with {experience_band} years of experience, within the NEXT TWO WEEKS from today.\n\n"
        "Structure the response into exactly two sections, in this order, each with a markdown "
        "heading:\n\n"
        "## Fixed-Date Drives\n"
        "Only real walk-in/campus drives with a confirmed, specific event date. Numbered list, "
        "chronological (soonest first), each entry in this exact shape:\n"
        "N. **Date: <exact date, e.g. 'August 12, 2026'>** — Company/Organization — Location — "
        "brief eligibility note\n"
        "If none were found, write exactly: 'No fixed-date drives found for this search.'\n\n"
        "## Ongoing Applications\n"
        "Real, active off-campus/rolling hiring with no single fixed event date — do NOT repeat "
        "a date field here, the section heading already makes that clear. Numbered list, each "
        "entry: Company/Organization — Location — brief role/eligibility note.\n"
        "If none were found, write exactly: 'No ongoing applications found for this search.'\n\n"
        "Never move an entry into 'Fixed-Date Drives' unless it has a real, specific, confirmed "
        "date — do not invent one to make an entry fit that section. Do not fabricate company "
        "names, dates, or listings in either section — if you're not confident something is real, "
        "leave it out entirely rather than guess. End with a short reminder that this is "
        "AI-generated from web search and should be independently verified with the "
        "company/college before attending or applying."
    )


async def _resolve_redirect(client: httpx.AsyncClient, redirect_url: str) -> str | None:
    # HEAD, not GET — we only need the final destination URL, not the page
    # body. follow_redirects because Gemini's grounding-api-redirect URLs
    # are themselves a redirect hop to the real source, verified live
    # (curl -IL resolved one to a real careers.cognizant.com job posting).
    # A 403/blocked final page (common — many career sites bot-block
    # non-browser requests) still gives us the correct resolved URL via
    # response.url; we only fail to resolve on a genuine network error.
    try:
        response = await client.head(redirect_url, follow_redirects=True, timeout=10.0)
        return str(response.url)
    except httpx.HTTPError:
        return None


def _line_byte_ranges(text: str) -> list[tuple[int, int, int]]:
    """(line_index, start_byte, end_byte) for every numbered-entry line —
    byte offsets because Citation spans are UTF-8 byte offsets (see
    ai_gateway/service.py's Citation docstring), not Python char offsets."""
    lines = text.split("\n")
    ranges = []
    cursor = 0
    for i, line in enumerate(lines):
        line_bytes = len(line.encode("utf-8"))
        if ENTRY_LINE_RE.match(line):
            ranges.append((i, cursor, cursor + line_bytes))
        cursor += line_bytes + 1  # +1 for the '\n' this line was split on
    return ranges


async def _inject_citation_links(text: str, citations: list[Citation]) -> str:
    """Attaches a real, resolved source link under each numbered entry that
    a citation actually supports — never a generic top-of-response list, so
    each job/drive entry is independently verifiable at a glance."""
    if not citations:
        return text

    line_ranges = _line_byte_ranges(text)
    if not line_ranges:
        return text

    unique_redirect_urls = {url for c in citations for url in c.source_urls}
    async with httpx.AsyncClient() as client:
        resolved = {
            url: await _resolve_redirect(client, url) for url in unique_redirect_urls
        }

    entry_links: dict[int, list[str]] = {idx: [] for idx, _, _ in line_ranges}
    for citation in citations:
        for idx, start, end in line_ranges:
            # Overlap test, not containment — a citation segment is a
            # sub-string WITHIN one entry's line (verified live), so this
            # is really "does this citation belong to this line".
            if citation.start_byte < end and citation.end_byte > start:
                for redirect_url in citation.source_urls:
                    real_url = resolved.get(redirect_url)
                    if real_url and real_url not in entry_links[idx]:
                        entry_links[idx].append(real_url)

    lines = text.split("\n")
    output = []
    for i, line in enumerate(lines):
        output.append(line)
        for url in entry_links.get(i, []):
            output.append(f"   [View / Apply]({url})")
    return "\n".join(output)


async def create_job_drive(
    db: AsyncSession, user_id: uuid.UUID, role: str, city: str, experience_band: str
) -> JobDrive:
    result = await generate_grounded(_build_prompt(role, city, experience_band))
    content = await _inject_citation_links(result.text, result.citations)

    drive = JobDrive(
        user_id=user_id,
        role=role,
        city=city,
        experience_band=experience_band,
        generated_content=content,
        status="draft",
    )
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


async def list_job_drives(db: AsyncSession, user_id: uuid.UUID) -> list[JobDrive]:
    # Every published drive (any user) + the current user's own drafts —
    # nobody else's draft is ever visible, which is what makes "publish"
    # a real, meaningful gate rather than cosmetic.
    result = await db.scalars(
        select(JobDrive)
        .where(or_(JobDrive.status == "published", JobDrive.user_id == user_id))
        .order_by(JobDrive.created_at.desc())
    )
    return list(result)


async def publish_job_drive(db: AsyncSession, user_id: uuid.UUID, drive_id: uuid.UUID) -> JobDrive:
    drive = await db.get(JobDrive, drive_id)
    if drive is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if drive.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the creator can publish this")

    drive.status = "published"
    drive.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(drive)
    return drive
