"""Shared helpers for parsing inline tool-call markup emitted by some LLMs.

Some models (LLaMA via Groq, GLM via Z.ai) occasionally emit tool calls as
inline text instead of structured tool_calls, for example:

    <function=move_to>{"location_id": "kitchen"}</function>
    <function=move_to={"location_id": "kitchen"}</function>
    <function=move_to{"location_id": "kitchen"}</function>

The separator between the function name and the JSON args varies by model
version — ">", "=", or absent — so it is made optional in the regex.
"""

from __future__ import annotations

import json
import re

from openai import BadRequestError

_INLINE_CALL_RE = re.compile(
    r"<function=(\w+)[=>]?(.*?)</function>", re.DOTALL
)


def parse_inline_tool_calls(content: str) -> list[dict[str, object]]:
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


def strip_inline_calls(content: str) -> str:
    """Remove all inline tool-call markup from a string."""
    return _INLINE_CALL_RE.sub("", content).strip()


def extract_failed_generation(exc: BadRequestError) -> str:
    """Pull the failed_generation string from a 400 error body.

    The API wraps the error as {"error": {"failed_generation": ...}}.
    Some openai SDK versions unwrap the "error" key so exc.body is the
    inner dict directly. As a last resort, regex over the exception string.
    """
    body = exc.body if isinstance(exc.body, dict) else {}
    error_info = body.get("error", body)
    if isinstance(error_info, dict):
        gen = error_info.get("failed_generation", "")
        if gen:
            return str(gen)
    m = re.search(r"'failed_generation':\s*'(.*?)'(?=[,}])", str(exc), re.DOTALL)
    return m.group(1) if m else ""
