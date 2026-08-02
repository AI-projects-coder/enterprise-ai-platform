import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_gateway.service import embed
from app.modules.knowledge.models import Chunk, Document

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


async def ingest_document(
    db: AsyncSession, user_id: uuid.UUID, title: str, content: str
) -> Document:
    document = Document(user_id=user_id, title=title)
    db.add(document)
    await db.flush()  # assigns document.id without committing, so chunks can reference it

    for index, text in enumerate(_chunk_text(content)):
        vector = await embed(text)
        db.add(Chunk(document_id=document.id, chunk_index=index, content=text, embedding=vector))

    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    result = await db.scalars(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result)


async def delete_document(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user_id:
        return False
    await db.delete(document)
    await db.commit()
    return True


async def retrieve_relevant_chunks(
    db: AsyncSession, user_id: uuid.UUID, query_text: str, top_k: int = TOP_K
) -> list[str]:
    query_vector = await embed(query_text)

    result = await db.scalars(
        select(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    return [chunk.content for chunk in result]
