from __future__ import annotations

from typing import Any

from backend.shared.demo_users import DemoUser


def money(currency: str, amount: float | int) -> str:
    return f"{currency} {amount:,.0f}"


def compose_answer(user: DemoUser, intent: str, tool_results: dict[str, Any]) -> str:
    if intent in {"payment_status", "vendor_payment_status"}:
        pa_records = tool_results.get("pa_status", {}).get("records", [])
        po_record = tool_results.get("po_detail", {}).get("record")
        if not pa_records and not po_record:
            return "I couldn't find an authorized PO or payment record matching that request. Source: PMP API."
        if pa_records:
            pa = pa_records[0]
            return (
                f"Hi {user.name}, PO {pa['po_no']} ({pa['description']} - "
                f"{money(pa['currency'], pa['po_amount_original'])}) has PA {pa['pa_no']}. "
                f"The PA status is {pa['pa_status']} and payment status is {pa['payment_status']}. "
                f"Expected payment date: {pa['expected_payment_date']}. Source: PMP API."
            )
        return _po_summary(po_record)

    if intent == "pending_approvals":
        records = tool_results.get("pending_approvals", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, there are no authorized procurement items pending your approval. Source: PMP API."
        rows = [
            f"{r['po_no']} ({r['description']}, {money(r['currency'], r['po_amount_original'])}) - {r['escalation_rule'] or 'no escalation note'}"
            for r in records
        ]
        return f"Hi {user.name}, these items are pending approval: " + "; ".join(rows) + ". Source: PMP API."

    if intent == "pending_pos":
        records = tool_results.get("po_list", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, I couldn't find any authorized pending POs for you. Source: PMP API."
        rows = [f"{r['po_no']} ({r['status']}, {money(r['currency'], r['po_amount_original'])})" for r in records]
        return f"Hi {user.name}, your authorized pending POs are: " + "; ".join(rows) + ". Source: PMP API."

    if intent == "budget_summary":
        records = tool_results.get("budget_summary", {}).get("records", [])
        if not records:
            return "I couldn't find authorized budget information for that request. Source: PMP API."
        rows = [
            f"{r['account_code']}: remaining {money('HKD', r['remaining_budget'])}, status {r['budget_status']}"
            for r in records
        ]
        return f"Budget summary for your authorized scope: " + "; ".join(rows) + ". Source: PMP API."

    if intent in {"po_detail", "general_po_search"}:
        po_record = tool_results.get("po_detail", {}).get("record")
        records = tool_results.get("po_list", {}).get("records", [])
        if po_record:
            return _po_summary(po_record)
        if records:
            rows = [f"{r['po_no']} ({r['status']}, {r['description']})" for r in records]
            return "I found these authorized matching POs: " + "; ".join(rows) + ". Source: PMP API."
        return "I couldn't find an authorized PO matching that request. Source: PMP API."

    return "I can help with PO status, payment status, pending approvals, vendor search, and budget summaries. Source: PMP API."


def _po_summary(po: dict[str, Any]) -> str:
    approvals = po.get("approval_route") or []
    pending = [a for a in approvals if a.get("action_status") == "Pending"]
    pending_text = f" It is pending with {pending[0]['approver_name']}." if pending else ""
    pa_records = po.get("purchase_authorizations") or []
    pa_text = ""
    if pa_records:
        pa = pa_records[0]
        pa_text = f" Linked PA {pa['pa_no']} is {pa['payment_status']}."
    return (
        f"PO {po['po_no']} is {po['status']} for {po['description']} with vendor {po['vendor_name']}, "
        f"amount {money(po['currency'], po['po_amount_original'])}.{pending_text}{pa_text} Source: PMP API."
    )
