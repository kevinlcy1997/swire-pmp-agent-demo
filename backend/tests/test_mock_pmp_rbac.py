from backend.data.seed_demo_db import seed
from backend.mock_pmp_api.repository import get_po_detail, list_pos, pending_approvals
from backend.shared.demo_users import get_demo_user


def setup_module() -> None:
    seed()


def test_coco_cannot_see_restricted_po() -> None:
    assert get_po_detail(get_demo_user("alice"), "RESTRICTED001") is None


def test_admin_can_see_restricted_po() -> None:
    record = get_po_detail(get_demo_user("admin"), "RESTRICTED001")
    assert record is not None
    assert record["po_no"] == "RESTRICTED001"


def test_coco_sees_own_cost_centre_pending_po() -> None:
    records = list_pos(get_demo_user("alice"), status="Pending Endorser")
    po_numbers = {record["po_no"] for record in records}
    assert "CPAC2015601" in po_numbers
    assert "RESTRICTED001" not in po_numbers


def test_nam_sees_items_pending_his_approval() -> None:
    records = pending_approvals(get_demo_user("bob"))
    po_numbers = {record["po_no"] for record in records}
    assert "CPAC2015601" in po_numbers
    assert "PPAC2017777" in po_numbers
    assert "RESTRICTED001" not in po_numbers
