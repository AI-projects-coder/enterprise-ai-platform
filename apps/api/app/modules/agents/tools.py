import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.datasets import service as datasets_service
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


def _dataset_id_or_error(dataset_id: str) -> uuid.UUID | dict:
    try:
        return uuid.UUID(dataset_id)
    except ValueError:
        return {"error": f"'{dataset_id}' is not a valid dataset id"}


# Each wrapper resolves dataset_id -> UUID itself and returns a clean error
# dict on failure rather than letting ValueError propagate — run_chat's tool
# loop doesn't wrap tool.handler() calls in try/except, so an uncaught
# exception here would crash the whole /chat request instead of just
# telling the model "that wasn't a valid id, try again".
async def _list_datasets(db: AsyncSession, user_id: uuid.UUID) -> dict:
    return await datasets_service.list_datasets_for_agent(db, user_id)


async def _sample_rows(db: AsyncSession, user_id: uuid.UUID, dataset_id: str, n: int = 5) -> dict:
    parsed = _dataset_id_or_error(dataset_id)
    if isinstance(parsed, dict):
        return parsed
    return await datasets_service.sample_rows(db, user_id, parsed, n)


async def _describe_dataset(db: AsyncSession, user_id: uuid.UUID, dataset_id: str) -> dict:
    parsed = _dataset_id_or_error(dataset_id)
    if isinstance(parsed, dict):
        return parsed
    return await datasets_service.describe_dataset(db, user_id, parsed)


async def _correlation_matrix(db: AsyncSession, user_id: uuid.UUID, dataset_id: str) -> dict:
    parsed = _dataset_id_or_error(dataset_id)
    if isinstance(parsed, dict):
        return parsed
    return await datasets_service.correlation_matrix(db, user_id, parsed)


async def _group_by_aggregate(
    db: AsyncSession,
    user_id: uuid.UUID,
    dataset_id: str,
    group_by: str,
    agg_column: str,
    agg_function: str,
) -> dict:
    parsed = _dataset_id_or_error(dataset_id)
    if isinstance(parsed, dict):
        return parsed
    return await datasets_service.group_by_aggregate(
        db, user_id, parsed, group_by, agg_column, agg_function
    )


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
        AgentTool(
            name="list_datasets",
            description=(
                "List the user's uploaded tabular datasets (CSVs), including each "
                "dataset's id, row count, and column names/types. Call this first "
                "whenever a question might be about uploaded data, so you know which "
                "dataset id to pass to the other dataset tools and what columns exist."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda: _list_datasets(db, user_id),
        ),
        AgentTool(
            name="sample_dataset_rows",
            description=(
                "Get the first few rows of a dataset as-is, to see real example values "
                "before computing statistics on it. Use the dataset id from list_datasets."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "The dataset's id"},
                    "n": {"type": "integer", "description": "How many rows to return (default 5)"},
                },
                "required": ["dataset_id"],
                "additionalProperties": False,
            },
            handler=lambda dataset_id, n=5: _sample_rows(db, user_id, dataset_id, n),
        ),
        AgentTool(
            name="describe_dataset",
            description=(
                "Get summary statistics (count, mean, std, min, quartiles, max) for "
                "every numeric column in a dataset. Use the dataset id from list_datasets."
            ),
            parameters={
                "type": "object",
                "properties": {"dataset_id": {"type": "string", "description": "The dataset's id"}},
                "required": ["dataset_id"],
                "additionalProperties": False,
            },
            handler=lambda dataset_id: _describe_dataset(db, user_id, dataset_id),
        ),
        AgentTool(
            name="dataset_correlation",
            description=(
                "Get the pairwise correlation matrix between all numeric columns in a "
                "dataset. Use this for questions about which variables move together."
            ),
            parameters={
                "type": "object",
                "properties": {"dataset_id": {"type": "string", "description": "The dataset's id"}},
                "required": ["dataset_id"],
                "additionalProperties": False,
            },
            handler=lambda dataset_id: _correlation_matrix(db, user_id, dataset_id),
        ),
        AgentTool(
            name="dataset_group_by_aggregate",
            description=(
                "Group a dataset by one column and aggregate another column within each "
                "group — e.g. total revenue per region, or average score per category. "
                "agg_function must be one of: sum, mean, count, min, max, median."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "The dataset's id"},
                    "group_by": {"type": "string", "description": "Column to group rows by"},
                    "agg_column": {"type": "string", "description": "Column to aggregate within each group"},
                    "agg_function": {
                        "type": "string",
                        "description": "One of: sum, mean, count, min, max, median",
                    },
                },
                "required": ["dataset_id", "group_by", "agg_column", "agg_function"],
                "additionalProperties": False,
            },
            handler=lambda dataset_id, group_by, agg_column, agg_function: _group_by_aggregate(
                db, user_id, dataset_id, group_by, agg_column, agg_function
            ),
        ),
    ]
