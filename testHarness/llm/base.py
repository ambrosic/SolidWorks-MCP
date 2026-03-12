"""
Abstract LLM provider interface.

All LLM providers (Ollama, OpenAI, Claude API, etc.) implement this
interface so the eval runner is provider-agnostic.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for LLM providers used in eval."""

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.0,
    ) -> dict:
        """Send a chat completion request with tool definitions.

        Args:
            messages: Conversation history in OpenAI format
            tools: Tool definitions in OpenAI function-calling format
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Response dict in OpenAI-compatible format:
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "...",
                        "tool_calls": [{"id": "...", "type": "function",
                                        "function": {"name": "...", "arguments": "..."}}]
                    },
                    "finish_reason": "tool_calls" | "stop"
                }]
            }
        """
        pass

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""
        pass
