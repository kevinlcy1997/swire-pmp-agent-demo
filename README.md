# Swire PMP Agent Demo

An AI-powered procurement assistant prototype for **Swire Properties' PMP (Procurement Management Platform)**. The system uses a LangGraph agent pipeline to interpret natural-language questions about purchase orders, payments, approvals, vendors, and budgets — returning RBAC-scoped answers sourced exclusively from PMP APIs.

---

## Architecture Overview

```
┌─────────────┐     HTTP/SSE      ┌─────────────────────┐    HTTP (internal)    ┌───────────────────┐
│   Frontend   │ ───────────────▶  │  Agent API (:8000)  │ ──────────────────▶   │ Mock PMP API      │
│  (Frontend)  │ ◀──────────────── │  LangGraph pipeline │ ◀────────────────── │ (:8001)            │
└─────────────┘   JSON / SSE      └─────────────────────┘   JSON               └────────┬──────────┘
                                                                                         │
                                                                                         ▼
                                                                                ┌──────────────────┐
                                                                                │  SQLite Database  │
                                                                                │  (swire_demo.db)  │
                                                                                └──────────────────┘
```

The backend is split into **two FastAPI services**:

| Service | Port | Responsibility |
|---|---|---|
| **Agent API** (`backend/agent_api`) | 8000 | LangGraph-style agent that classifies user intent, selects tools, calls PMP APIs, and composes natural-language answers. Consumed by the frontend. |
| **Mock PMP API** (`backend/mock_pmp_api`) | 8001 | Simulated PMP backend that owns SQLite data access, enforces role-based access control (RBAC), and exposes REST endpoints. |

> **Key design principle:** The agent never reads the database directly. It calls the Mock PMP APIs, which return only records the active demo user is authorized to see.

---

## LangGraph Agent Pipeline

The agent processes each user message through a sequential graph of nodes:

```
load_user_context → classify_intent → select_tools → call_pmp_tools → compose_answer → write_audit_log
```

| Node | Description |
|---|---|
| `load_user_context` | Loads the current demo user's profile and permissions |
| `classify_intent` | Rule-based NLU that maps the message to an intent (e.g. `payment_status`, `pending_approvals`, `po_detail`) |
| `select_tools` | Builds a tool plan — a list of PMP API calls needed to answer the question |
| `call_pmp_tools` | Executes the planned API calls against the Mock PMP API via `PmpClient` |
| `compose_answer` | Formats API results into a human-readable response |
| `write_audit_log` | Logs the conversation turn (question, intent, tool calls, answer) for audit |

If LangGraph is not installed, the pipeline falls back to sequential async function calls.

---

## RBAC (Role-Based Access Control)

Access to PO data is controlled per-user through SQL visibility filters:

| Role | Visibility |
|---|---|
| **Admin** | Sees all records |
| **Finance** | Non-sensitive POs + any PO that has a linked Purchase Authorization |
| **Submitter / Endorser / Approver** | Non-sensitive POs they submitted, belong to their cost centre, or are in their approval route |

Sensitive POs (e.g. `RESTRICTED001`) are hidden from unauthorized users. This is enforced at the Mock PMP API layer.

---

## Demo Users

| Key | Name | Role | Department | Description |
|---|---|---|---|---|
| `coco` | Alice Tan | Submitter | CPAC - Cityplaza Management Office | Property Manager. Sees her own and cost-centre-authorized POs |
| `nam` | Bob Chen | Endorser | CPAC - Cityplaza Management Office | Endorser. Sees items pending his approval |
| `finance` | Carol Wong | Finance | HFIN - Head Office FIN | Finance user. Sees payment and PA processing details |
| `admin` | Admin Demo | Admin | Digital / IT | Demo superuser. Sees all seeded records |

---

## Project Structure

```
agent_demo/
├── backend/
│   ├── agent_api/              # LangGraph agent service (port 8000)
│   │   ├── main.py             # FastAPI app with /api/chat, /api/chat/stream, /api/demo/users
│   │   ├── graph.py            # LangGraph state graph definition and node functions
│   │   ├── intent.py           # Rule-based intent classification and PO number extraction
│   │   ├── composer.py         # Natural-language answer composition from API results
│   │   └── pmp_client.py       # Async HTTP client for calling Mock PMP API
│   ├── mock_pmp_api/           # Simulated PMP backend (port 8001)
│   │   ├── main.py             # FastAPI app with /pmp-api/v1/ai/* endpoints
│   │   ├── rbac.py             # SQL visibility filters per user role
│   │   └── repository.py       # SQLite queries for POs, PAs, vendors, budgets, approvals
│   ├── shared/                 # Shared modules used by both services
│   │   ├── config.py           # Paths, env vars (DB_PATH, MOCK_PMP_BASE_URL, USE_REAL_LLM)
│   │   ├── demo_users.py       # Demo user definitions (dataclass + lookup)
│   │   ├── models.py           # Pydantic models (ChatRequest, ChatResponse, StreamEvent)
│   │   └── sqlite.py           # SQLite connection factory with dict row support
│   ├── data/
│   │   └── seed_demo_db.py     # Database schema + seed data script
│   ├── tests/                  # Pytest test suite
│   │   ├── test_agent_api.py   # Agent chat endpoint tests
│   │   ├── test_agent_demo.py  # Full integration tests (spins up Mock PMP server)
│   │   ├── test_intent.py      # Intent classification unit tests
│   │   └── test_mock_pmp_rbac.py  # RBAC visibility tests
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React + Vite chatbot UI
│   ├── server.js               # Express server (port 3001) — auth, chat history, proxies to Agent API
│   ├── src/App.jsx             # Main React chat application
│   ├── src/App.css             # Application styles
│   └── package.json            # Node.js dependencies
├── pytest.ini                  # Pytest configuration
└── .gitignore
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**

---

## Quick Start (Full Stack)

### 1. Backend Setup

```powershell
# Create virtual environment and install Python deps
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt

