"""OpenRouter LLM client — implements LLMClient via the OpenAI-compatible API."""

from __future__ import annotations

from httpx import Timeout
from openai import OpenAI

import fantsu.config as config

from ._inline_tools import parse_inline_tool_calls, strip_inline_calls


class OpenRouterClient:
    """Concrete LLMClient that calls the OpenRouter cloud API."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
        )

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]

        msg = response.choices[0].message

        # Normalise to the Ollama-style dict the rest of the game expects:
        # {"message": {"content": "...", "tool_calls": [{"function": {...}}, ...]}}
        content = msg.content or ""
        result: dict[str, object] = {"content": content}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "function": {
                        "name": tc.function.name,
                        # JSON string; narrator handles both str and dict
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        elif tools and content:
            # Fallback: model returned content with inline markup but no tool_calls
            inline = parse_inline_tool_calls(content)
            if inline:
                result["tool_calls"] = inline
                result["content"] = strip_inline_calls(content)
        return {"message": result}
