"""Azure OpenAI integration for intent classification and answer composition."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import AzureOpenAI, AsyncAzureOpenAI

from backend.shared.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
)

logger = logging.getLogger(__name__)

VALID_INTENTS = [
    "payment_status",
    "vendor_payment_status",
    "pending_approvals",
    "pending_pos",
    "all_pos",
    "budget_summary",
    "po_detail",
    "general_po_search",
]

INTENT_SYSTEM_PROMPT = f"""You are an intent classifier for a Procurement Management Platform (PMP) chatbot at Swire Properties.

Given a user message, classify it into exactly ONE of these intents:
{json.dumps(VALID_INTENTS)}

Rules:
- "payment_status": user asks about payment status, PA status, whether something is paid
- "vendor_payment_status": user asks about a specific vendor's payment or mentions a vendor name
- "pending_approvals": user asks what is pending their approval
- "pending_pos": user asks about their pending POs or POs awaiting action
- "all_pos": user wants to see all POs, list all purchase orders
- "budget_summary": user asks about budget, remaining budget, spending
- "po_detail": user mentions a specific PO number (e.g. FAIT2015600)
- "general_po_search": anything else about POs or procurement

Respond with ONLY the intent string, nothing else."""

COMPOSE_SYSTEM_PROMPT = """You are a helpful Swire Properties procurement assistant. You answer questions about purchase orders, payments, approvals, budgets, and vendors.

You will be given:
1. The user's name and role
2. The user's original question
3. Data retrieved from the PMP API (as JSON)

Rules:
- Present data in well-formatted markdown tables when showing lists
- Use bold for key values
- Be concise and professional
- Always end with "*Source: PMP API*" on a new line
- If the data is empty, politely say you couldn't find matching records
- For currency amounts, format with commas (e.g. HKD 1,234,567)
- Address the user by their first name
- Do NOT invent data — only use what is provided"""


def _get_sync_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def _get_async_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def llm_classify_intent(message: str) -> str:
    """Use Azure OpenAI to classify the user's intent."""
    client = _get_sync_client()
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0,
        max_tokens=30,
    )
    intent = response.choices[0].message.content.strip().lower()
    if intent in VALID_INTENTS:
        return intent
    logger.warning("LLM returned unknown intent %r, falling back to general_po_search", intent)
    return "general_po_search"


def _build_compose_messages(
    user_name: str,
    user_role: str,
    message: str,
    intent: str,
    tool_results: dict[str, Any],
) -> list[dict[str, str]]:
    data_summary = json.dumps(tool_results, ensure_ascii=False, default=str)
    user_prompt = (
        f"User: {user_name} (Role: {user_role})\n"
        f"Question: {message}\n"
        f"Detected intent: {intent}\n\n"
        f"PMP API data:\n```json\n{data_summary}\n```\n\n"
        "Please compose a clear, helpful answer."
    )
    return [
        {"role": "system", "content": COMPOSE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def llm_compose_answer(
    user_name: str,
    user_role: str,
    message: str,
    intent: str,
    tool_results: dict[str, Any],
) -> str:
    """Use Azure OpenAI to compose a natural-language answer (non-streaming)."""
    client = _get_sync_client()
    messages = _build_compose_messages(user_name, user_role, message, intent, tool_results)
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


async def llm_compose_answer_stream(
    user_name: str,
    user_role: str,
    message: str,
    intent: str,
    tool_results: dict[str, Any],
) -> AsyncIterator[str]:
    """Use Azure OpenAI to compose a natural-language answer, yielding token chunks."""
    client = _get_async_client()
    messages = _build_compose_messages(user_name, user_role, message, intent, tool_results)
    response = await client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
        stream=True,
    )
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
