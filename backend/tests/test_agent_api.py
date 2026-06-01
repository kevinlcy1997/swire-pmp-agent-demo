from fastapi.testclient import TestClient

from backend.agent_api.main import app
from backend.data.seed_demo_db import seed


def setup_module() -> None:
    seed()


def test_agent_chat_returns_payment_status_from_pmp_api() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "coco"},
        json={"message": "What's the payment status of my lobby signage PO?", "conversation_id": "test-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_key"] == "coco"
    assert "PA12345" in data["answer"]
    assert "Source: PMP API" in data["answer"]


def test_agent_does_not_leak_restricted_po_to_coco() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "coco"},
        json={"message": "Show me PO RESTRICTED001", "conversation_id": "test-2"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "couldn't find an authorized PO" in answer
    assert "Restricted Security Works" not in answer
    assert "250,000" not in answer
