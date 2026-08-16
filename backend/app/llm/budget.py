"""
Wall-clock budget arithmetic shared by the failover chain and the providers.

Vercel kills `api/index.py` at `maxDuration` (60s) with an opaque
FUNCTION_INVOCATION_TIMEOUT (504) that carries no pool diagnostics, no
`timed_out` flag and no partially generated critique — strictly worse for the
user than any app-level response. Staying under that limit is therefore an
invariant of every outbound call, not a best-effort check.

Before this module the chain only asked "has the deadline already passed?"
before starting a provider, while each call still used its own static timeout.
A Groq call with a 25s timeout could be started at t=44s (44 < 55, so the check
passed) and run to t=69s — the exact 504 the budget existed to prevent. Two
Gemini timeouts (22s each) plus one Groq timeout reach that without anything
exotic happening.

So a call is sized to the time that is actually left:

- `resolve_call_timeout()` clamps a provider's timeout to the remaining budget,
  and returns None when what is left is shorter than the provider's own
  measured latency — a 3s slice for a model that answers in 10s is not a call,
  it is a way to spend the budget a faster provider downstream could still use.
- Providers apply the resolved value as a hard ceiling per HTTP attempt, so
  neither key-pool retries nor httpx's per-operation timeouts (connect and read
  each get the full value) can push a call past the deadline.
"""

from __future__ import annotations

import time
from typing import Optional

# Must match `functions["api/index.py"].maxDuration` in the repo-root
# vercel.json — the hard limit this whole module exists to stay under.
PLATFORM_MAX_DURATION_S = 60.0

# Held back from the request budget for work that counts against the platform
# limit but not against anything the handler can measure: cold start (importing
# FastAPI, httpx, asyncpg and the JWT stack on a fresh isolate), JWT
# verification, and request/response transfer.
PLATFORM_RESERVE_S = 15.0

# Reserved after the last provider byte arrives: JSON parse, content checks,
# response serialization and the write back to the client.
RESPONSE_OVERHEAD_S = 1.5


def seconds_left(deadline_monotonic: Optional[float]) -> float:
    """Seconds until the deadline; +inf when the caller set no deadline."""
    if deadline_monotonic is None:
        return float("inf")
    return deadline_monotonic - time.monotonic()


def resolve_call_timeout(
    deadline_monotonic: Optional[float],
    provider_timeout: float,
    min_useful: float,
) -> Optional[float]:
    """
    Timeout for one HTTP attempt that cannot outlive the deadline.

    Returns None to mean "do not make this call": less time is left than the
    provider needs to answer at all, so attempting it would only burn the
    remainder of the budget.
    """
    usable = seconds_left(deadline_monotonic) - RESPONSE_OVERHEAD_S
    if usable < min_useful:
        return None
    return min(provider_timeout, usable)


def describe_skip(
    provider_name: str,
    deadline_monotonic: Optional[float],
    min_useful: float,
) -> str:
    """Ops-facing reason a provider was skipped, in the error/log breakdown."""
    return (
        f"{provider_name} skipped: {seconds_left(deadline_monotonic):.1f}s of the "
        f"request budget left, under the {min_useful:.0f}s a call needs"
    )
