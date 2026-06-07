from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Any

import backend.shared.config as _config
from backend.shared.demo_users import DemoUser

logger = logging.getLogger(__name__)

DETERMINISTIC_INTENTS = {
    "longest_waiting_po",
    "po_pending_party_analysis",
    "po_approval_progress",
    "po_volume_summary",
    "delayed_approval_summary",
    "pending_approvals",
    "pending_pos",
    "all_pos",
    "budget_summary",
    "po_detail",
    "general_po_search",
    "payment_status",
    "vendor_payment_status",
}


def money(currency: str, amount: float | int) -> str:
    return f"{currency} {amount:,.0f}"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator, *data_lines])


def compose_answer(user: DemoUser, intent: str, tool_results: dict[str, Any], message: str = "") -> str:
    if intent in DETERMINISTIC_INTENTS:
        return _template_answer(user, intent, tool_results)
    if _config.USE_REAL_LLM:
        try:
            from backend.agent_api.llm import llm_compose_answer
            answer = llm_compose_answer(user.name, user.role, message, intent, tool_results)
            logger.info("LLM composed answer (%d chars)", len(answer))
            return answer
        except Exception:
            logger.exception("LLM answer composition failed, falling back to template")
    return _template_answer(user, intent, tool_results)


def _template_answer(user: DemoUser, intent: str, tool_results: dict[str, Any]) -> str:
    if intent == "longest_waiting_po":
        pending = _pending_po_analysis_records(tool_results)
        if not pending:
            return f"Hi {user.name}, I couldn't find any authorized pending POs to analyze.\n\n*Source: PMP API*"
        top = pending[0]
        table = _md_table(
            ["Rank", "PO No", "Pending Party", "Role", "Waiting", "Description", "Amount"],
            [
                [
                    str(idx + 1),
                    item["po_no"],
                    item["pending_party"],
                    item["pending_role"],
                    f"{item['ageing_days']} days",
                    item["description"],
                    money(item["currency"], item["po_amount_original"]),
                ]
                for idx, item in enumerate(pending[:5])
            ],
        )
        return (
            f"Hi {user.name}, the longest-waiting authorized PO is **{top['po_no']}**, "
            f"pending with **{top['pending_party']} ({top['pending_role']})** for "
            f"**{top['ageing_days']} days**.\n\n{table}\n\n*Source: PMP API*"
        )

    if intent == "po_pending_party_analysis":
        pending = _pending_po_analysis_records(tool_results)
        if not pending:
            return f"Hi {user.name}, I couldn't find any authorized pending POs to analyze.\n\n*Source: PMP API*"
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in pending:
            groups[(item["pending_party"], item["pending_role"])].append(item)
        rows = []
        for (party, role), items in sorted(groups.items(), key=lambda pair: max(i["ageing_days"] for i in pair[1]), reverse=True):
            oldest = max(items, key=lambda i: i["ageing_days"])
            rows.append([party, role, str(len(items)), f"{oldest['ageing_days']} days", oldest["po_no"]])
        table = _md_table(["Pending Party", "Role", "PO Count", "Oldest Wait", "Oldest PO"], rows)
        return (
            f"Hi {user.name}, in your authorized scope, **{len(pending)} pending POs** are waiting for approval. "
            f"Here is the breakdown by pending party:\n\n{table}\n\n*Source: PMP API*"
        )

    if intent == "po_volume_summary":
        records = tool_results.get("po_list", {}).get("records", [])
        if not records:
            return f"Hi {user.name}, I couldn't find authorized POs to summarize.\n\n{_analytics_examples()}\n\n*Source: PMP API*"
        rows = _monthly_po_volume_rows(records)
        table = _md_table(["Month", "Status", "PO Count", "Total Amount"], rows)
        return (
            f"Hi {user.name}, here is the monthly PO volume for your authorized scope "
            f"({len(records)} POs total):\n\n{table}\n\n*Source: PMP API*"
        )

    if intent == "delayed_approval_summary":
        pending = _pending_po_analysis_records(tool_results)
        if not pending:
            return f"Hi {user.name}, I couldn't find any authorized pending approvals to analyze.\n\n*Source: PMP API*"
        delayed = [item for item in pending if item["is_overdue"] or item["ageing_days"] >= 3]
        source = delayed or pending
        rows = [
            [
                item["po_no"],
                item["pending_party"],
                item["pending_role"],
                f"{item['ageing_days']} days",
                "Overdue" if item["is_overdue"] else "Within SLA",
                item["due_at"] or "-",
                money(item["currency"], item["po_amount_original"]),
            ]
            for item in source[:8]
        ]
        table = _md_table(["PO No", "Pending Party", "Role", "Waiting", "Delay Status", "Due", "Amount"], rows)
        oldest = source[0]
        return (
            f"Hi {user.name}, I found **{len(delayed)} delayed / ageing approvals** in your authorized scope. "
            f"The oldest is **{oldest['po_no']}**, waiting with **{oldest['pending_party']}** for "
            f"**{oldest['ageing_days']} days**.\n\n{table}\n\n*Source: PMP API*"
        )

    if intent == "po_approval_progress":
        po_record = tool_results.get("po_detail", {}).get("record")
        if not po_record:
            return "I couldn't find an authorized PO matching that request.\n\n*Source: PMP API*"
        return _approval_progress_summary(po_record)

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
        return f"I couldn't find an authorized PO matching that request.\n\n{_analytics_examples()}\n\n*Source: PMP API*"

    return f"I can help with PO status, payment status, pending approvals, vendor search, budget summaries, and PO analytics.\n\n{_analytics_examples()}\n\n*Source: PMP API*"


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


