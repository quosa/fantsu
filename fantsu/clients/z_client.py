"""Z.ai LLM client — implements the LLMClient protocol via the OpenAI-compatible API."""

from __future__ import annotations

import time

from httpx import Timeout
from openai import BadRequestError, OpenAI, RateLimitError

import fantsu.config as config

from ._inline_tools import (
    extract_failed_generation,
    parse_inline_tool_calls,
    strip_inline_calls,
)

_MODEL = "glm-4.7"
_RETRY_DELAYS = [5, 15, 30]  # seconds between retries on 429


class ZAIClient:
    """Concrete LLMClient that calls the Z.ai cloud API.

    Always uses glm-4.7 regardless of the model argument passed by callers,
    since the other backends use different model name schemes.
    """

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=config.Z_API_KEY,
            base_url="https://api.z.ai/api/coding/paas/v4/",
            timeout=Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        )

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        _ = model  # ignored — ZAIClient always uses _MODEL
        kwargs: dict[str, object] = {
            "model": _MODEL,
            "messages": messages,
            "max_tokens": 512,
        }
        if tools:
            kwargs["tools"] = tools

        last_exc: RateLimitError | None = None
        for attempt, delay in enumerate([0] + _RETRY_DELAYS):
            if delay:
                print(f"  [z.ai] rate-limited, retrying in {delay}s "
                      f"(attempt {attempt + 1}/{len(_RETRY_DELAYS) + 1})...")
                time.sleep(delay)
            try:
                return self._call(kwargs, tools=tools)
            except RateLimitError as exc:
                last_exc = exc
        raise last_exc  # type: ignore[misc]

    def _call(
        self,
        kwargs: dict[str, object],
        tools: list[dict[str, object]] | None,
    ) -> dict[str, object]:
        try:
            response = self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        except BadRequestError as exc:
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
        content = msg.content or ""
        result: dict[str, object] = {"content": content}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        elif tools and content:
            inline = parse_inline_tool_calls(content)
            if inline:
                result["tool_calls"] = inline
                result["content"] = strip_inline_calls(content)
        return {"message": result}
