from backend.agent_api.intent import classify_intent, extract_po_no


def test_extract_po_no() -> None:
    assert extract_po_no("Show PO FAIT2015600") == "FAIT2015600"
    assert extract_po_no("Show me PO RESTRICTED001") == "RESTRICTED001"


def test_classify_payment_status() -> None:
    assert classify_intent("What's the payment status of my lobby signage PO?") == "payment_status"


def test_classify_pending_approvals() -> None:
    assert classify_intent("What is pending my approval?") == "pending_approvals"
