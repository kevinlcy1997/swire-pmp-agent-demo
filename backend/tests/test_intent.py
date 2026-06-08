from backend.agent_api.intent import classify_intent, extract_po_no, extract_status_filter


def test_extract_po_no() -> None:
    assert extract_po_no("Show PO FAIT2015600") == "FAIT2015600"
    assert extract_po_no("Show me PO RESTRICTED001") == "RESTRICTED001"


def test_extract_status_filter() -> None:
    assert extract_status_filter("my approved POs") == "Approved"
    assert extract_status_filter("show rejected POs") == "Rejected"
    assert extract_status_filter("my pending POs") == "pending"
    assert extract_status_filter("pending endorser POs") == "Pending Endorser"
    assert extract_status_filter("show all POs") is None
    assert extract_status_filter("list my purchase orders") is None


def test_classify_payment_status() -> None:
    assert classify_intent("What's the payment status of my lobby signage PO?") == "payment_status"


def test_classify_pending_approvals() -> None:
    assert classify_intent("What is pending my approval?") == "pending_approvals"


def test_classify_my_po_lists() -> None:
    assert classify_intent("Show my pending POs") == "pending_pos"
    assert classify_intent("show all of my POs") == "all_pos"
    assert classify_intent("show all my POs") == "all_pos"
    assert classify_intent("show my purchase orders") == "all_pos"
    assert classify_intent("all my purchase orders") == "all_pos"


def test_classify_process_analytics() -> None:
    assert classify_intent("longest wait time PO") == "longest_waiting_po"
    assert classify_intent("PO approval pending which party?") == "po_pending_party_analysis"
    assert classify_intent("Where is PO CPAC2015601 stuck?") == "po_approval_progress"
    assert classify_intent("show monthly PO volume") == "po_volume_summary"
    assert classify_intent("show delayed approval summary") == "delayed_approval_summary"
