"""
Shared LLM credential availability, so a refusal is learned once per limit
instead of once per request.

`key_pool.py` already skips credentials that were refused — but it holds that in
process memory, and every serverless invocation gets a fresh process. A user
whose Gemini free-tier quota is exhausted therefore paid one 429 per pooled key
on *every* generation, against the quota that was already exhausted, before Groq
was asked. This module carries the cooldowns across invocations through one
Postgres table (`provider_health`, migration 008).

Three properties are load-bearing:

- **It cannot fail a request.** Every read and write is bounded and swallows its
  errors; a missing table, an unreachable database or a slow query degrades to
  exactly the per-process behavior that existed before.
- **It records what the provider said, not a guess.** None of the three
  providers offers a free way to *ask* how much quota is left — a probe costs the
  request we are trying to save — but they all answer on the way out (Groq's
  `retry-after` / `x-ratelimit-reset-*` headers, Gemini's `RetryInfo`). Hints are
  clamped (`MAX_COOLDOWN_S`) because free-tier daily limits produce hints
  measured in hours, and trusting one means a single 429 can withhold a provider
  until tomorrow — including when the hint is wrong or the key has been
  replaced. Re-checking every 15 minutes costs one fast 429; being wrong for a
  day does not.
- **It never holds a secret.** Rows identify a credential by a hash prefix. A
  pool index would be shorter but is positional: reordering `GEMINI_API_KEYS`
  would silently re-point every row at a different key.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, List, NamedTuple, Optional, Sequence

from .budget import seconds_left
from .key_pool import (
    DEFAULT_COOLDOWN_SECONDS,
    load_cloudflare_credentials,
    load_gemini_credentials,
    load_groq_credentials,
    mark_cooldown,
)

logger = logging.getLogger(__name__)

# Ceiling on any recorded cooldown. See the module docstring: the clamp is
# deliberately the conservative direction — wasting one round trip beats losing a
# provider for a day to a stale or wrong hint.
MAX_COOLDOWN_S = 900.0

# The write happens on a path that has already failed, so it is only worth doing
# when the request can spare the connection. Missing a write costs nothing but
# the next request re-learning the refusal, which is the old behavior; overrunning
# the deadline to perform one is the failure mode `fix-function-invocation-timeout`
# existed to remove.
FLUSH_TIMEOUT_S = 2.5
FLUSH_MIN_SLACK_S = 4.0

# Bound on the one read the generation path makes. Same value the prompt lookup
# used on its own before the two reads were combined, so the pre-generation phase
# did not get slower.
SHARED_STATE_TIMEOUT_S = 3.0

# Observations are kept if a flush is skipped, so a later request in the same warm
# process can still store them (a recover_at already in the past is filtered out on
# read). The cap only stops an unflushable buffer from growing without bound.
MAX_PENDING_OBSERVATIONS = 32

_PROVIDER_LOADERS = {
    "gemini": load_gemini_credentials,
    "groq": load_groq_credentials,
    "cloudflare": load_cloudflare_credentials,
}


class Observation(NamedTuple):
    """One refusal worth remembering after this request ends."""

    provider: str
    # Empty when the limit is credential-wide (Cloudflare) rather than per model.
    model: str
    fingerprint: str
    recover_at: datetime
    reason: str


_pending: List[Observation] = []


def reset_provider_health_state() -> None:
    """Drop buffered observations (for tests)."""
    _pending.clear()


def credential_fingerprint(credential_id: str) -> str:
    """Stable, non-reversible label for a credential id."""
    return hashlib.sha256(credential_id.encode("utf-8")).hexdigest()[:16]


def clamp_cooldown_seconds(seconds: Optional[float]) -> float:
    """Turn a provider hint (or its absence) into a cooldown we will honor."""
    if seconds is None or seconds <= 0:
        return DEFAULT_COOLDOWN_SECONDS
    return min(seconds, MAX_COOLDOWN_S)


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    """
    Seconds from a `Retry-After` header, which is either a count or an HTTP date.

    Returns None for anything unparseable, so a malformed header falls back to
    the default cooldown rather than to an arbitrary number.
    """
    if not value:
        return None
    raw = value.strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s|m|h)")
_DURATION_UNITS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}


def parse_duration_hint(value: Optional[str]) -> Optional[float]:
    """
    Seconds from Groq's rate-limit reset format, e.g. `2m59.56s`, `7.66s`, `180ms`.

    A bare number is read as seconds. Returns None when nothing parses, so an
    unfamiliar format falls back to the default cooldown.
    """
    if not value:
        return None
    raw = value.strip()
    parts = _DURATION_PART.findall(raw)
    if parts:
        return sum(float(amount) * _DURATION_UNITS[unit] for amount, unit in parts)
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def seed_cooldowns(rows: Sequence[dict]) -> int:
    """
    Apply what earlier requests learned to this process's cooldowns.

    Seeding the existing pool state, rather than consulting the store during
    selection, keeps every selection rule (round-robin, model scoping, exclusion
    of already-tried keys) working unchanged on shared knowledge — and keeps the
    database out of the provider retry loop, which runs under a wall-clock
    deadline.

    The wall-clock instant is converted to a monotonic cooldown here because this
    is the only place both clocks are in hand: a monotonic value is meaningless in
    another process, and an absolute instant cannot be compared with one.

    Rows naming a credential this deployment does not have (a key that was
    rotated out) are ignored.
    """
    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    seeded = 0
    for provider, loader in _PROVIDER_LOADERS.items():
        matching = [r for r in rows if (r.get("provider") or "") == provider]
        if not matching:
            continue
        by_fingerprint = {
            credential_fingerprint(cred.id): cred for cred in loader()
        }
        for row in matching:
            cred = by_fingerprint.get(row.get("credentialFingerprint") or "")
            if cred is None:
                continue
            recover_at = row.get("recoverAt")
            if not isinstance(recover_at, datetime):
                continue
            if recover_at.tzinfo is None:
                recover_at = recover_at.replace(tzinfo=timezone.utc)
            remaining = (recover_at - now).total_seconds()
            if remaining <= 0:
                continue
            mark_cooldown(
                cred.id,
                min(remaining, MAX_COOLDOWN_S),
                scope=(row.get("model") or None),
                carried_over=True,
            )
            seeded += 1
    if seeded:
        logger.info(
            "Seeded %s credential cooldown(s) learned by earlier requests", seeded
        )
    return seeded


def observe_refusal(
    provider: str,
    credential_id: str,
    cooldown_seconds: float,
    *,
    model: Optional[str] = None,
    reason: str = "",
) -> None:
    """Remember a refusal for later requests. Buffered, never written inline."""
    if len(_pending) >= MAX_PENDING_OBSERVATIONS:
        return
    _pending.append(
        Observation(
            provider=provider,
            model=model or "",
            fingerprint=credential_fingerprint(credential_id),
            recover_at=datetime.now(timezone.utc)
            + timedelta(seconds=max(0.0, cooldown_seconds)),
            reason=reason[:200],
        )
    )


async def load_shared_state(setting_key: str) -> tuple[Optional[dict], List[dict]]:
    """
    Read the stored setting row and the in-effect availability rows together.

    One connection for both, because pooler connect time dominates either query:
    consulting availability therefore costs the generation path nothing it was not
    already paying for the prompt lookup.

    Returns `(None, [])` on any failure or on a read slower than
    `SHARED_STATE_TIMEOUT_S`. Both features have a working default (built-in
    prompt, per-process cooldowns), so neither is worth a failed generation.
    """
    from ..db_helper import fetch_setting_and_provider_health

    try:
        return await asyncio.wait_for(
            fetch_setting_and_provider_health(setting_key),
            timeout=SHARED_STATE_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Shared state read exceeded %.1fs; using per-process defaults",
            SHARED_STATE_TIMEOUT_S,
        )
        return None, []
    except Exception as e:
        logger.warning("Shared state read failed; using per-process defaults: %s", e)
        return None, []


async def flush_observations(deadline_monotonic: Optional[float] = None) -> int:
    """
    Write buffered refusals, if the request can still spare the time.

    Returns the number of records written (0 when there was nothing to write, no
    time to write it, or the write failed).
    """
    if not _pending:
        return 0
    if seconds_left(deadline_monotonic) < FLUSH_MIN_SLACK_S:
        logger.info(
            "Skipping provider health write: %.1fs left, under the %.1fs it needs",
            seconds_left(deadline_monotonic),
            FLUSH_MIN_SLACK_S,
        )
        return 0

    from ..db_helper import upsert_provider_health

    records = _record_tuples(_pending)
    try:
        await asyncio.wait_for(
            upsert_provider_health(records), timeout=FLUSH_TIMEOUT_S
        )
    except Exception as e:
        # Best-effort by design: the next request re-learns what was not stored.
        logger.warning("Provider health write failed: %s", e)
        return 0
    _pending.clear()
    return len(records)


def _record_tuples(observations: Iterable[Observation]) -> List[tuple]:
    return [
        (o.provider, o.model, o.fingerprint, o.recover_at, o.reason)
        for o in observations
    ]
