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
    if "all po" in text or "list po" in text or "show po" in text or "all purchase" in text or "every po" in text:
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
