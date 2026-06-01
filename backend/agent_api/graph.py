from __future__ import annotations

from typing import Any, TypedDict

from backend.agent_api.composer import compose_answer
from backend.agent_api.intent import classify_intent, extract_po_no
from backend.agent_api.pmp_client import PmpClient
from backend.shared.demo_users import DemoUser


class AgentState(TypedDict, total=False):
    user: DemoUser
    message: str
    conversation_id: str | None
    intent: str
    tool_plan: list[dict[str, Any]]
    tool_results: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    answer: str


async def load_user_context(state: AgentState) -> AgentState:
    return state


async def classify_intent_node(state: AgentState) -> AgentState:
    state["intent"] = classify_intent(state["message"])
    return state


async def select_tools(state: AgentState) -> AgentState:
    message = state["message"]
    intent = state["intent"]
    po_no = extract_po_no(message)
    plan: list[dict[str, Any]] = []
    if intent == "payment_status":
        if po_no:
            plan.append({"name": "po_detail", "args": {"po_no": po_no}})
            plan.append({"name": "pa_status", "args": {"po_no": po_no}})
        else:
            plan.append({"name": "po_list", "args": {"q": "lobby signage"}})
            plan.append({"name": "pa_status", "args": {"po_no": "FAIT2015600"}})
    elif intent == "vendor_payment_status":
        plan.append({"name": "vendor_search", "args": {"q": "BrightSign"}})
        plan.append({"name": "pa_status", "args": {"vendor_code": "BRI001"}})
    elif intent == "pending_approvals":
        plan.append({"name": "pending_approvals", "args": {}})
    elif intent == "pending_pos":
        plan.append({"name": "po_list", "args": {"status": "Pending Endorser"}})
    elif intent == "budget_summary":
        plan.append({"name": "budget_summary", "args": {}})
    elif intent == "po_detail" and po_no:
        plan.append({"name": "po_detail", "args": {"po_no": po_no}})
    else:
        plan.append({"name": "po_list", "args": {"q": message}})
    state["tool_plan"] = plan
    return state


async def call_pmp_tools(state: AgentState) -> AgentState:
    client = PmpClient(state["user"])
    results: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []
    for item in state["tool_plan"]:
        name = item["name"]
        args = item["args"]
        if name == "po_detail":
            result = await client.po_detail(**args)
        elif name == "po_list":
            result = await client.list_pos(**args)
        elif name == "vendor_search":
            result = await client.vendor_search(**args)
        elif name == "pa_status":
            result = await client.pa_status(**args)
        elif name == "pending_approvals":
            result = await client.pending_approvals()
        elif name == "budget_summary":
            result = await client.budget_summary(**args)
        else:
            result = {"records": [], "count": 0, "error": f"Unknown tool: {name}"}
        results[name] = result
        calls.append({"tool": name, "args": args, "result_count": result.get("count", 1 if result.get("record") else 0)})
    state["tool_results"] = results
    state["tool_calls"] = calls
    return state


async def compose_answer_node(state: AgentState) -> AgentState:
    state["answer"] = compose_answer(state["user"], state["intent"], state["tool_results"])
    return state


async def write_audit_log(state: AgentState) -> AgentState:
    client = PmpClient(state["user"])
    await client.audit(
        {
            "conversation_id": state.get("conversation_id"),
            "question": state["message"],
            "intent": state["intent"],
            "tool_calls": state.get("tool_calls", []),
            "final_answer": state["answer"],
        }
    )
    return state


async def run_agent_graph(user: DemoUser, message: str, conversation_id: str | None) -> AgentState:
    initial: AgentState = {"user": user, "message": message, "conversation_id": conversation_id}
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("load_user_context", load_user_context)
        graph.add_node("classify_intent", classify_intent_node)
        graph.add_node("select_tools", select_tools)
        graph.add_node("call_pmp_tools", call_pmp_tools)
        graph.add_node("compose_answer", compose_answer_node)
        graph.add_node("write_audit_log", write_audit_log)
        graph.set_entry_point("load_user_context")
        graph.add_edge("load_user_context", "classify_intent")
        graph.add_edge("classify_intent", "select_tools")
        graph.add_edge("select_tools", "call_pmp_tools")
        graph.add_edge("call_pmp_tools", "compose_answer")
        graph.add_edge("compose_answer", "write_audit_log")
        graph.add_edge("write_audit_log", END)
        app = graph.compile()
        return await app.ainvoke(initial)
    except ImportError:
        state = await load_user_context(initial)
        state = await classify_intent_node(state)
        state = await select_tools(state)
        state = await call_pmp_tools(state)
        state = await compose_answer_node(state)
        return await write_audit_log(state)
