"""
Shared value type for provider calls that also report which model answered.

Gemini and Groq pick a model per request from an allow-list and may retry
against a second model, so the model that actually produced the content is only
knowable inside the provider's rotation wrapper. Those wrappers therefore
return `ProviderOutput` instead of a bare string, and `suggestions.py` passes
the model on to the API response and the correction-history row
(`editable-prompt-model-log-and-critique-fix`).

Providers with a single fixed model (Cloudflare) keep returning plain text; the
caller pairs it with that provider's model constant.
"""

from __future__ import annotations

from typing import NamedTuple


class ProviderOutput(NamedTuple):
    """Raw model output plus the model id that produced it."""

    text: str
    model: str
