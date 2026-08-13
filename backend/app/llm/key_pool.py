"""
Environment-driven API key / credential pool for LLM providers.

Loads multiple Groq keys or Cloudflare (account_id, token) pairs, selects
via round-robin among non-cooled-down entries, and supports marking
credentials unavailable after 401/403/429.

Env convention (plural wins when non-empty after parse):
  GROQ_API_KEYS=key1,key2          else GROQ_API_KEY
  CLOUDFLARE_ACCOUNT_IDS=id1,id2   + CLOUDFLARE_API_TOKENS=tok1,tok2
                                   else CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_COOLDOWN_SECONDS = 60.0

_lock = threading.Lock()
# credential_id -> monotonic deadline
_cooldowns: Dict[str, float] = {}
# provider name -> next round-robin index
_rr_index: Dict[str, int] = {}


def reset_key_pool_state() -> None:
    """Clear cooldown and round-robin state (for tests)."""
    with _lock:
        _cooldowns.clear()
        _rr_index.clear()


def redact_secret(value: str, prefix: int = 4, suffix: int = 4) -> str:
    """Return a short redacted label safe for logs."""
    if not value:
        return "<empty>"
    if len(value) <= prefix + suffix:
        return "***"
    return f"{value[:prefix]}…{value[-suffix:]}"


def _split_csv(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class GroqCredential:
    api_key: str

    @property
    def id(self) -> str:
        return f"groq:{self.api_key}"

    @property
    def label(self) -> str:
        return redact_secret(self.api_key)


@dataclass(frozen=True)
class CloudflareCredential:
    account_id: str
    api_token: str

    @property
    def id(self) -> str:
        return f"cf:{self.account_id}:{self.api_token}"

    @property
    def label(self) -> str:
        return f"{redact_secret(self.account_id, 4, 4)}/{redact_secret(self.api_token)}"


def load_groq_credentials() -> List[GroqCredential]:
    """Load Groq keys: GROQ_API_KEYS if non-empty, else GROQ_API_KEY."""
    plural = _split_csv(os.environ.get("GROQ_API_KEYS"))
    if plural:
        return [GroqCredential(api_key=k) for k in plural]
    single = (os.environ.get("GROQ_API_KEY") or "").strip()
    if single:
        return [GroqCredential(api_key=single)]
    return []


def load_cloudflare_credentials() -> List[CloudflareCredential]:
    """Load CF pairs from parallel lists or singular back-compat vars.

    Mismatched non-empty parallel list lengths yield an empty pool (no
    silent mis-pairing).
    """
    ids = _split_csv(os.environ.get("CLOUDFLARE_ACCOUNT_IDS"))
    tokens = _split_csv(os.environ.get("CLOUDFLARE_API_TOKENS"))
    if ids or tokens:
        if len(ids) != len(tokens) or not ids:
            return []
        return [
            CloudflareCredential(account_id=i, api_token=t)
            for i, t in zip(ids, tokens)
        ]
    account_id = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    api_token = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if account_id and api_token:
        return [CloudflareCredential(account_id=account_id, api_token=api_token)]
    return []


def _is_cooled_down(credential_id: str, now: float) -> bool:
    until = _cooldowns.get(credential_id)
    if until is None:
        return False
    if until <= now:
        # Expired — drop entry lazily
        _cooldowns.pop(credential_id, None)
        return False
    return True


def mark_cooldown(
    credential_id: str,
    seconds: float = DEFAULT_COOLDOWN_SECONDS,
) -> None:
    """Mark a credential unavailable until now + seconds."""
    with _lock:
        _cooldowns[credential_id] = time.monotonic() + max(0.0, seconds)


def _acquire(
    provider: str,
    credentials: Sequence,
    exclude_ids: Optional[Sequence[str]] = None,
):
    """Round-robin among credentials that are not cooled down / excluded."""
    if not credentials:
        return None
    excluded = set(exclude_ids or ())
    with _lock:
        now = time.monotonic()
        eligible_indices = [
            i
            for i, c in enumerate(credentials)
            if c.id not in excluded and not _is_cooled_down(c.id, now)
        ]
        if not eligible_indices:
            return None
        start = _rr_index.get(provider, 0) % len(credentials)
        # Walk from start in ring order, pick first eligible
        ordered = list(range(start, len(credentials))) + list(range(0, start))
        for idx in ordered:
            if idx in eligible_indices:
                _rr_index[provider] = (idx + 1) % len(credentials)
                return credentials[idx]
        return None


def acquire_groq(
    exclude_ids: Optional[Sequence[str]] = None,
) -> Optional[GroqCredential]:
    return _acquire("groq", load_groq_credentials(), exclude_ids)


def acquire_cloudflare(
    exclude_ids: Optional[Sequence[str]] = None,
) -> Optional[CloudflareCredential]:
    return _acquire("cloudflare", load_cloudflare_credentials(), exclude_ids)


def is_groq_configured() -> bool:
    return bool(load_groq_credentials())


def is_cloudflare_configured() -> bool:
    return bool(load_cloudflare_credentials())


def cooldown_status_codes() -> Tuple[int, ...]:
    """HTTP statuses that trigger credential cooldown + next-key retry."""
    return (401, 403, 429)
