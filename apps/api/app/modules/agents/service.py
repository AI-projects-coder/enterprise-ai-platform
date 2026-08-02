import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.tools import build_tools
from app.modules.ai_gateway.schemas import ChatRequest, ChatResponse, ToolDeclaration
from app.modules.ai_gateway.service import generate
from app.modules.memory import service as memory_service

MAX_TOOL_ITERATIONS = 5


async def run_chat(db: AsyncSession, user_id: uuid.UUID, data: ChatRequest) -> ChatResponse:
    if data.conversation_id is None:
        conversation = await memory_service.create_conversation(db, user_id, title=data.message[:50])
    else:
        conversation = await memory_service.get_conversation(db, data.conversation_id, user_id)
        if conversation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    await memory_service.add_message(db, conversation.id, "user", data.message)

    tools = build_tools(db, user_id)
    tools_by_name = {t.name: t for t in tools}
    declarations = [
        ToolDeclaration(name=t.name, description=t.description, parameters=t.parameters) for t in tools
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        history = await memory_service.list_messages(db, conversation.id)
        result = await generate(history, tools=declarations)

        if result.kind == "text":
            await memory_service.add_message(db, conversation.id, "assistant", result.text)
            return ChatResponse(reply=result.text, conversation_id=conversation.id)

        # kind == "tool_calls" — persist the call and its result as their own
        # provider-neutral turns so the next generate() call (which always
        # rebuilds full history from memory, same as plain chat since phase 3)
        # reconstructs the exchange correctly.
        await memory_service.add_message(db, conversation.id, "tool_call", json.dumps(result.calls))

        outputs = []
        for call in result.calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                outputs.append({"name": call["name"], "response": {"error": "unknown tool"}})
                continue
            output = await tool.handler(**call["args"])
            outputs.append({"name": call["name"], "response": output})

        await memory_service.add_message(db, conversation.id, "tool_result", json.dumps(outputs))

    # Safety cap: the model kept calling tools instead of answering. Force one
    # final call with tools disabled so it must produce a text reply instead
    # of looping forever (and burning API cost) — a bug here would otherwise
    # be a runaway-cost incident, not just a wrong answer.
    history = await memory_service.list_messages(db, conversation.id)
    result = await generate(history, tools=None)
    text = result.text if result.kind == "text" else "I wasn't able to complete that request."
    await memory_service.add_message(db, conversation.id, "assistant", text)
    return ChatResponse(reply=text, conversation_id=conversation.id)
