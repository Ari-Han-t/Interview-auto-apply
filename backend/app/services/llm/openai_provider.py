from app.services.llm.base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    provider_name = "openai"
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    key_settings_attrs = ("OPENAI_API_KEY",)
    model_settings_attr = "OPENAI_MODEL"
