# Swire PMP Agent Demo Backend

Python prototype for the Swire PMP Procurement / POPA AI Assistant demo.

The backend is split into two FastAPI services:

- `agent_api`: LangGraph-style agent API consumed by the frontend.
- `mock_pmp_api`: simulated PMP backend that owns SQLite access and enforces RBAC.

The agent never reads the demo database directly. It calls the mock PMP APIs, and those APIs return only records authorized for the active demo user.

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\data\seed_demo_db.py
```

## Run

Terminal 1:

```powershell
.\.venv\Scripts\python -m uvicorn backend.mock_pmp_api.main:app --reload --port 8001
```

Terminal 2:

```powershell
.\.venv\Scripts\python -m uvicorn backend.agent_api.main:app --reload --port 8000
```

## Frontend Contract

The frontend should call the agent API only.

```http
GET http://localhost:8000/api/demo/users
POST http://localhost:8000/api/chat/stream
X-Demo-User: alice
Content-Type: application/json

{
  "message": "What's the payment status of my lobby signage PO?",
  "conversation_id": "demo-1"
}
```

Supported `X-Demo-User` values:

- `alice`
- `bob`
- `finance`
- `admin`

## Demo Questions

- `What's the payment status of my lobby signage PO?`
- `Show my pending POs.`
- `What is pending my approval?`
- `Have we paid BrightSign yet?`
- `Show PO FAIT2015600.`
- `Show me PO RESTRICTED001.`

## Tests

```powershell
.\.venv\Scripts\python -m pytest backend\tests
```
