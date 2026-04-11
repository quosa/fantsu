"""Groq LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

import json
import re

from openai import BadRequestError, OpenAI

import fantsu.config as config

# Matches both inline formats LLaMA models emit instead of proper tool_calls:
#   <function=name>{"key": "value"}</function>   (separator ">")
#   <function=name={"key": "value"}</function>   (separator "=", no closing ">")
_INLINE_CALL_RE = re.compile(
    r"<function=(\w+)[=>](.*?)</function>", re.DOTALL
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
        try:
            response = self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        except BadRequestError as exc:
            # Groq returns 400 with a 'failed_generation' field when the model
            # emits inline function-call markup instead of proper tool_calls.
            # Recover by parsing the raw generation out of the error body.
            if tools:
                body = exc.body if isinstance(exc.body, dict) else {}
                error_info = body.get("error", {})
                failed_gen = (
                    error_info.get("failed_generation", "")
                    if isinstance(error_info, dict)
                    else ""
                )
                inline = _parse_inline_tool_calls(str(failed_gen))
                if inline:
                    clean = _INLINE_CALL_RE.sub("", str(failed_gen)).strip()
                    return {"message": {"content": clean, "tool_calls": inline}}
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
            inline = _parse_inline_tool_calls(content)
            if inline:
                result["tool_calls"] = inline
                result["content"] = _INLINE_CALL_RE.sub("", content).strip()
        return {"message": result}
