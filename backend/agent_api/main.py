from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.agent_api.graph import run_agent_graph, load_user_context, classify_intent_node, select_tools, call_pmp_tools, write_audit_log, AgentState
from backend.agent_api.intent import classify_intent
import backend.shared.config as _config
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

        # Run pipeline up to tool calls
        initial: AgentState = {"user": user, "message": request.message, "conversation_id": conversation_id}
        state = await load_user_context(initial)
        state = await classify_intent_node(state)
        yield _sse("thinking", {"message": f"Detected intent: {state['intent']}."})
        state = await select_tools(state)
        state = await call_pmp_tools(state)

        for call in state.get("tool_calls", []):
            yield _sse("tool_call", call)
            yield _sse("tool_result", {"tool": call["tool"], "result_count": call["result_count"], "source": "PMP API"})

        # Compose answer — stream if LLM is enabled
        if _config.USE_REAL_LLM:
            try:
                from backend.agent_api.llm import llm_compose_answer_stream
                full_answer = ""
                async for chunk in llm_compose_answer_stream(
                    user.name, user.role, request.message,
                    state["intent"], state["tool_results"],
                ):
                    full_answer += chunk
                    yield _sse("delta", {"content": chunk})
                state["answer"] = full_answer
                yield _sse("answer", {"content": full_answer, "conversation_id": conversation_id})
            except Exception as exc:
                import logging
                logging.getLogger(__name__).exception("LLM streaming failed: %s", exc)
                from backend.agent_api.composer import compose_answer
                state["answer"] = compose_answer(user, state["intent"], state["tool_results"], request.message)
                yield _sse("answer", {"content": state["answer"], "conversation_id": conversation_id})
        else:
            from backend.agent_api.composer import compose_answer
            state["answer"] = compose_answer(user, state["intent"], state["tool_results"], request.message)
            yield _sse("answer", {"content": state["answer"], "conversation_id": conversation_id})

        # Audit log
        state = await write_audit_log(state)
        yield _sse("done", {"conversation_id": conversation_id})

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(event_type: str, data: dict[str, Any]) -> str:
    event = StreamEvent(type=event_type, data=data)
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
