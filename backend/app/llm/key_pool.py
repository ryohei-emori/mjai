"""
Environment-driven API key / credential pool for LLM providers.

Loads multiple Groq keys or Cloudflare (account_id, token) pairs, selects
via round-robin among non-cooled-down entries, and supports marking
credentials unavailable after 401/403/429.

Env convention (plural wins when non-empty after parse):
  GROQ_API_KEYS=key1,key2          else GROQ_API_KEY
  CLOUDFLARE_ACCOUNT_IDS=id1,id2   + CLOUDFLARE_API_TOKENS=tok1,tok2
                                   else CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN
  GEMINI_API_KEYS=key1,key2        else GEMINI_API_KEY
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple, TypeVar

_TCred = TypeVar("_TCred")

DEFAULT_COOLDOWN_SECONDS = 60.0


class _Cooldown(NamedTuple):
    """When a credential becomes selectable again, and where we learned it."""

    until: float
    # True when seeded from shared storage, i.e. an earlier request paid for this
    # refusal. Skipping without any call in *this* request is worth saying out
    # loud in a failure breakdown, since it means no provider was even asked.
    carried_over: bool


class PoolAvailability(NamedTuple):
    """Whether a provider is worth calling at all, from cooldown state alone."""

    configured: bool
    # Every (credential, scope) pair is cooled down: calling would only collect
    # the same refusals again.
    all_cooled: bool
    # Soonest expiry across those pairs; None when nothing is cooled down.
    recover_in_s: Optional[float]
    # No cooled entry was learned in this request.
    carried_over: bool


_lock = threading.Lock()
# cooldown key -> _Cooldown
_cooldowns: Dict[str, _Cooldown] = {}
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


def _dedupe_by_id(credentials: Sequence[_TCred]) -> List[_TCred]:
    """Preserve first occurrence of each credential.id (identical keys collapse)."""
    seen: Set[str] = set()
    out: List[_TCred] = []
    for cred in credentials:
        cred_id = cred.id  # type: ignore[attr-defined]
        if cred_id in seen:
            continue
        seen.add(cred_id)
        out.append(cred)
    return out


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


@dataclass(frozen=True)
class GeminiCredential:
    api_key: str

    @property
    def id(self) -> str:
        return f"gemini:{self.api_key}"

    @property
    def label(self) -> str:
        return redact_secret(self.api_key)


def load_groq_credentials() -> List[GroqCredential]:
    """Load Groq keys: GROQ_API_KEYS if non-empty, else GROQ_API_KEY.

    Plural wins when non-empty (singular is not merged). Duplicate keys
    in the plural list are collapsed to one entry.
    """
    plural = _split_csv(os.environ.get("GROQ_API_KEYS"))
    if plural:
        return _dedupe_by_id([GroqCredential(api_key=k) for k in plural])
    single = (os.environ.get("GROQ_API_KEY") or "").strip()
    if single:
        return [GroqCredential(api_key=single)]
    return []


def load_cloudflare_credentials() -> List[CloudflareCredential]:
    """Load CF pairs from parallel lists or singular back-compat vars.

    Mismatched non-empty parallel list lengths yield an empty pool (no
    silent mis-pairing). Duplicate pairs are collapsed. Plural lists win
    when either is set (singular is not merged).
    """
    ids = _split_csv(os.environ.get("CLOUDFLARE_ACCOUNT_IDS"))
    tokens = _split_csv(os.environ.get("CLOUDFLARE_API_TOKENS"))
    if ids or tokens:
        if len(ids) != len(tokens) or not ids:
            return []
        return _dedupe_by_id(
            [
                CloudflareCredential(account_id=i, api_token=t)
                for i, t in zip(ids, tokens)
            ]
        )
    account_id = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    api_token = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if account_id and api_token:
        return [CloudflareCredential(account_id=account_id, api_token=api_token)]
    return []


def load_gemini_credentials() -> List[GeminiCredential]:
    """Load Gemini keys: GEMINI_API_KEYS if non-empty, else GEMINI_API_KEY.

    Plural wins when non-empty (singular is not merged). Duplicate keys
    in the plural list are collapsed to one entry.
    """
    plural = _split_csv(os.environ.get("GEMINI_API_KEYS"))
    if plural:
        return _dedupe_by_id([GeminiCredential(api_key=k) for k in plural])
    single = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if single:
        return [GeminiCredential(api_key=single)]
    return []


def credential_pool_index(credentials: Sequence, credential_id: str) -> int:
    """Return 0-based index of credential_id in the loaded pool, or -1."""
    for i, cred in enumerate(credentials):
        if cred.id == credential_id:
            return i
    return -1


def format_credential_ref(provider: str, index: int, label: str) -> str:
    """Safe log/error label: provider[index] + redacted secret label."""
    return f"{provider}[{index}] ({label})"


def _cooldown_key(credential_id: str, scope: Optional[str] = None) -> str:
    """Map key for cooldown. Optional scope = model id (Groq per-model limits)."""
    if scope:
        return f"{credential_id}::{scope}"
    return credential_id


def _live_cooldown(
    credential_id: str,
    now: float,
    scope: Optional[str] = None,
) -> Optional[_Cooldown]:
    """Cooldown still in effect for this credential/scope, or None."""
    key = _cooldown_key(credential_id, scope)
    entry = _cooldowns.get(key)
    if entry is None:
        return None
    if entry.until <= now:
        # Expired — drop entry lazily
        _cooldowns.pop(key, None)
        return None
    return entry


def _is_cooled_down(
    credential_id: str,
    now: float,
    scope: Optional[str] = None,
) -> bool:
    return _live_cooldown(credential_id, now, scope) is not None


def mark_cooldown(
    credential_id: str,
    seconds: float = DEFAULT_COOLDOWN_SECONDS,
    *,
    scope: Optional[str] = None,
    carried_over: bool = False,
) -> None:
    """Mark a credential unavailable until now + seconds.

    When ``scope`` is set (e.g. Groq model id), cooldown applies only to that
    scope so a different model can still use the same key.

    ``carried_over`` marks state seeded from shared storage rather than observed
    here, so a skip can say whether this request ever asked the provider.
    """
    with _lock:
        _cooldowns[_cooldown_key(credential_id, scope)] = _Cooldown(
            until=time.monotonic() + max(0.0, seconds),
            carried_over=carried_over,
        )


def pool_availability(
    credentials: Sequence,
    scopes: Sequence[Optional[str]] = (None,),
) -> PoolAvailability:
    """
    Summarize whether any (credential, scope) pair is still worth trying.

    ``scopes`` is the set of models the caller may rotate over, since Gemini and
    Groq limits are per model: a pool is only unusable when every key is cooled
    down for every model it could pick, not when the key that answered last is.
    """
    if not credentials:
        return PoolAvailability(
            configured=False, all_cooled=False, recover_in_s=None, carried_over=False
        )
    effective_scopes = list(scopes) or [None]
    with _lock:
        now = time.monotonic()
        remaining: List[float] = []
        carried: List[bool] = []
        for cred in credentials:
            for scope in effective_scopes:
                entry = _live_cooldown(cred.id, now, scope)
                if entry is None:
                    return PoolAvailability(
                        configured=True,
                        all_cooled=False,
                        recover_in_s=None,
                        carried_over=False,
                    )
                remaining.append(entry.until - now)
                carried.append(entry.carried_over)
    return PoolAvailability(
        configured=True,
        all_cooled=True,
        recover_in_s=min(remaining),
        carried_over=all(carried),
    )


def release_soonest_cooldown(
    credentials: Sequence,
    scopes: Sequence[Optional[str]] = (None,),
) -> Optional[str]:
    """
    Drop the cooldown expiring soonest so one real attempt can still be made.

    Recorded availability describes the past and can be stale, so it must never
    be the sole reason no provider is called; the credential closest to
    recovering is the most plausible candidate to spend that attempt on. Returns
    the credential id that was released, or None when nothing was cooled down.
    """
    effective_scopes = list(scopes) or [None]
    with _lock:
        now = time.monotonic()
        soonest_key: Optional[str] = None
        soonest_cred: Optional[str] = None
        soonest_until = float("inf")
        for cred in credentials:
            for scope in effective_scopes:
                entry = _live_cooldown(cred.id, now, scope)
                if entry is not None and entry.until < soonest_until:
                    soonest_until = entry.until
                    soonest_key = _cooldown_key(cred.id, scope)
                    soonest_cred = cred.id
        if soonest_key is None:
            return None
        _cooldowns.pop(soonest_key, None)
        return soonest_cred


def _acquire(
    provider: str,
    credentials: Sequence,
    exclude_ids: Optional[Sequence[str]] = None,
    cooldown_scope: Optional[str] = None,
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
            if c.id not in excluded
            and not _is_cooled_down(c.id, now, cooldown_scope)
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
    *,
    cooldown_scope: Optional[str] = None,
) -> Optional[GroqCredential]:
    """Select a Groq key. ``cooldown_scope`` should be the model id in use."""
    return _acquire(
        "groq",
        load_groq_credentials(),
        exclude_ids,
        cooldown_scope,
    )


def acquire_cloudflare(
    exclude_ids: Optional[Sequence[str]] = None,
) -> Optional[CloudflareCredential]:
    return _acquire("cloudflare", load_cloudflare_credentials(), exclude_ids)


def acquire_gemini(
    exclude_ids: Optional[Sequence[str]] = None,
    *,
    cooldown_scope: Optional[str] = None,
) -> Optional[GeminiCredential]:
    """Select a Gemini key. ``cooldown_scope`` should be the model id in use."""
    return _acquire(
        "gemini",
        load_gemini_credentials(),
        exclude_ids,
        cooldown_scope,
    )


def is_groq_configured() -> bool:
    return bool(load_groq_credentials())


def is_cloudflare_configured() -> bool:
    return bool(load_cloudflare_credentials())


def is_gemini_configured() -> bool:
    return bool(load_gemini_credentials())


def cooldown_status_codes() -> Tuple[int, ...]:
    """HTTP statuses that trigger credential cooldown + next-key retry."""
    return (401, 403, 429)
