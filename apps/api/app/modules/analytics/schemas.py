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
