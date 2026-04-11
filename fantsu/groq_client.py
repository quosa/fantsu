"""Groq LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

import json
import re

from openai import OpenAI

import fantsu.config as config

# Matches the inline function-call format some LLaMA models emit instead of
# proper tool_calls: <function=name>{"key": "value"}</function>
_INLINE_CALL_RE = re.compile(
    r"<function=(\w+)>(.*?)</function>", re.DOTALL
)


def _parse_inline_tool_calls(content: str) -> list[dict[str, object]]:
    """Extract tool calls from inline <function=name>{...}</function> markup."""
    calls: list[dict[str, object]] = []
    for name, args_str in _INLINE_CALL_RE.findall(content):
        args_str = args_str.strip()
        try:
            args: object = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        calls.append({"function": {"name": name, "arguments": json.dumps(args)}})
    return calls


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
            # Some models emit inline <function=name>{...}</function> markup
            # instead of proper tool_calls — parse and normalise them.
            inline = _parse_inline_tool_calls(content)
            if inline:
                result["tool_calls"] = inline
                result["content"] = _INLINE_CALL_RE.sub("", content).strip()
        return {"message": result}
