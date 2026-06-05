from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.shared.config import DB_PATH


SCHEMA = """
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS goods_receipts;
DROP TABLE IF EXISTS purchase_authorizations;
DROP TABLE IF EXISTS approval_routes;
DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS cost_allocations;
DROP TABLE IF EXISTS po_items;
DROP TABLE IF EXISTS purchase_orders;
DROP TABLE IF EXISTS vendors;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  user_key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  department TEXT NOT NULL,
  cost_centre_code TEXT NOT NULL,
  role TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE vendors (
  vendor_id INTEGER PRIMARY KEY,
  vendor_code TEXT UNIQUE NOT NULL,
  vendor_name TEXT NOT NULL,
  payee_name TEXT,
  contact_email TEXT,
  fmsd_approved INTEGER NOT NULL DEFAULT 0,
  is_sensitive INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE purchase_orders (
  po_id INTEGER PRIMARY KEY,
  po_no TEXT UNIQUE NOT NULL,
  po_date TEXT NOT NULL,
  po_type TEXT NOT NULL,
  status TEXT NOT NULL,
  currency TEXT NOT NULL,
  po_amount_original REAL NOT NULL,
  po_amount_base REAL NOT NULL,
  finance_team TEXT NOT NULL,
  project_code TEXT NOT NULL,
  description TEXT NOT NULL,
  notes TEXT,
  vendor_id INTEGER NOT NULL,
  submitter_user_id TEXT NOT NULL,
  cost_centre_code TEXT NOT NULL,
  percent_left REAL NOT NULL DEFAULT 100,
  outstand_amount_original REAL NOT NULL DEFAULT 0,
  is_sensitive INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id),
  FOREIGN KEY(submitter_user_id) REFERENCES users(user_id)
);

CREATE TABLE po_items (
  item_id INTEGER PRIMARY KEY,
  po_id INTEGER NOT NULL,
  sequence_no INTEGER NOT NULL,
  item_type TEXT NOT NULL,
  description TEXT NOT NULL,
  unit_cost REAL NOT NULL,
  quantity REAL NOT NULL,
  item_amount REAL NOT NULL,
  FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
);

CREATE TABLE cost_allocations (
  allocation_id INTEGER PRIMARY KEY,
  po_id INTEGER NOT NULL,
  account_code TEXT NOT NULL,
  account_description TEXT NOT NULL,
  business_unit_code TEXT NOT NULL,
  year_month TEXT NOT NULL,
  allocated_cost_original REAL NOT NULL,
  allocated_cost_hkd REAL NOT NULL,
  FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
);

CREATE TABLE budgets (
  budget_id INTEGER PRIMARY KEY,
  cost_centre_code TEXT NOT NULL,
  account_code TEXT NOT NULL,
  project_code TEXT NOT NULL,
  year INTEGER NOT NULL,
  yearly_budget REAL NOT NULL,
  ytm_used REAL NOT NULL,
  remaining_budget REAL NOT NULL,
  budget_status TEXT NOT NULL
);

CREATE TABLE approval_routes (
  route_id INTEGER PRIMARY KEY,
  po_id INTEGER NOT NULL,
  step_order INTEGER NOT NULL,
  approver_role TEXT NOT NULL,
  approver_user_id TEXT NOT NULL,
  approver_name TEXT NOT NULL,
  action_status TEXT NOT NULL,
  action_at TEXT,
  escalation_rule TEXT,
  FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id),
  FOREIGN KEY(approver_user_id) REFERENCES users(user_id)
);

CREATE TABLE purchase_authorizations (
  pa_id INTEGER PRIMARY KEY,
  pa_no TEXT UNIQUE NOT NULL,
  po_id INTEGER NOT NULL,
  pa_amount REAL NOT NULL,
  pa_status TEXT NOT NULL,
  payment_status TEXT NOT NULL,
  expected_payment_date TEXT,
  finance_owner TEXT,
  created_by_user_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
);

CREATE TABLE goods_receipts (
  receipt_id INTEGER PRIMARY KEY,
  po_id INTEGER NOT NULL,
  receipt_date TEXT NOT NULL,
  quantity_received REAL NOT NULL,
  condition TEXT NOT NULL,
  received_by_user_id TEXT NOT NULL,
  FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
);

CREATE TABLE audit_logs (
  audit_id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_key TEXT NOT NULL,
  conversation_id TEXT,
  question TEXT NOT NULL,
  intent TEXT NOT NULL,
  tool_calls_json TEXT NOT NULL,
  final_answer TEXT NOT NULL
);
"""


