from __future__ import annotations

from typing import Any

from backend.mock_pmp_api.rbac import po_visibility_where
from backend.shared.demo_users import DemoUser
from backend.shared.sqlite import get_connection


PO_SELECT = """
SELECT
  po.po_id,
  po.po_no,
  po.po_date,
  po.po_type,
  po.status,
  po.currency,
  po.po_amount_original,
  po.po_amount_base,
  po.finance_team,
  po.project_code,
  po.description,
  po.vendor_id,
  po.submitter_user_id,
  po.cost_centre_code,
  po.percent_left,
  po.outstand_amount_original,
  v.vendor_code,
  v.vendor_name
FROM purchase_orders po
JOIN vendors v ON v.vendor_id = po.vendor_id
"""


def list_pos(
    user: DemoUser,
    status: str | None = None,
    vendor_code: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    where, params = po_visibility_where(user)
    clauses = [where]
    if status and status.lower() != "all":
        clauses.append("LOWER(po.status) = LOWER(?)")
        params.append(status)
    if vendor_code:
        clauses.append("LOWER(v.vendor_code) = LOWER(?)")
        params.append(vendor_code)
    if q:
        like = f"%{q.lower()}%"
        clauses.append("(LOWER(po.po_no) LIKE ? OR LOWER(po.description) LIKE ? OR LOWER(v.vendor_name) LIKE ?)")
        params.extend([like, like, like])
    sql = f"{PO_SELECT} WHERE {' AND '.join(clauses)} ORDER BY po.po_date DESC"
    with get_connection() as conn:
        return list(conn.execute(sql, params).fetchall())


def get_po_detail(user: DemoUser, po_no: str) -> dict[str, Any] | None:
    where, params = po_visibility_where(user)
    sql = f"{PO_SELECT} WHERE po.po_no = ? AND {where}"
    with get_connection() as conn:
        po = conn.execute(sql, [po_no, *params]).fetchone()
        if not po:
            return None
        po_id = po["po_id"]
        po["items"] = list(conn.execute("SELECT * FROM po_items WHERE po_id = ? ORDER BY sequence_no", [po_id]).fetchall())
        po["cost_allocations"] = list(conn.execute("SELECT * FROM cost_allocations WHERE po_id = ?", [po_id]).fetchall())
        po["approval_route"] = list(conn.execute("SELECT * FROM approval_routes WHERE po_id = ? ORDER BY step_order", [po_id]).fetchall())
        po["goods_receipts"] = list(conn.execute("SELECT * FROM goods_receipts WHERE po_id = ?", [po_id]).fetchall())
        po["purchase_authorizations"] = list(conn.execute("SELECT * FROM purchase_authorizations WHERE po_id = ?", [po_id]).fetchall())
        return po


def search_vendors(user: DemoUser, q: str) -> list[dict[str, Any]]:
    where, params = po_visibility_where(user)
    like = f"%{q.lower()}%"
    sql = f"""
    SELECT DISTINCT v.vendor_id, v.vendor_code, v.vendor_name, v.fmsd_approved
    FROM vendors v
    JOIN purchase_orders po ON po.vendor_id = v.vendor_id
    WHERE {where}
      AND (LOWER(v.vendor_name) LIKE ? OR LOWER(v.vendor_code) LIKE ?)
    ORDER BY v.vendor_name
    """
    with get_connection() as conn:
        return list(conn.execute(sql, [*params, like, like]).fetchall())


def get_pa_status(user: DemoUser, po_no: str | None = None, vendor_code: str | None = None) -> list[dict[str, Any]]:
    where, params = po_visibility_where(user)
    clauses = [where]
    if po_no:
        clauses.append("LOWER(po.po_no) = LOWER(?)")
        params.append(po_no)
    if vendor_code:
        clauses.append("LOWER(v.vendor_code) = LOWER(?)")
        params.append(vendor_code)
    sql = f"""
    SELECT
      pa.pa_no,
      pa.pa_amount,
      pa.pa_status,
      pa.payment_status,
      pa.expected_payment_date,
      pa.finance_owner,
      po.po_no,
      po.description,
      po.currency,
      po.po_amount_original,
      v.vendor_name
    FROM purchase_authorizations pa
    JOIN purchase_orders po ON po.po_id = pa.po_id
    JOIN vendors v ON v.vendor_id = po.vendor_id
    WHERE {' AND '.join(clauses)}
    ORDER BY pa.created_at DESC
    """
    with get_connection() as conn:
        return list(conn.execute(sql, params).fetchall())


def pending_approvals(user: DemoUser) -> list[dict[str, Any]]:
    if user.role == "Admin":
        user_filter = ""
        params: list[object] = []
    else:
        user_filter = "AND ar.approver_user_id = ?"
        params = [user.user_id]
    sql = f"""
    SELECT
      po.po_no,
      po.description,
      po.status,
      po.currency,
      po.po_amount_original,
      po.po_date,
      v.vendor_name,
      ar.approver_role,
      ar.approver_name,
      ar.escalation_rule
    FROM approval_routes ar
    JOIN purchase_orders po ON po.po_id = ar.po_id
    JOIN vendors v ON v.vendor_id = po.vendor_id
    WHERE ar.action_status = 'Pending'
      AND po.is_sensitive = 0
      {user_filter}
    ORDER BY po.po_date DESC
    """
    with get_connection() as conn:
        return list(conn.execute(sql, params).fetchall())


def budget_summary(user: DemoUser, account_code: str | None = None) -> list[dict[str, Any]]:
    params: list[object] = []
    clauses: list[str] = []
    if user.role != "Admin":
        clauses.append("cost_centre_code = ?")
        params.append(user.cost_centre_code)
    if account_code:
        clauses.append("account_code = ?")
        params.append(account_code)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with get_connection() as conn:
        return list(conn.execute(f"SELECT * FROM budgets {where} ORDER BY account_code", params).fetchall())


def insert_audit_log(
    user_key: str,
    conversation_id: str | None,
    question: str,
    intent: str,
    tool_calls_json: str,
    final_answer: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs
            (user_key, conversation_id, question, intent, tool_calls_json, final_answer)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [user_key, conversation_id, question, intent, tool_calls_json, final_answer],
        )
        conn.commit()
