from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate plain text from LLM"""
        pass

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON from LLM"""
        pass
