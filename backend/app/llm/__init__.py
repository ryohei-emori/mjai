"""
LLM provider module for AI text correction suggestions.
Supports Groq (primary) and Cloudflare Workers AI (failover).
"""

from .suggestions import generate_suggestions
from .parser import parse_model_output, ParsedResponse, CorrectionSuggestion

__all__ = [
    "generate_suggestions",
    "parse_model_output",
    "ParsedResponse",
    "CorrectionSuggestion",
]
