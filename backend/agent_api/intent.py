from __future__ import annotations

import logging
import re

import backend.shared.config as _config

logger = logging.getLogger(__name__)


def extract_po_no(message: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,}[A-Z0-9]*\d{3,}|RESTRICTED\d+)\b", message.upper())
    return match.group(1) if match else None


def _rule_based_intent(message: str) -> str:
    text = message.lower()
    if (
        ("po" in text or "purchase order" in text)
        and (
            "monthly" in text
            or "month" in text
            or "volume" in text
            or "count" in text
            or "trend" in text
            or "how many" in text
        )
    ):
        return "po_volume_summary"
    if (
        ("approval" in text or "approve" in text or "endorser" in text)
        and (
            "delayed" in text
            or "delay" in text
            or "overdue" in text
            or "late" in text
            or "ageing" in text
            or "aging" in text
            or "sla" in text
        )
    ):
        return "delayed_approval_summary"
    if (
        "longest wait" in text
        or "longest waiting" in text
        or "wait time" in text
        or "waiting longest" in text
        or "oldest pending" in text
        or "oldest po" in text
    ):
        return "longest_waiting_po"
    if (
        "pending which party" in text
        or "pending by party" in text
        or "which party" in text
        or "who is holding" in text
        or "who is holding up" in text
        or "approval bottleneck" in text
        or "approval pending party" in text
    ):
        return "po_pending_party_analysis"
    if extract_po_no(message) and ("stuck" in text or "progress" in text or "approval route" in text):
        return "po_approval_progress"
    if "pending my approval" in text or "pending approval" in text or "approve" in text:
        return "pending_approvals"
    if "budget" in text:
        return "budget_summary"
    if "brightsign" in text or "vendor" in text:
        return "vendor_payment_status"
    if "paid" in text or "payment" in text or "pa " in text or "payment status" in text:
        return "payment_status"
    if extract_po_no(message):
        return "po_detail"
    if "pending po" in text or "my pending" in text or "show my pending" in text:
        return "pending_pos"
    if (
        "all po" in text
        or "all of my po" in text
        or "all my po" in text
        or "list po" in text
        or "show po" in text
        or "my po" in text
        or "my purchase order" in text
        or "all purchase" in text
        or "all of my purchase" in text
        or "all my purchase" in text
        or "every po" in text
        or "every purchase" in text
    ):
        return "all_pos"
    return "general_po_search"


def classify_intent(message: str) -> str:
    if _config.USE_REAL_LLM:
        try:
            from backend.agent_api.llm import llm_classify_intent
            intent = llm_classify_intent(message)
            logger.info("LLM classified intent: %s", intent)
            return intent
        except Exception:
            logger.exception("LLM intent classification failed, falling back to rule-based")
    return _rule_based_intent(message)
