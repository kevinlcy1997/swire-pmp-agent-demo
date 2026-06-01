from __future__ import annotations

import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.mock_pmp_api import repository
from backend.shared.demo_users import DEMO_USERS, DemoUser, get_demo_user

app = FastAPI(title="Swire Demo Mock PMP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(x_demo_user: Annotated[str | None, Header()] = None) -> DemoUser:
    try:
        return get_demo_user(x_demo_user)
    except KeyError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-pmp-api"}


@app.get("/pmp-api/v1/ai/demo/users")
def demo_users() -> list[dict[str, str]]:
    return [user.__dict__ for user in DEMO_USERS.values()]


@app.get("/pmp-api/v1/ai/po/list")
def po_list(
    user: Annotated[DemoUser, Depends(current_user)],
    status: str | None = None,
    vendor_code: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    records = repository.list_pos(user, status=status, vendor_code=vendor_code, q=q)
    return {"records": records, "count": len(records), "scope": user.user_key}


@app.get("/pmp-api/v1/ai/po/{po_no}/detail")
def po_detail(po_no: str, user: Annotated[DemoUser, Depends(current_user)]) -> dict[str, object]:
    record = repository.get_po_detail(user, po_no)
    if not record:
        raise HTTPException(status_code=404, detail="No authorized PO found for this user.")
    return {"record": record, "scope": user.user_key}


@app.get("/pmp-api/v1/ai/vendor/search")
def vendor_search(
    user: Annotated[DemoUser, Depends(current_user)],
    q: Annotated[str, Query(min_length=1)],
) -> dict[str, object]:
    records = repository.search_vendors(user, q)
    return {"records": records, "count": len(records), "scope": user.user_key}


@app.get("/pmp-api/v1/ai/pa/status")
def pa_status(
    user: Annotated[DemoUser, Depends(current_user)],
    po_no: str | None = None,
    vendor_code: str | None = None,
) -> dict[str, object]:
    records = repository.get_pa_status(user, po_no=po_no, vendor_code=vendor_code)
    return {"records": records, "count": len(records), "scope": user.user_key}


@app.get("/pmp-api/v1/ai/approval/pending")
def approval_pending(user: Annotated[DemoUser, Depends(current_user)]) -> dict[str, object]:
    records = repository.pending_approvals(user)
    return {"records": records, "count": len(records), "scope": user.user_key}


@app.get("/pmp-api/v1/ai/budget/summary")
def budget_summary(
    user: Annotated[DemoUser, Depends(current_user)],
    account_code: str | None = None,
) -> dict[str, object]:
    records = repository.budget_summary(user, account_code=account_code)
    return {"records": records, "count": len(records), "scope": user.user_key}


@app.post("/pmp-api/v1/ai/audit")
def write_audit(payload: dict[str, object], user: Annotated[DemoUser, Depends(current_user)]) -> dict[str, str]:
    repository.insert_audit_log(
        user_key=user.user_key,
        conversation_id=str(payload.get("conversation_id") or ""),
        question=str(payload.get("question") or ""),
        intent=str(payload.get("intent") or ""),
        tool_calls_json=json.dumps(payload.get("tool_calls") or [], ensure_ascii=False),
        final_answer=str(payload.get("final_answer") or ""),
    )
    return {"status": "ok"}
