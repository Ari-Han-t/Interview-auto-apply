from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from app.core.config import settings
from app.core.interfaces.llm import LLMProvider
from app.services.llm.base import (
    clean_and_parse_json,
    keys_from_settings,
    split_keys,
)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI (AI Services) via the AzureOpenAI SDK client."""

    provider_name = "azure"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_keys = split_keys(api_key) if api_key else keys_from_settings("AZURE_OPENAI_API_KEY")
        self._key_index = 0
        self.endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", "")
        self.deployment = getattr(settings, "AZURE_OPENAI_DEPLOYMENT", "")
        self.api_version = getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.model = (
            model
            or getattr(settings, "AZURE_OPENAI_MODEL", "")
            or self.deployment
        )
        self.client: Optional[AzureOpenAI] = None
        self._init_client()

    def _init_client(self) -> None:
        if self.api_keys and self.endpoint and self.deployment:
            self.client = AzureOpenAI(
                api_key=self.api_keys[self._key_index % len(self.api_keys)],
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
                timeout=25.0,
            )
        else:
            self.client = None

    @property
    def has_key(self) -> bool:
        return bool(self.client)

    def _require_client(self) -> AzureOpenAI:
        if not self.client:
            missing = []
            if not self.api_keys:
                missing.append("AZURE_OPENAI_API_KEY")
            if not self.endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not self.deployment:
                missing.append("AZURE_OPENAI_DEPLOYMENT")
            raise ValueError(
                "Azure OpenAI is not configured. Missing: " + ", ".join(missing)
            )
        return self.client

    def _chat(self, messages: List[Dict[str, str]], max_retries: int = 3, **kwargs):
        client = self._require_client()
        kwargs.pop("max_retries", None)
        last_err: Optional[Exception] = None
        for attempt in range(max(1, max_retries)):
            try:
                return client.chat.completions.create(
                    model=self.model, messages=messages, **kwargs
                )
            except Exception as e:
                last_err = e
                status = getattr(e, "status_code", None)
                can_rotate = (status in (401, 403, 429) or "429" in str(e)) and len(self.api_keys) > 1
                if can_rotate:
                    self._key_index = (self._key_index + 1) % len(self.api_keys)
                    self._init_client()
                    client = self._require_client()
                    continue
                if status == 429 or "429" in str(e):
                    import time

                    time.sleep(min(5 * (attempt + 1), 15))
                    continue
                raise e
        raise last_err if last_err else RuntimeError("Azure OpenAI request failed")

    def generate_text(
        self, system_prompt: str, user_prompt: str, max_retries: int = 3, **kwargs
    ) -> str:
        kwargs.pop("max_retries", None)
        response = self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=max_retries,
            **kwargs,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Azure OpenAI returned empty content")
        return content.strip()

    def generate_json(
        self, system_prompt: str, user_prompt: str, max_retries: int = 3, **kwargs
    ) -> Dict[str, Any]:
        kwargs.pop("max_retries", None)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        for attempt in range(max(1, max_retries)):
            try:
                try:
                    response = self._chat(
                        messages,
                        max_retries=1,
                        response_format={"type": "json_object"},
                        **kwargs,
                    )
                except Exception as req_err:
                    if "response_format" in str(req_err) or "400" in str(req_err):
                        response = self._chat(
                            [
                                {
                                    "role": "system",
                                    "content": system_prompt
                                    + "\nIMPORTANT: Return ONLY a valid raw JSON object string without any markdown fences.",
                                },
                                {"role": "user", "content": user_prompt},
                            ],
                            max_retries=1,
                            **kwargs,
                        )
                    else:
                        raise req_err
                return clean_and_parse_json(response.choices[0].message.content)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                import time

                time.sleep(5)
        raise RuntimeError("Azure OpenAI JSON request failed")
