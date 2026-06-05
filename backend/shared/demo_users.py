from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoUser:
    user_key: str
    user_id: str
    name: str
    role: str
    department: str
    cost_centre_code: str
    description: str


DEMO_USERS: dict[str, DemoUser] = {
    "coco": DemoUser(
        user_key="coco",
        user_id="618731",
        name="Alice Tan",
        role="Submitter",
        department="CPAC - Cityplaza Management Office",
        cost_centre_code="067007",
        description="Property Manager. Sees her own and cost-centre-authorized POs.",
    ),
    "nam": DemoUser(
        user_key="nam",
        user_id="782144",
        name="Bob Chen",
        role="Endorser",
        department="CPAC - Cityplaza Management Office",
        cost_centre_code="067007",
        description="Endorser. Sees items pending his approval.",
    ),
    "finance": DemoUser(
        user_key="finance",
        user_id="900201",
        name="Carol Wong",
        role="Finance",
        department="HFIN - Head Office FIN",
        cost_centre_code="HFIN",
        description="Finance user. Sees payment and PA processing details.",
    ),
    "admin": DemoUser(
        user_key="admin",
        user_id="000001",
        name="Admin Demo",
        role="Admin",
        department="Digital / IT",
        cost_centre_code="ALL",
        description="Demo superuser. Sees all seeded records.",
    ),
    "maggie": DemoUser(
        user_key="maggie",
        user_id="700445",
        name="Diana Lau",
        role="Submitter",
        department="PPAC - Pacific Place Management Office",
        cost_centre_code="088888",
        description="Property Manager at Pacific Place. Only sees her own POs.",
    ),
}


def get_demo_user(user_key: str | None) -> DemoUser:
    if not user_key:
        return DEMO_USERS["coco"]
    normalized = user_key.strip().lower()
    if normalized not in DEMO_USERS:
        raise KeyError(f"Unknown demo user: {user_key}")
    return DEMO_USERS[normalized]
