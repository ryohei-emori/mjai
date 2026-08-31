import os
import sys
from pathlib import Path

import pytest

# Allow `import app.xxx` when pytest is run from the repo root or from backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


PROVIDER_ENV_VARS = (
    "GEMINI_API_KEY",
    "GEMINI_API_KEYS",
    "GEMINI_MODEL",
    "GEMINI_THINKING_LEVEL",
    "GROQ_API_KEY",
    "GROQ_API_KEYS",
    "GROQ_MODEL",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_ACCOUNT_IDS",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_API_TOKENS",
)


@pytest.fixture(autouse=True)
def _isolate_provider_state(request):
    """
    Clear credential cooldowns, buffered health observations, and provider
    credentials between tests.

    The cooldowns are process-global by design — the failover chain now skips a
    provider whose whole pool is cooled down — so a cooldown left behind by one
    test would silently change which provider another test's chain calls.

    The credentials are cleared for the same reason: which providers are
    configured decides which ones a pass plans to call. `backend/app/main.py`
    loads `conf/.env` on import, so a developer with real keys ran a different
    chain than CI did, and a test could pass on one and fail on the other.
    Tests set the credentials they need. The exception is the `integration`
    marker: those tests are opt-in live smokes whose whole point is to spend a
    real key, and their skip conditions are evaluated at collection time, before
    this fixture could put anything back.
    """
    from app.llm.key_pool import reset_key_pool_state
    from app.llm.provider_health import reset_provider_health_state

    keep_credentials = request.node.get_closest_marker("integration") is not None
    saved = (
        {}
        if keep_credentials
        else {name: os.environ.pop(name, None) for name in PROVIDER_ENV_VARS}
    )
    reset_key_pool_state()
    reset_provider_health_state()
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_key_pool_state()
        reset_provider_health_state()
