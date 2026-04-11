"""Groq LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

import json
import re

from httpx import Timeout
from openai import BadRequestError, OpenAI

import fantsu.config as config

# Matches inline formats LLaMA models emit instead of proper tool_calls.
# The separator between the function name and the JSON args varies by model
# version — ">", "=", or absent entirely — so it is made optional:
#   <function=name>{"key": "value"}</function>
#   <function=name={"key": "value"}</function>
#   <function=name{"key": "value"}</function>
_INLINE_CALL_RE = re.compile(
    r"<function=(\w+)[=>]?(.*?)</function>", re.DOTALL
)


def _extract_failed_generation(exc: BadRequestError) -> str:
    """Pull the failed_generation string from a Groq 400 error body.

    Groq wraps the error as {"error": {"failed_generation": ...}}.  Some
    openai SDK versions unwrap the "error" key so exc.body is the inner dict
    directly.  As a last resort, regex over the exception's string form.
    """
    body = exc.body if isinstance(exc.body, dict) else {}
    # Handle both {"error": {"failed_generation": ...}} and {"failed_generation": ...}
    error_info = body.get("error", body)
    if isinstance(error_info, dict):
        gen = error_info.get("failed_generation", "")
        if gen:
            return str(gen)
    # Fallback: parse the string representation of the exception
    m = re.search(r"'failed_generation':\s*'(.*?)'(?=[,}])", str(exc), re.DOTALL)
    return m.group(1) if m else ""


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
                inline = _parse_inline_tool_calls(_extract_failed_generation(exc))
                if inline:
                    failed_gen = _extract_failed_generation(exc)
                    clean = _INLINE_CALL_RE.sub("", failed_gen).strip()
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