def _pending_po_analysis_records(tool_results: dict[str, Any]) -> list[dict[str, Any]]:
    records = tool_results.get("pending_po_details", {}).get("records", [])
    analyzed = [_analyze_pending_po(record) for record in records]
    return sorted([item for item in analyzed if item], key=lambda item: item["ageing_days"], reverse=True)


def _monthly_po_volume_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        month = _month_label(record.get("po_date"))
        status = record.get("status") or "Unknown"
        currency = record.get("currency") or "HKD"
        key = (month, status, currency)
        bucket = groups.setdefault(key, {"count": 0, "amount": 0})
        bucket["count"] += 1
        bucket["amount"] += record.get("po_amount_original") or 0
    rows = []
    for (month, status, currency), bucket in sorted(groups.items()):
        rows.append([month, status, str(bucket["count"]), money(currency, bucket["amount"])])
    return rows


def _analyze_pending_po(po: dict[str, Any]) -> dict[str, Any] | None:
    approvals = po.get("approval_route") or []
    pending_steps = [step for step in approvals if step.get("action_status") == "Pending"]
    if not pending_steps:
        return None
    current = sorted(pending_steps, key=lambda step: step.get("step_order") or 999)[0]
    entered_at = current.get("entered_at") or po.get("po_date")
    return {
        "po_no": po["po_no"],
        "description": po["description"],
        "currency": po["currency"],
        "po_amount_original": po["po_amount_original"],
        "pending_party": current.get("approver_name") or "Unknown",
        "pending_role": current.get("approver_role") or "Unknown",
        "pending_since": entered_at,
        "due_at": current.get("due_at") or "",
        "ageing_days": _ageing_days(entered_at),
        "is_overdue": _is_overdue(current.get("due_at")),
        "vendor_name": po.get("vendor_name") or "",
    }


def _approval_progress_summary(po: dict[str, Any]) -> str:
    approvals = po.get("approval_route") or []
    rows = []
    current_pending = None
    for step in sorted(approvals, key=lambda item: item.get("step_order") or 999):
        waiting = ""
        if step.get("action_status") == "Pending":
            current_pending = step
            waiting = f"{_ageing_days(step.get('entered_at') or po.get('po_date'))} days"
        rows.append(
            [
                str(step.get("step_order") or ""),
                step.get("approver_role") or "",
                step.get("approver_name") or "",
                step.get("action_status") or "",
                step.get("entered_at") or "",
                step.get("action_at") or "-",
                waiting or "-",
            ]
        )
    table = _md_table(["Step", "Role", "Party", "Status", "Entered", "Actioned", "Waiting"], rows)
    if current_pending:
        headline = (
            f"PO **{po['po_no']}** is currently pending with **{current_pending.get('approver_name')} "
            f"({current_pending.get('approver_role')})** for "
            f"**{_ageing_days(current_pending.get('entered_at') or po.get('po_date'))} days**."
        )
    else:
        headline = f"PO **{po['po_no']}** is not currently waiting for approval. Current status: **{po['status']}**."
    return f"{headline}\n\n{table}\n\n*Source: PMP API*"


def _ageing_days(entered_at: str | None) -> int:
    if not entered_at:
        return 0
    try:
        start = datetime.fromisoformat(entered_at).date()
    except ValueError:
        start = date.fromisoformat(entered_at[:10])
    today = date.fromisoformat(_config.DEMO_TODAY)
    return max((today - start).days, 0)


def _is_overdue(due_at: str | None) -> bool:
    if not due_at:
        return False
    try:
        due = datetime.fromisoformat(due_at).date()
    except ValueError:
        due = date.fromisoformat(due_at[:10])
    return date.fromisoformat(_config.DEMO_TODAY) > due


def _month_label(value: str | None) -> str:
    if not value:
        return "Unknown"
    try:
        parsed = datetime.fromisoformat(value).date()
    except ValueError:
        parsed = date.fromisoformat(value[:10])
    return parsed.strftime("%Y-%m")


def _analytics_examples() -> str:
    return (
        "Supported analytics examples: monthly PO volume, delayed approval summary, "
        "longest wait time PO, and PO approval pending by party."
    )
