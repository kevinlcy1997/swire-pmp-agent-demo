"""Verify all demo prompts end-to-end with USE_REAL_LLM=true via streaming."""
import httpx
import json
import sys

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def stream_chat(user, message, conv_id):
    """Call /api/chat/stream, return dict with intent, answer, events count."""
    body = json.dumps({"message": message, "conversation_id": conv_id})
    events = []
    with httpx.Client(timeout=60) as c:
        with c.stream(
            "POST", f"{BASE}/api/chat/stream",
            headers={"X-Demo-User": user, "Content-Type": "application/json"},
            content=body,
        ) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
    intent = ""
    for e in events:
        msg = e.get("message", "")
        if "Detected intent:" in msg:
            intent = msg.split("Detected intent: ")[1].rstrip(".")
    # Final answer = last content event with substantial text
    final = [e for e in events if "content" in e and len(e.get("content", "")) > 50]
    answer = final[-1]["content"] if final else ""
    tools = [e.get("tool") for e in events if "tool" in e and "source" not in e]
    return {"intent": intent, "answer": answer, "events": len(events), "tools": tools}


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {label}")
    else:
        FAIL += 1
        print(f"  FAIL: {label} -- {detail}")


def divider(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ── ALICE ──

divider("ALICE-1: what is my longest pending po")
r = stream_chat("alice", "what is my longest pending po", "a1")
print(f"  Intent: {r['intent']} | Events: {r['events']} | Tools: {r['tools']}")
print(f"  Answer preview: {r['answer'][:300]}")
check("intent = longest_waiting_po", r["intent"] == "longest_waiting_po", r["intent"])
check("CPAC2020001 in answer (14 days)", "CPAC2020001" in r["answer"], "missing CPAC2020001")
check("Victor Ng mentioned", "Victor Ng" in r["answer"], "missing Victor Ng")
check("no PPAC/TKOT/IEAS POs (out of scope)", "PPAC2020003" not in r["answer"], "leaked PPAC2020003")

divider("ALICE-2: what is the approval chain of CPAC2020001?")
r = stream_chat("alice", "what is the approval chain of CPAC2020001?", "a2")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:400]}")
check("intent = po_approval_progress", r["intent"] == "po_approval_progress", r["intent"])
check("Victor Ng in answer", "Victor Ng" in r["answer"], "missing Victor Ng")
check("Cost Controller mentioned", "Cost Controller" in r["answer"], "missing role")

divider("ALICE-3: draft reminder email to Victor Ng about CPAC2020001")
r = stream_chat("alice", "can you help me to draft a reminder email to Victor Ng about the PO CPAC2020001?", "a3")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:500]}")
check("LLM streaming used (events > 10)", r["events"] > 10, f"only {r['events']} events")
has_email = any(w in r["answer"].lower() for w in ["subject", "dear", "reminder", "regards"])
check("looks like email draft", has_email, "no email markers found")
check("mentions Victor Ng", "Victor Ng" in r["answer"], "missing Victor Ng")
check("mentions CPAC2020001", "CPAC2020001" in r["answer"], "missing PO number")

divider("ALICE-4: detail of PO TKOT2020008")
r = stream_chat("alice", "detail of PO TKOT2020008", "a4")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:300]}")
check("intent = po_detail", r["intent"] == "po_detail", r["intent"])
blocked = "couldn't find" in r["answer"].lower() or "not found" in r["answer"].lower() or "no authorized" in r["answer"].lower()
check("RBAC blocks TKOT PO for alice", blocked, "alice should NOT see TKO POs")

divider("ALICE-5: my approved POs")
r = stream_chat("alice", "my approved POs", "a5")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:400]}")
check("intent = all_pos", r["intent"] == "all_pos", r["intent"])
check("FAIT2015600 or CPAC2018802 in answer", "FAIT2015600" in r["answer"] or "CPAC2018802" in r["answer"])
check("no pending POs shown", "Pending Endorser" not in r["answer"] and "Pending Cost Controller" not in r["answer"], "pending POs leaked")

divider("ALICE-6: payment status of CPAC2018802")
r = stream_chat("alice", "payment status of CPAC2018802", "a6")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:400]}")
check("intent = payment_status or po_detail", r["intent"] in ("payment_status", "po_detail"), r["intent"])
check("CPAC2018802 in answer", "CPAC2018802" in r["answer"], "missing PO")

# ── BOB ──

divider("BOB-1: what is my pending pos")
r = stream_chat("bob", "what is my pending pos", "b1")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:500]}")
check("intent = pending_pos", r["intent"] == "pending_pos", r["intent"])
check("CPAC2015601 in answer", "CPAC2015601" in r["answer"], "missing CPAC2015601")
check("PPAC2017777 in answer (bob is endorser)", "PPAC2017777" in r["answer"], "missing PPAC2017777")
check("TKOT2019002 in answer", "TKOT2019002" in r["answer"], "missing TKOT2019002")
bob_sees_more = sum(1 for po in ["CPAC2015601","PPAC2017777","TKOT2019002","IEAS2019004","TKOT2020008"] if po in r["answer"])
check(f"bob sees 5+ pending POs (found {bob_sees_more})", bob_sees_more >= 5, f"only {bob_sees_more}")

# ── ADMIN ──

divider("ADMIN-1: what is the longest pending PO?")
r = stream_chat("admin", "what is the longest pending PO?", "ad1")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:400]}")
check("intent = longest_waiting_po", r["intent"] == "longest_waiting_po", r["intent"])
check("PPAC2020003 in answer (16 days, global longest)", "PPAC2020003" in r["answer"], "missing PPAC2020003")
check("Sarah Lee mentioned", "Sarah Lee" in r["answer"], "missing Sarah Lee")

divider("ADMIN-2: what is the approval chain of PO PPAC2020003")
r = stream_chat("admin", "what is the approval chain of PO PPAC2020003", "ad2")
print(f"  Intent: {r['intent']} | Events: {r['events']}")
print(f"  Answer preview: {r['answer'][:500]}")
check("intent = po_approval_progress", r["intent"] == "po_approval_progress", r["intent"])
check("Sarah Lee (Department Head)", "Sarah Lee" in r["answer"], "missing Sarah Lee")
check("Diana Lau (Submitter)", "Diana Lau" in r["answer"], "missing Diana Lau")
check("shows multi-step route", "Bob Chen" in r["answer"] and "Victor Ng" in r["answer"], "incomplete route")

# ── SUMMARY ──
print(f"\n{'='*70}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} checks")
print(f"{'='*70}")
sys.exit(1 if FAIL > 0 else 0)
