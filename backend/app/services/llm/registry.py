import logging
from typing import Dict, Iterable, List, Optional, Type

from app.core.config import settings
from app.core.interfaces.llm import LLMProvider

logger = logging.getLogger(__name__)

# Canonical provider name -> implementation class (lazy imports to avoid cycles)
_REGISTRY: Dict[str, str] = {
    "openrouter": "app.services.llm.openrouter_provider:OpenRouterProvider",
    "openai": "app.services.llm.openai_provider:OpenAIProvider",
    "groq": "app.services.llm.groq_provider:GroqProvider",
    "gemini": "app.services.llm.gemini_provider:GeminiProvider",
    "google": "app.services.llm.gemini_provider:GeminiProvider",
    "anthropic": "app.services.llm.anthropic_provider:AnthropicProvider",
    "claude": "app.services.llm.anthropic_provider:AnthropicProvider",
    "azure": "app.services.llm.azure_provider:AzureOpenAIProvider",
}

# Preference order when LLM_PROVIDER is unset/unknown
_DEFAULT_ORDER = ("openrouter", "openai", "groq", "gemini", "anthropic", "azure")

# Key settings attrs used to decide whether a provider is configured
_KEY_ATTRS: Dict[str, tuple] = {
    "openrouter": ("OPENROUTER_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "anthropic": ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    "azure": ("AZURE_OPENAI_API_KEY",),
}


def _load_class(path: str) -> Type[LLMProvider]:
    module_path, _, cls_name = path.partition(":")
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


def normalize_provider(name: str) -> str:
    name = (name or "").strip().lower()
    if name == "google":
        return "gemini"
    if name == "claude":
        return "anthropic"
    return name


def available_providers() -> List[str]:
    """Provider names that currently have at least one API key configured."""
    result = []
    for name in _REGISTRY:
        canonical = normalize_provider(name)
        if canonical in result:
            continue
        attrs = _KEY_ATTRS.get(name, ())
        if any(getattr(settings, a, "") for a in attrs):
            if canonical == "azure" and not (
                settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_DEPLOYMENT
            ):
                continue
            result.append(canonical)
    return result


def is_configured(name: str) -> bool:
    return normalize_provider(name) in available_providers()


def create_provider(name: str) -> LLMProvider:
    canonical = normalize_provider(name)
    # pick first registry key that maps to this canonical name
    for reg_name, path in _REGISTRY.items():
        if normalize_provider(reg_name) == canonical:
            return _load_class(path)()
    raise ValueError(
        f"Unknown LLM provider '{name}'. Valid: {', '.join(sorted(set(normalize_provider(r) for r in _REGISTRY)))}"
    )


class FallbackChain(LLMProvider):
    """Tries each configured provider in order until one succeeds."""

    def __init__(self, providers: List[LLMProvider], names: Optional[List[str]] = None):
        if not providers:
            raise ValueError("FallbackChain requires at least one provider")
        self.providers = providers
        self.names = names or [type(p).__name__ for p in providers]

    def _run(self, method: str, system_prompt: str, user_prompt: str, **kwargs):
        from app.services.llm.gemini_provider import GeminiContentBlockedError

        errors: List[str] = []
        for idx, provider in enumerate(self.providers):
            try:
                return getattr(provider, method)(system_prompt, user_prompt, **kwargs)
            except GeminiContentBlockedError:
                # Content policy rejections should surface to the caller, not silently
                # reroute to another vendor.
                raise
            except Exception as e:
                errors.append(f"{self.names[idx]}: {e}")
                logger.warning(
                    "LLM provider %s failed (%s); trying next in chain",
                    self.names[idx],
                    e,
                )
        raise RuntimeError(
            "All LLM providers failed. Configure at least one API key "
            f"(tried: {'; '.join(errors)})"
        )

    def generate_text(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return self._run("generate_text", system_prompt, user_prompt, **kwargs)

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict:
        result = self._run("generate_json", system_prompt, user_prompt, **kwargs)
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object from LLM chain")
        return result


def _parse_chain(pref: Optional[str], exclude: Iterable[str]) -> List[str]:
    exclude_set = {normalize_provider(x) for x in exclude}

    ordered: List[str] = []
    primary = normalize_provider(pref or settings.LLM_PROVIDER or "openrouter")
    ordered.append(primary)

    fallbacks_raw = settings.LLM_FALLBACK_PROVIDERS or ""
    for part in fallbacks_raw.split(","):
        part = normalize_provider(part)
        if part and part not in ordered:
            ordered.append(part)

    for name in _DEFAULT_ORDER:
        if name not in ordered:
            ordered.append(name)

    return [n for n in ordered if n not in exclude_set]


def get_llm(
    prefer: Optional[str] = None,
    exclude: Iterable[str] = (),
) -> LLMProvider:
    """
    Return the preferred provider if configured, otherwise a FallbackChain over
    every configured provider (primary first, then LLM_FALLBACK_PROVIDERS order).
    """
    chain_names = _parse_chain(prefer, exclude)
    configured = [n for n in chain_names if is_configured(n)]

    if not configured:
        # Nothing configured: return the primary anyway so callers get a clear
        # "API key required" error from the provider itself.
        name = chain_names[0] if chain_names else "openrouter"
        logger.warning("No LLM API keys configured; defaulting to %s", name)
        return create_provider(name)

    if len(configured) == 1:
        return create_provider(configured[0])

    providers = [create_provider(n) for n in configured]
    return FallbackChain(providers, names=configured)


# Convenience: module-level accessor used by AI services
def default_llm() -> LLMProvider:
    return get_llm()
