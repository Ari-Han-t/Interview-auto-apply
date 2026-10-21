import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI

from app.core.config import settings
from app.core.interfaces.llm import LLMProvider

logger = logging.getLogger(__name__)


def clean_and_parse_json(content: str) -> Union[Dict[str, Any], List[Any]]:
    """Clean markdown formatting and parse JSON payload safely."""
    if not content:
        raise ValueError("Empty response content from LLM")

    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def split_keys(raw: Optional[str]) -> List[str]:
    """Split a comma/whitespace separated key string into a clean list."""
    if not raw:
        return []
    parts = re.split(r"[,\s]+", raw.strip())
    return [p for p in parts if p]


def keys_from_settings(*names: str) -> List[str]:
    """Collect API keys from one or more Settings attribute names."""
    keys: List[str] = []
    for name in names:
        keys.extend(split_keys(getattr(settings, name, "") or ""))
    # de-dupe, preserve order
    seen = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


class OpenAICompatibleProvider(LLMProvider):
    """
    Base for any OpenAI-compatible chat completions API (OpenRouter, OpenAI,
    Groq, DeepSeek, Together, etc.). Supports multiple API keys with rotation
    on rate limits / auth failures.
    """

    provider_name: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    default_model: str = ""
    # Settings attribute names that hold API keys (checked in order)
    key_settings_attrs: tuple = ("OPENAI_API_KEY",)
    model_settings_attr: Optional[str] = "OPENAI_MODEL"
    # Extra body injected into every request (e.g. OpenRouter provider routing)
    extra_body: Optional[Dict[str, Any]] = None

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if api_key:
            self.api_keys = split_keys(api_key)
        else:
            self.api_keys = keys_from_settings(*self.key_settings_attrs)
        self._key_index = 0

        if model:
            self.model = model
        elif self.model_settings_attr:
            self.model = getattr(settings, self.model_settings_attr, "") or self.default_model
        else:
            self.model = self.default_model

        self.client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self) -> None:
        if self.api_keys:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_keys[self._key_index % len(self.api_keys)],
                timeout=120.0,
                max_retries=2,
            )
        else:
            self.client = None

    @property
    def has_key(self) -> bool:
        return bool(self.api_keys)

    def _rotate_key(self) -> bool:
        """Advance to the next configured API key. Returns False if only one key."""
        if len(self.api_keys) <= 1:
            return False
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        self._init_client()
        logger.info(
            "%s: rotated to API key #%d", self.provider_name, self._key_index + 1
        )
        return True

    def _is_rate_limit(self, err: Exception) -> bool:
        text = str(err).lower()
        status = getattr(err, "status_code", None)
        return status == 429 or "429" in text or "rate limit" in text or "rate_limit" in text

    def _is_transient(self, err: Exception) -> bool:
        """Connection resets, timeouts and upstream 5xx — worth retrying."""
        status = getattr(err, "status_code", None)
        if status in (408, 409, 500, 502, 503, 504, 529):
            return True
        text = str(err).lower()
        markers = (
            "connection", "timeout", "timed out", "temporarily",
            "unavailable", "overloaded", "econnreset", "econnrefused",
            "remote end closed", "ssl", "proxy",
        )
        return any(m in text for m in markers)

    def _is_auth_error(self, err: Exception) -> bool:
        status = getattr(err, "status_code", None)
        return status in (401, 403) or "invalid api key" in str(err).lower() or "unauthorized" in str(err).lower()

    def _should_rotate(self, err: Exception) -> bool:
        return self._is_rate_limit(err) or self._is_auth_error(err)

    def _merge_extra_body(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        if self.extra_body:
            extra = dict(kwargs.get("extra_body") or {})
            for k, v in self.extra_body.items():
                extra.setdefault(k, v)
            kwargs["extra_body"] = extra
        return kwargs

    def _chat(self, messages: List[Dict[str, str]], max_retries: int = 3, **kwargs):
        if not self.client:
            logger.error("%s: no API key configured.", self.provider_name)
            raise ValueError(
                f"{self.provider_name} API key is required. "
                f"Set one of: {', '.join(self.key_settings_attrs)}."
            )

        kwargs = self._merge_extra_body(kwargs)
        if "max_tokens" not in kwargs and "max_completion_tokens" not in kwargs:
            kwargs["max_tokens"] = 250
        attempts = max_retries * max(1, len(self.api_keys))
        last_err: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                return self.client.chat.completions.create(
                    model=self.model, messages=messages, **kwargs
                )
            except Exception as e:
                last_err = e
                # Check for OpenRouter / provider credit hint "can only afford X"
                afford_m = re.search(r"can only afford (\d+)", str(e))
                if afford_m:
                    afforded = int(afford_m.group(1))
                    adjusted = max(60, afforded - 20)
                    logger.warning(
                        "%s: credit limit hint received; adjusting max_tokens from %s to %d",
                        self.provider_name, kwargs.get("max_tokens"), adjusted
                    )
                    kwargs["max_tokens"] = adjusted
                    continue
                if self._should_rotate(e) and self._rotate_key():
                    continue
                if (self._is_rate_limit(e) or self._is_transient(e)) and attempt < attempts - 1:
                    time.sleep(min(5 * (attempt + 1), 15))
                    logger.warning(
                        "%s: transient error (%s); retrying attempt %d/%d",
                        self.provider_name, e, attempt + 2, attempts,
                    )
                    continue
                logger.error("Error calling %s: %s", self.provider_name, e)
                raise e
        raise last_err if last_err else RuntimeError(f"{self.provider_name} request failed")

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
            raise ValueError(f"{self.provider_name} returned empty content")
        return content.strip()

    def generate_json(
        self, system_prompt: str, user_prompt: str, max_retries: int = 3, **kwargs
    ) -> Dict[str, Any]:
        kwargs.pop("max_retries", None)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        attempts = max(1, max_retries)
        last_err: Optional[Exception] = None

        for attempt in range(attempts):
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
                        json_messages = [
                            {
                                "role": "system",
                                "content": system_prompt
                                + "\nIMPORTANT: Return ONLY a valid raw JSON object string without any markdown fences.",
                            },
                            {"role": "user", "content": user_prompt},
                        ]
                        response = self._chat(json_messages, max_retries=1, **kwargs)
                    else:
                        raise req_err
                return clean_and_parse_json(response.choices[0].message.content)
            except Exception as e:
                last_err = e
                if (self._is_rate_limit(e) or self._is_transient(e)) and attempt < attempts - 1:
                    time.sleep(5)
                    continue
                logger.error("Error calling %s JSON: %s", self.provider_name, e)
                if attempt == attempts - 1:
                    raise e
        raise last_err if last_err else RuntimeError(f"{self.provider_name} JSON request failed")
