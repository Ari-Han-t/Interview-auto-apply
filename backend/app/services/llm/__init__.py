"""Multi-provider LLM layer.

Usage:
    from app.services.llm import get_llm
    llm = get_llm()                 # primary + configured fallbacks
    llm = get_llm(prefer="groq")    # force a specific provider first
    text = llm.generate_text(system, user)
"""

from app.services.llm.registry import (
    FallbackChain,
    available_providers,
    create_provider,
    default_llm,
    get_llm,
    is_configured,
)

__all__ = [
    "FallbackChain",
    "available_providers",
    "create_provider",
    "default_llm",
    "get_llm",
    "is_configured",
]
