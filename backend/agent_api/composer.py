from __future__ import annotations

from typing import Any

from backend.shared.demo_users import DemoUser


def money(currency: str, amount: float | int) -> str:
    return f"{currency} {amount:,.0f}"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator, *data_lines])


def compose_answer(user: DemoUser, intent: str, tool_results: dict[str, Any]) -> str:
    if intent in {"payment_status", "vendor_payment_status"}:
        pa_records = tool_results.get("pa_status", {}).get("records", [])
        po_record = tool_results.get("po_detail", {}).get("record")
        if not pa_records and not po_record:
            return "I couldn't find an authorized PO or payment record matching that request.\n\n*Source: PMP API*"
        if pa_records:
            table = _md_table(
                ["PO No", "Description", "PO Amount", "PA No", "PA Status", "Payment Status", "Expected Date"],
                [[pa['po_no'], pa['description'], money(pa['currency'], pa['po_amount_original']),
                  pa['pa_no'], pa['pa_status'], pa['payment_status'], pa['expected_payment_date']]
                 for pa in pa_records],
            )
            return f"Hi {user.name}, here are the payment details:\n\n{table}\n\n*Source: PMP API*"
        return _po_summary(po_record)

    if intent == "pending_approvals":
        records = tool_results.get("pending_approvals", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, there are no authorized procurement items pending your approval.\n\n*Source: PMP API*"
        table = _md_table(
            ["PO No", "Description", "Amount", "Vendor", "Escalation"],
            [[r['po_no'], r['description'], money(r['currency'], r['po_amount_original']),
              r['vendor_name'], r['escalation_rule'] or '—']
             for r in records],
        )
        return f"Hi {user.name}, these items are pending your approval ({len(records)} total):\n\n{table}\n\n*Source: PMP API*"

    if intent == "pending_pos":
        records = tool_results.get("po_list", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, I couldn't find any authorized pending POs for you.\n\n*Source: PMP API*"
        table = _md_table(
            ["PO No", "Status", "Description", "Amount"],
            [[r['po_no'], r['status'], r['description'], money(r['currency'], r['po_amount_original'])]
             for r in records],
        )
        return f"Hi {user.name}, your authorized pending POs:\n\n{table}\n\n*Source: PMP API*"

    if intent == "all_pos":
        records = tool_results.get("po_list", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, I couldn't find any authorized POs for your scope.\n\n*Source: PMP API*"
        table = _md_table(
            ["PO No", "Status", "Description", "Vendor", "Amount"],
            [[r['po_no'], r['status'], r['description'], r['vendor_name'], money(r['currency'], r['po_amount_original'])]
             for r in records],
        )
        return f"Hi {user.name}, here are all POs authorized for your scope ({len(records)} total):\n\n{table}\n\n*Source: PMP API*"

    if intent == "budget_summary":
        records = tool_results.get("budget_summary", {}).get("records", [])
        if not records:
            return "I couldn't find authorized budget information for that request.\n\n*Source: PMP API*"
        table = _md_table(
            ["Account Code", "Yearly Budget", "Used (YTM)", "Remaining", "Status"],
            [[r['account_code'], money('HKD', r['yearly_budget']), money('HKD', r['ytm_used']),
              money('HKD', r['remaining_budget']), r['budget_status']]
             for r in records],
        )
        return f"Hi {user.name}, budget summary for your authorized scope:\n\n{table}\n\n*Source: PMP API*"

    if intent in {"po_detail", "general_po_search"}:
        po_record = tool_results.get("po_detail", {}).get("record")
        records = tool_results.get("po_list", {}).get("records", [])
        if po_record:
            return _po_summary(po_record)
        if records:
            table = _md_table(
                ["PO No", "Status", "Description", "Amount"],
                [[r['po_no'], r['status'], r['description'], money(r['currency'], r['po_amount_original'])]
                 for r in records],
            )
            return f"I found these authorized matching POs:\n\n{table}\n\n*Source: PMP API*"
        return "I couldn't find an authorized PO matching that request.\n\n*Source: PMP API*"

    return "I can help with PO status, payment status, pending approvals, vendor search, and budget summaries.\n\n*Source: PMP API*"


def _po_summary(po: dict[str, Any]) -> str:
    approvals = po.get("approval_route") or []
    pending = [a for a in approvals if a.get("action_status") == "Pending"]
    pa_records = po.get("purchase_authorizations") or []

    details = _md_table(
        ["Field", "Value"],
        [
            ["PO No", po['po_no']],
            ["Status", po['status']],
            ["Description", po['description']],
            ["Vendor", po['vendor_name']],
            ["Amount", money(po['currency'], po['po_amount_original'])],
            ["Pending With", pending[0]['approver_name'] if pending else "—"],
            ["Linked PA", f"{pa_records[0]['pa_no']} ({pa_records[0]['payment_status']})" if pa_records else "—"],
        ],
    )
    return f"**PO {po['po_no']}** details:\n\n{details}\n\n*Source: PMP API*"
