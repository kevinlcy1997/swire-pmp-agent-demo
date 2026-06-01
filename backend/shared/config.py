from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = Path(os.getenv("SWIRE_DEMO_DB", str(DATA_DIR / "swire_demo.sqlite3")))

MOCK_PMP_BASE_URL = os.getenv("MOCK_PMP_BASE_URL", "http://127.0.0.1:8001")
USE_REAL_LLM = os.getenv("USE_REAL_LLM", "false").lower() == "true"
