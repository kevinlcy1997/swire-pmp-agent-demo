from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.agent_api.graph import run_agent_graph
from backend.agent_api.intent import classify_intent
from backend.shared.demo_users import DEMO_USERS, DemoUser, get_demo_user
from backend.shared.models import ChatRequest, ChatResponse, DemoUserResponse, StreamEvent

app = FastAPI(title="Swire Demo LangGraph Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(x_demo_user: str | None) -> DemoUser:
    try:
        return get_demo_user(x_demo_user)
    except KeyError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agent-api"}


@app.get("/api/demo/users", response_model=list[DemoUserResponse])
def demo_users() -> list[DemoUserResponse]:
    return [DemoUserResponse(**user.__dict__) for user in DEMO_USERS.values()]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_demo_user: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    user = current_user(x_demo_user)
    conversation_id = request.conversation_id or str(uuid.uuid4())
    state = await run_agent_graph(user, request.message, conversation_id)
    return ChatResponse(
        conversation_id=conversation_id,
        user_key=user.user_key,
        intent=state["intent"],
        answer=state["answer"],
        tool_calls=state.get("tool_calls", []),
    )


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_demo_user: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    user = current_user(x_demo_user)
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def events():
        yield _sse("thinking", {"message": "Reading your user context and checking PMP permissions.", "user": user.user_key})
        intent = classify_intent(request.message)
        yield _sse("thinking", {"message": f"Detected intent: {intent}."})
        state = await run_agent_graph(user, request.message, conversation_id)
        for call in state.get("tool_calls", []):
            yield _sse("tool_call", call)
            yield _sse("tool_result", {"tool": call["tool"], "result_count": call["result_count"], "source": "PMP API"})
        yield _sse("answer", {"content": state["answer"], "conversation_id": conversation_id})
        yield _sse("done", {"conversation_id": conversation_id})

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(event_type: str, data: dict[str, Any]) -> str:
    event = StreamEvent(type=event_type, data=data)
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
