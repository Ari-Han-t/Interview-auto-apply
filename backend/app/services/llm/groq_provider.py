import os
import json
import logging
import time
from typing import Dict, Any
from openai import OpenAI
from app.core.interfaces.llm import LLMProvider

logger = logging.getLogger(__name__)

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key,
            )

    def generate_text(self, system_prompt: str, user_prompt: str, max_retries: int = 3, **kwargs) -> str:
        if not self.client:
            logger.warning("GROQ_API_KEY not set. Returning mock text.")
            return "Mock generated text because API key is missing."

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    **kwargs
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                logger.error(f"Error calling Groq: {e}")
                raise e

    def generate_json(self, system_prompt: str, user_prompt: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        if not self.client:
            logger.warning("GROQ_API_KEY not set. Returning mock JSON.")
            return {"mock": "data"}

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    **kwargs
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                logger.error(f"Error calling Groq JSON: {e}")
                raise e
