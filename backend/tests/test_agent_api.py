from fastapi.testclient import TestClient

from backend.agent_api.main import app
from backend.data.seed_demo_db import seed


def setup_module() -> None:
    seed()


def test_agent_chat_returns_payment_status_from_pmp_api() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "What's the payment status of my lobby signage PO?", "conversation_id": "test-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_key"] == "alice"
    assert "PA12345" in data["answer"]
    assert "Source: PMP API" in data["answer"]


def test_agent_does_not_leak_restricted_po_to_coco() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "Show me PO RESTRICTED001", "conversation_id": "test-2"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "couldn't find an authorized PO" in answer
    assert "Restricted Security Works" not in answer
    assert "250,000" not in answer


def test_agent_calculates_longest_waiting_po_from_scoped_details() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "bob"},
        json={"message": "longest wait time PO", "conversation_id": "test-longest"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "longest_waiting_po"
    assert "PPAC2017777" in data["answer"]
    assert "7 days" in data["answer"]
    assert data["tool_calls"][0]["tool"] == "pending_po_details"


def test_agent_groups_pending_pos_by_party() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "PO approval pending which party?", "conversation_id": "test-party"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "po_pending_party_analysis"
    assert "Bob Chen" in data["answer"]
    assert "CPAC2015601" in data["answer"]


def test_agent_explains_po_approval_progress() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "Where is PO CPAC2015601 stuck?", "conversation_id": "test-progress"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "po_approval_progress"
    assert "Bob Chen" in data["answer"]
    assert "4 days" in data["answer"]


def test_agent_summarizes_monthly_po_volume_from_authorized_pos() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "show monthly PO volume", "conversation_id": "test-volume"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "po_volume_summary"
    assert data["tool_calls"][0]["tool"] == "po_list"
    assert "2026-05" in data["answer"]
    assert "Approved" in data["answer"]
    assert "Pending Endorser" in data["answer"]
    assert "monthly PO volume" in data["answer"]


def test_agent_summarizes_delayed_approvals_from_pending_details() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "bob"},
        json={"message": "show delayed approval summary", "conversation_id": "test-delay"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "delayed_approval_summary"
    assert data["tool_calls"][0]["tool"] == "pending_po_details"
    assert "delayed / ageing approvals" in data["answer"]
    assert "PPAC2017777" in data["answer"]
    assert "Overdue" in data["answer"]


def test_unknown_analytics_fallback_lists_supported_examples() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "show procurement magic dashboard", "conversation_id": "test-fallback"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "Supported analytics examples" in answer
    assert "monthly PO volume" in answer
    assert "delayed approval summary" in answer
