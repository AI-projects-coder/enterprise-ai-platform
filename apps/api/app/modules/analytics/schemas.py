import uuid
from datetime import date as date_type

from pydantic import BaseModel


class DailyUsage(BaseModel):
    day: date_type
    llm_calls: int
    total_tokens: int


class UsageSummary(BaseModel):
    since_days: int
    conversation_count: int
    message_count: int
    document_count: int
    llm_call_count: int
    total_tokens: int
    daily: list[DailyUsage]


class MemberUsage(BaseModel):
    user_id: uuid.UUID
    email: str
    message_count: int
    llm_call_count: int
    total_tokens: int


class OrgUsageSummary(BaseModel):
    since_days: int
    member_count: int
    total_message_count: int
    total_tokens: int
    members: list[MemberUsage]
