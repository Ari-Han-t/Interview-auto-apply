from app.services.llm.base import OpenAICompatibleProvider


class AnthropicProvider(OpenAICompatibleProvider):
    """Claude via Anthropic's OpenAI-compatible endpoint."""

    provider_name = "anthropic"
    base_url = "https://api.anthropic.com/v1/"
    default_model = "claude-sonnet-4-5"
    key_settings_attrs = ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
    model_settings_attr = "ANTHROPIC_MODEL"
