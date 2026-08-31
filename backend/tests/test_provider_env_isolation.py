"""The test environment must not inherit real provider credentials.

`backend/app/main.py` loads `conf/.env` on import, so before the autouse
fixture in `conftest.py` scrubbed them, a developer with keys on disk ran a
different failover chain than CI did: `_plan_providers()` saw a configured
Cloudflare it was never told about, so a test asserting "every provider is
cooled down, so release the soonest one" found a healthy third provider and the
release never happened. It failed locally and passed in CI.
"""

import os

from tests.conftest import PROVIDER_ENV_VARS


def test_no_provider_credentials_leak_into_a_test():
    leaked = [name for name in PROVIDER_ENV_VARS if os.environ.get(name)]
    assert leaked == [], (
        "provider credentials visible to a test: "
        f"{leaked}. Tests must set the credentials they need, so the "
        "configured-provider set does not depend on the developer's conf/.env."
    )
