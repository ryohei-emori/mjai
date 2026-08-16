import sys
from pathlib import Path

import pytest

# Allow `import app.xxx` when pytest is run from the repo root or from backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def _isolate_provider_state():
    """
    Clear credential cooldowns and buffered health observations between tests.

    These are process-global by design — the failover chain now skips a provider
    whose whole pool is cooled down — so a cooldown left behind by one test would
    silently change which provider another test's chain calls.
    """
    from app.llm.key_pool import reset_key_pool_state
    from app.llm.provider_health import reset_provider_health_state

    reset_key_pool_state()
    reset_provider_health_state()
    yield
    reset_key_pool_state()
    reset_provider_health_state()
