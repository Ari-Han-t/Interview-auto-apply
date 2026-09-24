from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.llm.base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    provider_name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "openai/gpt-oss-120b"
    key_settings_attrs = ("OPENROUTER_API_KEY",)
    model_settings_attr = "OPENROUTER_MODEL"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=model)
        # OpenRouter-specific upstream routing preference (e.g. "Groq")
        upstream = settings.OPENROUTER_PROVIDER
        if upstream:
            self.extra_body = {"provider": {"order": [upstream], "allow_fallbacks": True}}
