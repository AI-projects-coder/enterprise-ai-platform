import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.service import retrieve_relevant_chunks


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Awaitable[dict]]


async def _search_knowledge(db: AsyncSession, user_id: uuid.UUID, query: str) -> dict:
    chunks = await retrieve_relevant_chunks(db, user_id, query)
    if not chunks:
        return {"found": False, "chunks": []}
    return {"found": True, "chunks": chunks}


async def _get_current_datetime() -> dict:
    return {"utc_datetime": datetime.now(timezone.utc).isoformat()}


def build_tools(db: AsyncSession, user_id: uuid.UUID) -> list[AgentTool]:
    """Built fresh per request, not module-level — handlers close over this
    request's db session and user_id, so a module-level registry would leak
    one user's session into another user's concurrent tool call."""
    return [
        AgentTool(
            name="search_knowledge",
            description=(
                "Search the user's uploaded documents for information relevant to a "
                "query. Use this when the question might be answered by something the "
                "user uploaded, not for general knowledge you already have."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=lambda query: _search_knowledge(db, user_id, query),
        ),
        AgentTool(
            name="get_current_datetime",
            description=(
                "Get the current date and time in UTC. Use this for questions about "
                "today's date, the current time, or relative dates — you cannot know "
                "these from training data."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda: _get_current_datetime(),
        ),
    ]
