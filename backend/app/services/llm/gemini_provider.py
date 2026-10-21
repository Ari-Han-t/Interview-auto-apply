import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.interfaces.llm import LLMProvider

logger = logging.getLogger(__name__)


class GeminiContentBlockedError(ValueError):
    pass


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "GOOGLE_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
        # Lazy: avoid circular import with registry at module load time
        self._fallback = None

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    @property
    def fallback(self) -> LLMProvider:
        if self._fallback is None:
            from app.services.llm.registry import get_llm

            # Any configured provider other than Gemini itself
            self._fallback = get_llm(exclude=("gemini",))
        return self._fallback

    def _generate(self, system_prompt: str, user_prompt: str, json_mode: bool, **kwargs):
        options = dict(kwargs)
        options.pop("max_retries", None)

        if self.api_key:
            config = {"maxOutputTokens": options.get("max_tokens", 16384)}
            if "temperature" in options:
                config["temperature"] = options["temperature"]
            if "top_p" in options:
                config["topP"] = options["top_p"]
            if json_mode:
                config["responseMimeType"] = "application/json"
            try:
                response = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": config,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("promptFeedback", {}).get("blockReason"):
                    raise GeminiContentBlockedError("Gemini declined this content.")
                candidates = payload.get("candidates") or []
                if not candidates:
                    raise ValueError("Gemini returned no candidates")
                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")
                if finish_reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY"}:
                    raise GeminiContentBlockedError("Gemini declined this content.")
                if finish_reason != "STOP":
                    raise ValueError("Gemini response did not finish")
                text = "".join(
                    part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                    if not part.get("thought")
                ).strip()
                if not text:
                    raise ValueError("Gemini returned empty content")
                if not json_mode:
                    return text
                result = json.loads(text)
                if not isinstance(result, dict):
                    raise ValueError("Expected a JSON object")
                return result
            except GeminiContentBlockedError:
                raise
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
                logger.warning("Gemini request failed (%s); trying fallback providers", e)
        else:
            logger.warning("Gemini API key is not configured; trying fallback providers")

        method = getattr(self.fallback, "generate_json" if json_mode else "generate_text")
        try:
            result = method(system_prompt, user_prompt, **options)
            if json_mode and not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            if not json_mode and (not isinstance(result, str) or not result.strip()):
                raise ValueError("Expected nonempty text")
            return result
        except GeminiContentBlockedError:
            raise
        except Exception:
            raise RuntimeError(
                "Resume AI is unavailable. Check Gemini and fallback API configuration, then try again."
            ) from None

    def generate_text(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return self._generate(system_prompt, user_prompt, False, **kwargs)

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict[str, Any]:
        return self._generate(system_prompt, user_prompt, True, **kwargs)
