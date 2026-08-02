import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: uuid.UUID


class ToolDeclaration(BaseModel):
    """Provider-neutral tool schema — the agents module describes tools this
    way; only ai_gateway translates it into Gemini's FunctionDeclaration shape,
    same boundary principle as role translation in service.py."""

    name: str
    description: str
    parameters: dict
