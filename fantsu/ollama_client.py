"""Production LLM client backed by a local Ollama instance.

This is the only module that imports the `ollama` library.  Everything else
in the package depends only on the LLMClient protocol defined in npc.py.
"""

from __future__ import annotations

import ollama as ollama_lib


class OllamaClient:
    """Concrete LLMClient that calls the local Ollama daemon."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        kwargs = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools  # type: ignore[assignment]
        response = ollama_lib.chat(**kwargs)
        # ollama returns a ChatResponse object; normalise to a plain dict
        if hasattr(response, "model_dump"):
            raw: dict[str, object] = response.model_dump()
        else:
            raw = dict(response)
        return raw
