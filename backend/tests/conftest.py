"""Force rule-based mode for all tests so assertions match deterministic template output."""

import backend.shared.config as config

# Override before any test module imports the flag
config.USE_REAL_LLM = False
