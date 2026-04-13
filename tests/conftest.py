"""Shared test fixtures and helpers."""

from __future__ import annotations

import pytest

from fantsu.world import build as _build


@pytest.fixture()
def state():  # type: ignore[return]
    return _build()


class MockNPCClient:
    """Minimal NPC stub — returns a static reply without any network call."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {"message": {"content": "Aye."}}
