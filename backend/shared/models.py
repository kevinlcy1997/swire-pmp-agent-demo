from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    user_key: str
    intent: str
    answer: str
    tool_calls: list[dict[str, Any]]


class DemoUserResponse(BaseModel):
    user_key: str
    user_id: str
    name: str
    role: str
    department: str
    cost_centre_code: str
    description: str


StreamEventType = Literal["thinking", "tool_call", "tool_result", "answer", "error", "done"]


class StreamEvent(BaseModel):
    type: StreamEventType
    data: dict[str, Any]