def seed() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            """
            INSERT INTO users
            (user_id, user_key, name, email, department, cost_centre_code, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("618731", "alice", "Alice Tan", "alice.tan@swireproperties.com", "CPAC - Cityplaza Management Office", "067007", "Submitter"),
                ("782144", "bob", "Bob Chen", "bob.chen@swireproperties.com", "CPAC - Cityplaza Management Office", "067007", "Endorser"),
                ("900201", "finance", "Carol Wong", "carol.wong@swireproperties.com", "HFIN - Head Office FIN", "HFIN", "Finance"),
                ("000001", "admin", "Admin Demo", "admin.demo@swireproperties.com", "Digital / IT", "ALL", "Admin"),
                ("700445", "diana", "Diana Lau", "diana.lau@swireproperties.com", "PPAC - Pacific Place Management Office", "088888", "Submitter"),
                ("811002", "tko_peter", "Edward Ho", "edward.ho@swireproperties.com", "TKOT - TKO Gateway Management Office", "055012", "Submitter"),
                ("811003", "ie_jenny", "Fiona Yip", "fiona.yip@swireproperties.com", "IEAS - Island East Management Office", "033009", "Submitter"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO vendors
            (vendor_id, vendor_code, vendor_name, payee_name, contact_email, fmsd_approved, is_sensitive)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "BRI001", "BrightSign Ltd", "BrightSign Ltd", "billing@brightsign.example", 1, 0),
                (2, "SIT008", "SIT VENDOR", "SIT PAYEE", "sit@example.test", 0, 0),
                (3, "SEC999", "Restricted Security Works Ltd", "Restricted Security Works Ltd", "restricted@example.test", 1, 1),
                (4, "GRN002", "GreenTech Maintenance Ltd", "GreenTech Maintenance Ltd", "accounts@greentech.example", 1, 0),
                (5, "FSE003", "FireSafe Engineering Co", "FireSafe Engineering Co", "billing@firesafe.example", 1, 0),
                (6, "ACE004", "ACE Elevator Services Ltd", "ACE Elevator Services Ltd", "invoice@ace-elevator.example", 1, 0),
            ],
        )
        conn.executemany(
            """
            INSERT INTO purchase_orders
            (po_id, po_no, po_date, po_type, status, currency, po_amount_original, po_amount_base,
             finance_team, project_code, description, notes, vendor_id, submitter_user_id,
             cost_centre_code, percent_left, outstand_amount_original, is_sensitive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "FAIT2015600", "2026-05-22", "Type 1 - Standard PO", "Approved", "HKD", 45000, 45000, "CPAC - Cityplaza Management Office", "General - (ALL) General", "Lobby signage replacement - Cityplaza Tower 1", "Submitted from vendor quotation", 1, "618731", "067007", 0, 0, 0),
                (2, "CPAC2015601", "2026-05-29", "Type 1 - Standard PO", "Pending Endorser", "HKD", 128000, 128000, "CPAC - Cityplaza Management Office", "General - (ALL) General", "Lift lobby marble repair", "Escalate if not endorsed within 1 working day", 2, "618731", "067007", 100, 128000, 0),
                (3, "PPAC2017777", "2026-05-20", "Type 1 - Standard PO", "Pending Endorser", "HKD", 78000, 78000, "PPAC - Pacific Place Management Office", "General - (ALL) General", "Pacific Place signage refresh", "Outside Coco cost centre", 1, "700445", "088888", 100, 78000, 0),
                (4, "RESTRICTED001", "2026-05-18", "Type 1 - Standard PO", "Approved", "HKD", 250000, 250000, "EXEC - Executive Office", "Confidential", "Restricted executive security works", "Sensitive demo record", 3, "700445", "999999", 20, 50000, 1),
                (5, "PPAC2018801", "2026-05-25", "Type 1 - Standard PO", "Approved", "HKD", 92000, 92000, "PPAC - Pacific Place Management Office", "General - (ALL) General", "Pacific Place L3 washroom renovation", "Maggie submitted", 4, "700445", "088888", 40, 36800, 0),
                (6, "TKOT2019001", "2026-05-15", "Type 1 - Standard PO", "Approved", "HKD", 185000, 185000, "TKOT - TKO Gateway Management Office", "General - (ALL) General", "TKO Gateway carpark barrier replacement", "TKO property - only admin visible to demo users", 6, "811002", "055012", 60, 111000, 0),
                (7, "TKOT2019002", "2026-05-28", "Type 1 - Standard PO", "Pending Endorser", "HKD", 67000, 67000, "TKOT - TKO Gateway Management Office", "General - (ALL) General", "TKO Gateway lobby LED panel installation", "TKO property pending", 1, "811002", "055012", 100, 67000, 0),
                (8, "IEAS2019003", "2026-05-10", "Type 1 - Standard PO", "Approved", "HKD", 320000, 320000, "IEAS - Island East Management Office", "General - (ALL) General", "Island East fire alarm system upgrade", "Island East property", 5, "811003", "033009", 15, 48000, 0),
                (9, "IEAS2019004", "2026-05-30", "Type 1 - Standard PO", "Pending Endorser", "HKD", 145000, 145000, "IEAS - Island East Management Office", "General - (ALL) General", "Island East B2 chiller pipe repair", "Island East pending", 4, "811003", "033009", 100, 145000, 0),
                (10, "CPAC2018802", "2026-05-27", "Type 1 - Standard PO", "Approved", "HKD", 56000, 56000, "CPAC - Cityplaza Management Office", "General - (ALL) General", "Cityplaza Tower 2 corridor lighting upgrade", "Another Coco PO", 4, "618731", "067007", 50, 28000, 0),
            ],
        )
        conn.executemany(
            """
            INSERT INTO po_items
            (po_id, sequence_no, item_type, description, unit_cost, quantity, item_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, "Others", "Lobby signage design and installation", 45000, 1, 45000),
                (2, 1, "Repair", "Lift lobby marble repair", 128000, 1, 128000),
                (3, 1, "Others", "Pacific Place signage refresh", 78000, 1, 78000),
                (4, 1, "Security", "Restricted works", 250000, 1, 250000),
                (5, 1, "Renovation", "L3 washroom full renovation", 92000, 1, 92000),
                (6, 1, "Repair", "Carpark barrier system replacement", 185000, 1, 185000),
                (7, 1, "Others", "LED panel supply and installation", 67000, 1, 67000),
                (8, 1, "Repair", "Fire alarm system full upgrade", 320000, 1, 320000),
                (9, 1, "Repair", "B2 chiller pipe repair and insulation", 145000, 1, 145000),
                (10, 1, "Others", "Corridor lighting LED upgrade", 56000, 1, 56000),
            ],
        )
        conn.executemany(
            """
            INSERT INTO cost_allocations
            (po_id, account_code, account_description, business_unit_code, year_month, allocated_cost_original, allocated_cost_hkd)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "067007.010204", "Building Maintenance - Signage", "067007", "05-2026", 45000, 45000),
                (2, "067007.010207", "Building Maintenance - Repairs", "067007", "05-2026", 128000, 128000),
                (3, "088888.010204", "Building Maintenance - Signage", "088888", "05-2026", 78000, 78000),
                (4, "999999.040404", "Confidential Security", "999999", "05-2026", 250000, 250000),
                (5, "088888.010301", "Building Maintenance - Renovation", "088888", "05-2026", 92000, 92000),
                (6, "055012.010207", "Building Maintenance - Repairs", "055012", "05-2026", 185000, 185000),
                (7, "055012.010204", "Building Maintenance - Signage", "055012", "05-2026", 67000, 67000),
                (8, "033009.010207", "Building Maintenance - Repairs", "033009", "05-2026", 320000, 320000),
                (9, "033009.010207", "Building Maintenance - Repairs", "033009", "05-2026", 145000, 145000),
                (10, "067007.010204", "Building Maintenance - Signage", "067007", "05-2026", 56000, 56000),
            ],
        )
        conn.executemany(
            """
            INSERT INTO budgets
            (cost_centre_code, account_code, project_code, year, yearly_budget, ytm_used, remaining_budget, budget_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("067007", "067007.010204", "General", 2026, 500000, 221000, 279000, "Sufficient"),
                ("067007", "067007.010207", "General", 2026, 800000, 692000, 108000, "Near Limit"),
                ("088888", "088888.010204", "General", 2026, 350000, 180000, 170000, "Sufficient"),
                ("088888", "088888.010301", "General", 2026, 600000, 412000, 188000, "Sufficient"),
                ("055012", "055012.010207", "General", 2026, 900000, 520000, 380000, "Sufficient"),
                ("055012", "055012.010204", "General", 2026, 400000, 310000, 90000, "Near Limit"),
                ("033009", "033009.010207", "General", 2026, 1200000, 865000, 335000, "Sufficient"),
                ("999999", "999999.040404", "Confidential", 2026, 1000000, 900000, 100000, "Restricted"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO approval_routes
            (po_id, step_order, approver_role, approver_user_id, approver_name, action_status, action_at, escalation_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, "Submitter", "618731", "Alice Tan", "Approved", "2026-05-22T15:43:00", None),
                (1, 2, "Endorser", "782144", "Bob Chen", "Approved", "2026-05-23T09:30:00", None),
                (2, 1, "Submitter", "618731", "Alice Tan", "Approved", "2026-05-29T10:00:00", None),
                (2, 2, "Endorser", "782144", "Bob Chen", "Pending", None, "Escalate in 1 working day"),
                (3, 2, "Endorser", "782144", "Bob Chen", "Pending", None, "Escalate in 2 working days"),
                (4, 2, "Approver", "000001", "Admin Demo", "Approved", "2026-05-19T12:00:00", None),
                (5, 1, "Submitter", "700445", "Diana Lau", "Approved", "2026-05-25T11:00:00", None),
                (5, 2, "Endorser", "782144", "Bob Chen", "Approved", "2026-05-26T09:00:00", None),
                (6, 1, "Submitter", "811002", "Edward Ho", "Approved", "2026-05-15T10:00:00", None),
                (6, 2, "Endorser", "782144", "Bob Chen", "Approved", "2026-05-16T14:00:00", None),
                (7, 1, "Submitter", "811002", "Edward Ho", "Approved", "2026-05-28T09:00:00", None),
                (7, 2, "Endorser", "782144", "Bob Chen", "Pending", None, "Escalate in 3 working days"),
                (8, 1, "Submitter", "811003", "Fiona Yip", "Approved", "2026-05-10T09:30:00", None),
                (8, 2, "Endorser", "782144", "Bob Chen", "Approved", "2026-05-11T15:00:00", None),
                (9, 1, "Submitter", "811003", "Fiona Yip", "Approved", "2026-05-30T10:00:00", None),
                (9, 2, "Endorser", "782144", "Bob Chen", "Pending", None, "Escalate in 2 working days"),
                (10, 1, "Submitter", "618731", "Alice Tan", "Approved", "2026-05-27T14:00:00", None),
                (10, 2, "Endorser", "782144", "Bob Chen", "Approved", "2026-05-28T10:00:00", None),
            ],
        )
        conn.executemany(
            """
            INSERT INTO purchase_authorizations
            (pa_no, po_id, pa_amount, pa_status, payment_status, expected_payment_date, finance_owner, created_by_user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("PA12345", 1, 45000, "Pending", "Pending Payment Processing", "2026-06-12", "Carol Wong", "618731", "2026-06-06T09:00:00"),
                ("PA54321", 4, 200000, "Approved", "Paid", "2026-05-30", "Carol Wong", "700445", "2026-05-20T09:00:00"),
                ("PA67890", 5, 55200, "Approved", "Paid", "2026-06-01", "Carol Wong", "700445", "2026-05-28T09:00:00"),
                ("PA11111", 6, 185000, "Pending", "Pending Payment Processing", "2026-06-15", "Carol Wong", "811002", "2026-06-01T09:00:00"),
                ("PA22222", 8, 272000, "Approved", "Paid", "2026-06-03", "Carol Wong", "811003", "2026-05-20T09:00:00"),
                ("PA33333", 10, 28000, "Pending", "Pending Payment Processing", "2026-06-10", "Carol Wong", "618731", "2026-06-02T09:00:00"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO goods_receipts
            (po_id, receipt_date, quantity_received, condition, received_by_user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "2026-06-05", 1, "Good", "618731"),
                (4, "2026-05-25", 1, "Good", "700445"),
                (5, "2026-06-01", 1, "Good", "700445"),
                (6, "2026-06-03", 1, "Good", "811002"),
                (8, "2026-05-25", 1, "Good", "811003"),
                (10, "2026-06-04", 1, "Good", "618731"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
    print(f"Seeded demo database at {DB_PATH}")
