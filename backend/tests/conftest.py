"""Configure LLM mode for tests.

Set USE_REAL_LLM = True  to test with Azure OpenAI (requires credentials in .env).
Set USE_REAL_LLM = False to test with deterministic rule-based fallback (faster, no API calls).
"""

import backend.shared.config as config

config.USE_REAL_LLM = True
