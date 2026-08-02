import io
import json
import uuid

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.datasets.models import Dataset

# CSV only for v1 — Excel needs an extra parser dependency (openpyxl) and
# has more binary-format edge cases; CSV covers the core "structured
# tabular data" case pandas handles most robustly out of the box.
MAX_DATASET_SIZE = 10 * 1024 * 1024

ALLOWED_AGG_FUNCTIONS = {"sum", "mean", "count", "min", "max", "median"}


def _to_json_safe(obj) -> dict:
    """pandas/numpy results (numpy.float64, numpy.int64, pd.Timestamp, NaN)
    aren't JSON-serializable via the stdlib json module that
    agents/service.py uses to persist tool results — pandas' own .to_json()
    already knows how to convert all of those correctly (NaN -> null), so
    round-tripping through it is simpler than hand-writing a custom encoder."""
    return json.loads(obj.to_json())


def _parse_csv(content: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not parse CSV: {exc}") from exc


async def create_dataset(db: AsyncSession, user_id: uuid.UUID, title: str, content: bytes) -> Dataset:
    # Parsed synchronously, unlike video's analyze step — a CSV read is
    # milliseconds to low seconds even at the size cap, so there's no need
    # for BackgroundTasks/a "processing" status here; a bad file is rejected
    # immediately with a clear error instead of discovered later mid-chat.
    df = _parse_csv(content)
    columns = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]

    dataset = Dataset(
        user_id=user_id, title=title, storage_ref="", row_count=len(df), columns=columns
    )
    db.add(dataset)
    await db.flush()  # assigns dataset.id before it's needed as the storage key

    dataset.storage_ref = await storage.save(dataset.id, content, "text/csv", folder="datasets")
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def list_datasets(db: AsyncSession, user_id: uuid.UUID) -> list[Dataset]:
    result = await db.scalars(
        select(Dataset).where(Dataset.user_id == user_id).order_by(Dataset.created_at.desc())
    )
    return list(result)


async def _get_owned_dataset(db: AsyncSession, user_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset | None:
    result = await db.scalars(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id)
    )
    return result.first()


async def _load_dataframe(db: AsyncSession, user_id: uuid.UUID, dataset_id: uuid.UUID):
    """Re-downloads and re-parses on every call rather than caching a
    DataFrame anywhere — each tool call is a fresh, possibly-different Cloud
    Run instance (same statelessness reasoning as storage.py itself), and at
    the 10MB size cap a re-parse is fast enough that caching would be
    premature complexity, not a fix for a measured problem."""
    dataset = await _get_owned_dataset(db, user_id, dataset_id)
    if dataset is None:
        return None, {"error": "Dataset not found"}
    content = await storage.load(dataset.storage_ref)
    return pd.read_csv(io.BytesIO(content)), None


async def list_datasets_for_agent(db: AsyncSession, user_id: uuid.UUID) -> dict:
    datasets = await list_datasets(db, user_id)
    return {
        "datasets": [
            {
                "id": str(d.id),
                "title": d.title,
                "row_count": d.row_count,
                "columns": d.columns,
            }
            for d in datasets
        ]
    }


async def sample_rows(db: AsyncSession, user_id: uuid.UUID, dataset_id: uuid.UUID, n: int = 5) -> dict:
    df, error = await _load_dataframe(db, user_id, dataset_id)
    if error:
        return error
    return {"rows": json.loads(df.head(n).to_json(orient="records"))}


async def describe_dataset(db: AsyncSession, user_id: uuid.UUID, dataset_id: uuid.UUID) -> dict:
    df, error = await _load_dataframe(db, user_id, dataset_id)
    if error:
        return error
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return {"error": "No numeric columns to describe"}
    return {"stats": _to_json_safe(numeric.describe())}


async def correlation_matrix(db: AsyncSession, user_id: uuid.UUID, dataset_id: uuid.UUID) -> dict:
    df, error = await _load_dataframe(db, user_id, dataset_id)
    if error:
        return error
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return {"error": "Need at least 2 numeric columns to compute correlations"}
    return {"correlations": _to_json_safe(numeric.corr())}


async def group_by_aggregate(
    db: AsyncSession,
    user_id: uuid.UUID,
    dataset_id: uuid.UUID,
    group_by: str,
    agg_column: str,
    agg_function: str,
) -> dict:
    df, error = await _load_dataframe(db, user_id, dataset_id)
    if error:
        return error

    if agg_function not in ALLOWED_AGG_FUNCTIONS:
        return {"error": f"Unsupported aggregation '{agg_function}'. Use one of: {sorted(ALLOWED_AGG_FUNCTIONS)}"}
    missing = [c for c in (group_by, agg_column) if c not in df.columns]
    if missing:
        return {"error": f"Column(s) not found: {missing}. Available columns: {list(df.columns)}"}

    result = df.groupby(group_by)[agg_column].agg(agg_function)
    return {"result": _to_json_safe(result)}
