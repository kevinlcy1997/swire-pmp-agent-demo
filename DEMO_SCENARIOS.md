# Swire PMP Agent Demo — Testing Scenarios

This document provides step-by-step demo scenarios to showcase the AI assistant's **role-based access control (RBAC)**, structured markdown output, and multi-property data isolation.

> **Prerequisites:** All 4 services running (`.\start-all.ps1`). Open **http://localhost:5173**.

---

## Scenario 1: Same Question, Different Visibility

**Goal:** Show that the same question returns different data depending on the user's role and scope.

**Question:** `show all pos`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — Submitter, Cityplaza) | Sees **3 POs** — only her own CPAC POs (FAIT2015600, CPAC2015601, CPAC2018802) |
| 2 | `maggie` / `password123` (Diana Lau — Submitter, Pacific Place) | Sees **2 POs** — only her own PPAC POs (PPAC2017777, PPAC2018801) |
| 3 | `nam` / `password123` (Bob Chen — Endorser) | Sees **9 POs** — all non-sensitive POs across all properties (he is in every approval route) |
| 4 | `admin` / `password123` (Admin Demo) | Sees **all 10 POs** — including the sensitive RESTRICTED001 |

**Key takeaway:** Two submitters (Alice & Diana) at the same role level see completely different POs because they belong to different properties/cost centres.

---

## Scenario 2: Sensitive Data Wall

**Goal:** Prove that sensitive/restricted POs are hidden from unauthorized users with no data leakage.

**Question:** `Show PO RESTRICTED001`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — Submitter) | ❌ "couldn't find an authorized PO" — no vendor name, no amount leaked |
| 2 | `maggie` / `password123` (Diana Lau — Submitter) | ❌ Same denial — even though Diana submitted it, it's marked sensitive |
| 3 | `finance` / `password123` (Carol Wong — Finance) | ✅ Sees the PO — Finance can view it because a Purchase Authorization (PA54321) is linked |
| 4 | `admin` / `password123` (Admin Demo) | ✅ Sees full details — HKD 250,000, Restricted Security Works Ltd |

**Key takeaway:** Sensitive POs are completely invisible to unauthorized roles. No partial data leaks.

---

## Scenario 3: Cross-Property Isolation

**Goal:** Show that submitters cannot see POs from other properties, even non-sensitive ones.

**Question:** `Show PO TKOT2019001`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — Cityplaza) | ❌ Blocked — TKO Gateway is not her cost centre |
| 2 | `maggie` / `password123` (Diana Lau — Pacific Place) | ❌ Blocked — TKO Gateway is not her cost centre |
| 3 | `nam` / `password123` (Bob Chen — Endorser) | ✅ Sees the PO — he endorsed it (in the approval route) |
| 4 | `admin` / `password123` (Admin Demo) | ✅ Sees full details |

**Key takeaway:** Property-level data isolation is enforced. Only users in the approval chain or with higher roles can see cross-property POs.

---

## Scenario 4: Approval Queue by Role

**Goal:** Show that the approval queue is scoped to the user's authority level.

**Question:** `What is pending my approval?`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — Submitter) | "no authorized procurement items pending your approval" — submitters don't approve |
| 2 | `nam` / `password123` (Bob Chen — Endorser) | Sees **4 pending items**: CPAC2015601, PPAC2017777, TKOT2019002, IEAS2019004 — with escalation rules |
| 3 | `admin` / `password123` (Admin Demo) | Sees the same **4 pending items** — admin sees all pending across the org |

**Key takeaway:** Submitters see nothing in the approval queue. Endorsers see items assigned to them. Admin sees everything.

---

## Scenario 5: Payment Status with RBAC

**Goal:** Show payment tracking works correctly within RBAC scope.

**Question:** `What's the payment status of my lobby signage PO?`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan) | ✅ Sees PA12345 — Pending Payment Processing, expected date 2026-06-12 |
| 2 | `maggie` / `password123` (Diana Lau) | ✅ Sees the same PA — the PO (FAIT2015600) is visible to her via the PMP API search |
| 3 | `finance` / `password123` (Carol Wong) | ✅ Sees payment details — Finance has visibility on all POs with linked PAs |

---

## Scenario 6: Budget Visibility by Cost Centre

**Goal:** Show that budget data is scoped to the user's cost centre.

**Question:** `What's my budget situation?`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — cost centre 067007) | Sees **2 budget lines** — 067007 signage (Sufficient) and repairs (Near Limit) |
| 2 | `finance` / `password123` (Carol Wong — cost centre HFIN) | Sees **0 budget lines** — HFIN has no seeded budgets |
| 3 | `admin` / `password123` (Admin Demo) | Sees **all 8 budget lines** across all cost centres including Restricted |

**Key takeaway:** Each user only sees budgets for their own cost centre. Admin sees the full picture.

---

## Scenario 7: Pending POs (Submitter Comparison)

**Goal:** Side-by-side comparison of two submitters at the same role level.

**Question:** `Show my pending POs`

| Step | Login As | Expected Result |
|---|---|---|
| 1 | `coco` / `password123` (Alice Tan — Cityplaza) | Sees **1 PO**: CPAC2015601 (Lift lobby marble repair, HKD 128,000) |
| 2 | `maggie` / `password123` (Diana Lau — Pacific Place) | Sees **1 PO**: PPAC2017777 (Pacific Place signage refresh, HKD 78,000) |
| 3 | `admin` / `password123` (Admin Demo) | Sees **4 POs**: all pending POs across all properties |

**Key takeaway:** Same role, same question — completely different results based on cost centre ownership.

---

## Quick Reference: Demo Logins

| Username | Password | Display Name | Role | Property |
|---|---|---|---|---|
| `coco` | `password123` | Alice Tan | Submitter | Cityplaza (CPAC) |
| `nam` | `password123` | Bob Chen | Endorser | Cityplaza (CPAC) |
| `finance` | `password123` | Carol Wong | Finance | Head Office (HFIN) |
| `admin` | `password123` | Admin Demo | Admin | All |
| `maggie` | `password123` | Diana Lau | Submitter | Pacific Place (PPAC) |

## Quick Reference: Supported Questions

| Question | Intent |
|---|---|
| `show all pos` | List all POs in scope |
| `Show my pending POs` | Pending POs only |
| `What is pending my approval?` | Approval queue |
| `What's the payment status of my lobby signage PO?` | Payment tracking |
| `Have we paid BrightSign yet?` | Vendor payment lookup |
| `Show PO FAIT2015600` | Specific PO detail |
| `Show PO RESTRICTED001` | Sensitive PO test |
| `What's my budget situation?` | Budget summary |
