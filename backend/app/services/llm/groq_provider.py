from app.services.llm.base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    provider_name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"
    key_settings_attrs = ("GROQ_API_KEY",)
    model_settings_attr = "GROQ_MODEL"
