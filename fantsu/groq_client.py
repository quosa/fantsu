"""Groq LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

from openai import OpenAI

import fantsu.config as config


class GroqClient:
    """Concrete LLMClient that calls Groq's cloud API."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
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
        result: dict[str, object] = {"content": msg.content or ""}
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
        return {"message": result}
