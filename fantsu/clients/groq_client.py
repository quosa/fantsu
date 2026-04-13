"""Groq LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

from httpx import Timeout
from openai import BadRequestError, OpenAI

import fantsu.config as config

from ._inline_tools import (
    extract_failed_generation,
    parse_inline_tool_calls,
    strip_inline_calls,
)

# Re-export so existing tests that import _parse_inline_tool_calls from this
# module directly continue to work without changes.
_parse_inline_tool_calls = parse_inline_tool_calls


class GroqClient:
    """Concrete LLMClient that calls Groq's cloud API."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
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
        try:
            response = self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        except BadRequestError as exc:
            # Groq returns 400 with a 'failed_generation' field when the model
            # emits inline function-call markup instead of proper tool_calls.
            # Recover by parsing the raw generation out of the error body.
            if tools:
                failed_gen = extract_failed_generation(exc)
                inline = parse_inline_tool_calls(failed_gen)
                if inline:
                    return {
                        "message": {
                            "content": strip_inline_calls(failed_gen),
                            "tool_calls": inline,
                        }
                    }
            raise

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
            # Fallback: model returned content with inline markup but no 400 error
            inline = parse_inline_tool_calls(content)
            if inline:
                result["tool_calls"] = inline
                result["content"] = strip_inline_calls(content)
        return {"message": result}
