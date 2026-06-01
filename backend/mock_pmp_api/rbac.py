from __future__ import annotations

from backend.shared.demo_users import DemoUser


def po_visibility_where(user: DemoUser, alias: str = "po") -> tuple[str, list[object]]:
    if user.role == "Admin":
        return "1 = 1", []
    if user.role == "Finance":
        return f"({alias}.is_sensitive = 0 OR EXISTS (SELECT 1 FROM purchase_authorizations pa WHERE pa.po_id = {alias}.po_id))", []
    if user.role in {"Submitter", "Endorser", "Approver"}:
        return (
            f"""(
                {alias}.is_sensitive = 0
                AND (
                    {alias}.submitter_user_id = ?
                    OR {alias}.cost_centre_code = ?
                    OR EXISTS (
                        SELECT 1 FROM approval_routes ar
                        WHERE ar.po_id = {alias}.po_id
                        AND ar.approver_user_id = ?
                    )
                )
            )""",
            [user.user_id, user.cost_centre_code, user.user_id],
        )
    return "0 = 1", []


def can_view_payment(user: DemoUser) -> bool:
    return user.role in {"Finance", "Admin", "Submitter", "Endorser", "Approver"}
