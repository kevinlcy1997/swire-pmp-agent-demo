from __future__ import annotations

import subprocess
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.agent_api.main import app as agent_app
from backend.data.seed_demo_db import seed


@pytest.fixture(scope="module", autouse=True)
def mock_pmp_server():
    seed()
    process = subprocess.Popen(
        [
            "py",
            "-3",
            "-m",
            "uvicorn",
            "backend.mock_pmp_api.main:app",
            "--port",
            "8001",
            "--log-level",
            "warning",
        ]
    )
    for _ in range(30):
        try:
            response = httpx.get("http://127.0.0.1:8001/health", timeout=1)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("mock PMP server did not start")
    yield
    process.terminate()
    process.wait(timeout=10)


client = TestClient(agent_app)


def test_agent_answers_coco_payment_status() -> None:
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "What's the payment status of my lobby signage PO?", "conversation_id": "test-coco"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "PA12345" in answer
    assert "Pending Payment Processing" in answer
    assert "Source: PMP API" in answer


def test_agent_does_not_leak_restricted_po_to_coco() -> None:
    response = client.post(
        "/api/chat",
        headers={"X-Demo-User": "alice"},
        json={"message": "Show me PO RESTRICTED001.", "conversation_id": "test-restricted"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "couldn't find an authorized PO" in answer
    assert "Restricted Security Works" not in answer
    assert "250,000" not in answer


def test_same_question_differs_by_role() -> None:
    payload = {"message": "What is pending my approval?", "conversation_id": "test-role"}
    coco = client.post("/api/chat", headers={"X-Demo-User": "alice"}, json=payload).json()["answer"]
    nam = client.post("/api/chat", headers={"X-Demo-User": "bob"}, json=payload).json()["answer"]
    assert "no authorized procurement items pending your approval" in coco
    assert "CPAC2015601" in nam
    assert coco != nam
