"""
OpenAI-compatible LLM provider.

Works with Ollama, OpenAI, OpenRouter, LM Studio, and any endpoint
that speaks the OpenAI chat completions protocol with tool calling.

Uses raw `requests` instead of the `openai` package to minimize
dependencies and avoid version churn.
"""

import requests
import logging
from testHarness.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    """Provider for any OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",  # Ollama default
        api_key: str = "ollama",                       # Ollama ignores this
        model: str = "qwen2.5:14b",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.0,
    ) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        logger.debug(f"POST {url} model={self.model} msgs={len(messages)} tools={len(tools)}")

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def model_name(self) -> str:
        return self.model
