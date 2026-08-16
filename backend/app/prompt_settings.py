"""
Shared, editable AI-correction system prompt stored in Postgres.

One global row (`app_settings.correction_system_prompt`) shared by every
allow-listed user, so a prompt edit made in one browser applies to everyone and
survives logout. Only the *rules body* is stored; the JSON output contract is
appended by `llm.prompts.build_system_prompt()` on every request, so a bad edit
can lower critique quality but can never break the response schema.

Row absence means "built-in default in effect" rather than a copy of the
default text, so improving the default in code still reaches anyone who has not
customized it. Reset therefore deletes the row (see migration 006).
"""

from __future__ import annotations

import logging
from typing import Optional, TypedDict

import asyncpg

from .db_helper import delete_setting, fetch_setting, upsert_setting
from .llm.prompts import SYSTEM_PROMPT_BODY

logger = logging.getLogger(__name__)

SETTING_KEY = "correction_system_prompt"

# Generous enough for the default prompt plus substantial additions, low enough
# that a paste accident cannot push the prompt past provider context limits.
MAX_PROMPT_LENGTH = 20000


class PromptValidationError(ValueError):
    """The submitted prompt is empty or exceeds MAX_PROMPT_LENGTH."""


class PromptStoreUnavailableError(RuntimeError):
    """`app_settings` does not exist yet (migration 006 not applied)."""

    def __init__(self) -> None:
        super().__init__(
            "Prompt storage is not available: the app_settings table does not "
            "exist. Apply backend/supabase/migrations/006_app_settings.sql to "
            "the database, then retry."
        )


class PromptSettings(TypedDict):
    """Effective prompt plus where it came from, for the settings UI."""

    systemPrompt: str
    defaultSystemPrompt: str
    isCustomized: bool
    updatedAt: Optional[str]
    updatedBy: Optional[str]


def validate_prompt(prompt: object) -> str:
    """
    Return the prompt to store, or raise PromptValidationError.

    Leading/trailing whitespace is trimmed; interior formatting (the rule
    sections are newline-separated) is preserved verbatim.
    """
    if not isinstance(prompt, str):
        raise PromptValidationError("systemPrompt must be a string")
    trimmed = prompt.strip()
    if not trimmed:
        raise PromptValidationError("systemPrompt must not be empty")
    if len(trimmed) > MAX_PROMPT_LENGTH:
        raise PromptValidationError(
            f"systemPrompt must be at most {MAX_PROMPT_LENGTH} characters "
            f"(got {len(trimmed)})"
        )
    return trimmed


def _to_settings(row: Optional[dict]) -> PromptSettings:
    """Shape a stored row (or its absence) as the settings response."""
    if row and (row.get("settingValue") or "").strip():
        updated_at = row.get("updatedAt")
        return {
            "systemPrompt": row["settingValue"],
            "defaultSystemPrompt": SYSTEM_PROMPT_BODY,
            "isCustomized": True,
            "updatedAt": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            "updatedBy": row.get("updatedBy"),
        }
    return {
        "systemPrompt": SYSTEM_PROMPT_BODY,
        "defaultSystemPrompt": SYSTEM_PROMPT_BODY,
        "isCustomized": False,
        "updatedAt": None,
        "updatedBy": None,
    }


async def get_prompt_settings() -> PromptSettings:
    """Read the effective prompt. Falls back to the default if the store fails."""
    try:
        row = await fetch_setting(SETTING_KEY)
    except Exception as e:
        # The settings UI stays usable (showing the default) when the store is
        # unreachable, rather than failing the whole dialog.
        logger.warning("Failed to read %s; serving built-in default: %s", SETTING_KEY, e)
        return _to_settings(None)
    return _to_settings(row)


async def save_prompt_settings(prompt: str, updated_by: Optional[str] = None) -> PromptSettings:
    """
    Validate and store a custom prompt.

    Raises PromptValidationError for bad input, and
    PromptStoreUnavailableError when the table has not been created yet — a
    save silently doing nothing would be worse than a message naming the
    migration to apply.
    """
    value = validate_prompt(prompt)
    try:
        row = await upsert_setting(SETTING_KEY, value, updated_by)
    except asyncpg.exceptions.UndefinedTableError:
        raise PromptStoreUnavailableError()
    return _to_settings(row)


async def reset_prompt_settings() -> PromptSettings:
    """Delete the stored prompt so the built-in default applies again."""
    try:
        await delete_setting(SETTING_KEY)
    except asyncpg.exceptions.UndefinedTableError:
        # Nothing stored can exist without the table, so the default is already
        # in effect and reset has nothing to undo.
        logger.warning("app_settings missing; reset is a no-op (default in effect)")
    return _to_settings(None)


def prompt_override_from_row(row: Optional[dict]) -> Optional[str]:
    """
    Return the stored custom prompt body for a generation request, or None.

    None means "use the built-in default", which is also what an absent row or an
    unreadable store produces: a settings-store problem must degrade to
    default-prompt suggestions, never fail generation. The read itself is done by
    `llm.provider_health.load_shared_state()`, which fetches this row and the
    credential-availability rows on one connection under one timeout, so
    consulting either costs the generation path a single round trip.
    """
    if not row:
        return None
    value = (row.get("settingValue") or "").strip()
    return value or None
