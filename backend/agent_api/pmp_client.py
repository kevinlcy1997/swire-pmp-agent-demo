from __future__ import annotations

from typing import Any

import httpx

from backend.shared.config import MOCK_PMP_BASE_URL
from backend.shared.demo_users import DemoUser


class PmpClient:
    def __init__(self, user: DemoUser, base_url: str = MOCK_PMP_BASE_URL) -> None:
        self.user = user
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-Demo-User": user.user_key}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=10.0) as client:
            response = await client.get(path, params=params)
            if response.status_code == 404:
                return {"records": [], "count": 0, "not_found": True, "detail": response.json().get("detail")}
            response.raise_for_status()
            return response.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=10.0) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

    async def list_pos(self, **params: Any) -> dict[str, Any]:
        return await self._get("/pmp-api/v1/ai/po/list", params=params)

    async def po_detail(self, po_no: str) -> dict[str, Any]:
        return await self._get(f"/pmp-api/v1/ai/po/{po_no}/detail")

    async def vendor_search(self, q: str) -> dict[str, Any]:
        return await self._get("/pmp-api/v1/ai/vendor/search", params={"q": q})

    async def pa_status(self, **params: Any) -> dict[str, Any]:
        return await self._get("/pmp-api/v1/ai/pa/status", params=params)

    async def pending_approvals(self) -> dict[str, Any]:
        return await self._get("/pmp-api/v1/ai/approval/pending")

    async def budget_summary(self, **params: Any) -> dict[str, Any]:
        return await self._get("/pmp-api/v1/ai/budget/summary", params=params)

    async def audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/pmp-api/v1/ai/audit", payload)