# Seed the demo SQLite database
.\.venv\Scripts\python backend\data\seed_demo_db.py
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
cd ..
```

### 3. Start All Services (4 terminals)

**Terminal 1 — Mock PMP API (port 8001):**
```powershell
.\.venv\Scripts\python -m uvicorn backend.mock_pmp_api.main:app --reload --port 8001
```

**Terminal 2 — Agent API (port 8000):**
```powershell
.\.venv\Scripts\python -m uvicorn backend.agent_api.main:app --reload --port 8000
```

**Terminal 3 — Frontend server (port 3001):**
```powershell
cd frontend
npm run server
```

**Terminal 4 — Vite dev server (port 5173):**
```powershell
cd frontend
npm run dev
```

### 4. Open the Demo

1. Open **http://localhost:5173**
2. Login as **coco** / **password123**
3. Try a question: _"What's the payment status of my lobby signage PO?"_

### Demo Logins

| Username | Password | Role | Description |
|---|---|---|---|
| `coco` | `password123` | Submitter | Property Manager — sees her own POs |
| `nam` | `password123` | Endorser | Sees items pending his approval |
| `finance` | `password123` | Finance | Sees payment/PA details |
| `admin` | `password123` | Admin | Sees all records |
```

---

## Backend-Only Setup

## API Reference

### Agent API (consumed by the frontend)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/demo/users` | List available demo users |
| `POST` | `/api/chat` | Synchronous chat — returns full JSON response |
| `POST` | `/api/chat/stream` | Streaming chat — returns Server-Sent Events (SSE) |

#### Example Request

```http
POST http://localhost:8000/api/chat/stream
X-Demo-User: coco
Content-Type: application/json

{
  "message": "What's the payment status of my lobby signage PO?",
  "conversation_id": "demo-1"
}
```

#### SSE Event Types

| Event | Description |
|---|---|
| `thinking` | Agent progress updates (e.g. "Detected intent: payment_status") |
| `tool_call` | Tool invocation details (tool name, arguments, result count) |
| `tool_result` | Tool execution result summary |
| `answer` | Final natural-language answer |
| `done` | Stream complete |

### Mock PMP API (internal, called by the agent)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/pmp-api/v1/ai/po/list` | List POs (filterable by status, vendor, keyword) |
| `GET` | `/pmp-api/v1/ai/po/{po_no}/detail` | PO detail with items, approvals, PAs, GRs |
| `GET` | `/pmp-api/v1/ai/vendor/search` | Search vendors by name or code |
| `GET` | `/pmp-api/v1/ai/pa/status` | Payment authorization status |
| `GET` | `/pmp-api/v1/ai/approval/pending` | Items pending user's approval |
| `GET` | `/pmp-api/v1/ai/budget/summary` | Budget summary by cost centre |
| `POST` | `/pmp-api/v1/ai/audit` | Write audit log entry |

All Mock PMP endpoints require the `X-Demo-User` header for RBAC enforcement.

---

## Supported Intents

| Intent | Example Question |
|---|---|
| `payment_status` | "What's the payment status of my lobby signage PO?" |
| `vendor_payment_status` | "Have we paid BrightSign yet?" |
| `pending_approvals` | "What is pending my approval?" |
| `pending_pos` | "Show my pending POs." |
| `po_detail` | "Show PO FAIT2015600." |
| `budget_summary` | "What's my budget situation?" |
| `general_po_search` | Any other PO-related query |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SWIRE_DEMO_DB` | `backend/data/swire_demo.sqlite3` | Path to the SQLite database |
| `MOCK_PMP_BASE_URL` | `http://127.0.0.1:8001` | Base URL of the Mock PMP API |
| `USE_REAL_LLM` | `false` | Enable real LLM integration (future) |

---

## Running Tests

```powershell
# Unit tests (intent, RBAC, agent API)
.\.venv\Scripts\python -m pytest backend\tests

# Specific test file
.\.venv\Scripts\python -m pytest backend\tests\test_mock_pmp_rbac.py -v
```

> **Note:** `test_agent_demo.py` is a full integration test that automatically starts the Mock PMP server on port 8001.

---

## Database Schema

The seeded SQLite database contains the following tables:

| Table | Description |
|---|---|
| `users` | Demo user accounts |
| `vendors` | Vendor master data |
| `purchase_orders` | PO header records (includes `is_sensitive` flag) |
| `po_items` | PO line items |
| `cost_allocations` | Cost allocation records per PO |
| `budgets` | Budget data by cost centre and account code |
| `approval_routes` | Multi-step approval workflows per PO |
| `purchase_authorizations` | Payment authorization (PA) records |
| `goods_receipts` | Goods receipt records |
| `audit_logs` | Agent conversation audit trail |

---

## License

Internal prototype — Swire Properties / Protiviti.
