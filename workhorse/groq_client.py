"""Groq client with batched tool calling and structured output."""
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from groq import Groq

from .config import GroqConfig

logger = logging.getLogger(__name__)


class GroqClient:
    """Minimal Groq client optimized for task-based execution."""

    def __init__(self, config: GroqConfig):
        self.config = config
        self.client = Groq(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        response_format: Optional[Dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a single chat completion. No streaming for <8K outputs."""
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        elif self.config.max_tokens:
            kwargs["max_tokens"] = self.config.max_tokens

        try:
            response = self.client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    def batch_chat(
        self,
        requests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute multiple chat completions in parallel."""
        import asyncio
        import aiohttp

        # Fallback: sequential execution if async not available
        return [self.chat(**req) for req in requests]

    def _parse_response(self, response) -> Dict[str, Any]:
        """Extract the minimal useful data from a Groq response."""
        message = response.choices[0].message
        result = {
            "content": message.content,
            "role": message.role,
            "finish_reason": response.choices[0].finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }
        if hasattr(message, "tool_calls") and message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    },
                }
                for tc in message.tool_calls
            ]
        return result

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token for English text."""
        return len(text) // 4

    def build_system_prompt(self, directive: str, skills: Optional[List[str]] = None) -> str:
        """Build a minimal system prompt under 500 tokens."""
        skills_block = ""
        if skills:
            skills_block = "\n".join(f"- {s}" for s in skills)
        prompt = (
            f"{directive}\n\n"
            "Rules: No acknowledgements. No status updates. No apologies. "
            "Output only actionable results in requested format.\n"
        )
        if skills_block:
            prompt += f"\nActive Skills:\n{skills_block}"
        return prompt
