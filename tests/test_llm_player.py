"""Integration test: a GLM-4.7 player LLM drives the game with natural language.

The player LLM (GLM-4.7) generates natural language commands each turn,
observes the narration, and retries with different approaches if it fails.
The narrator LLM (GLM-4.7) interprets those commands into game tool calls.

Skipped automatically when Z_API_KEY is not set.

Run with:
    Z_API_KEY=... pytest tests/test_llm_player.py -v -s
"""

from __future__ import annotations

import re

import pytest

import fantsu.config as config
from fantsu.clients.z_client import ZAIClient
from fantsu.narrator import process_input
from fantsu.prompts import LLM_PLAYER_SYSTEM
from fantsu.state import GameState
from fantsu.world import build

from .conftest import MockNPCClient

pytestmark = pytest.mark.skipif(
    not config.Z_API_KEY,
    reason="Z_API_KEY not set — skipping LLM player test",
)

MAX_ATTEMPTS = 10


class LLMPlayerDriver:
    """Drives the game by asking a GLM model for natural language commands.

    Maintains a full conversation history so the model can reason about
    what has happened and adapt its approach when actions fail.
    """

    def __init__(self, client: ZAIClient, goal: str) -> None:
        self._client = client
        self._history: list[dict[str, str]] = [
            {"role": "system", "content": LLM_PLAYER_SYSTEM.format(goal=goal)},
        ]

    def next_command(self, narration: str) -> str:
        """Ask the player LLM what to do next, given the latest narration."""
        self._history.append({"role": "user", "content": narration})
        print("  [player thinking...]", flush=True)
        response = self._client.chat(model="", messages=self._history)
        message = response.get("message", {})
        if isinstance(message, dict):
            content = str(message.get("content", ""))
        else:
            content = str(message)
        self._history.append({"role": "assistant", "content": content})
        print(f"  [player raw] {content!r}", flush=True)

        m = re.search(r"^Action:\s*(.+)", content, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return content.strip()


def _boots_worn(state: GameState) -> bool:
    boots = state.items.get("player_boots")
    return bool(boots and boots.state.get("worn"))


def test_player_llm_wears_boots() -> None:
    """GLM-4.7 player LLM completes the task of wearing the boots in the quarters.

    The boots start on the floor of the farmhand quarters (the starting room).
    The player needs to pick them up and wear them — a two-step task that
    exercises natural language understanding and basic goal-directed planning.
    """
    state = build()
    narrator = ZAIClient()
    npc_stub = MockNPCClient()
    player = LLMPlayerDriver(
        ZAIClient(),
        goal="Pick up the boots from the floor and wear them.",
    )

    transcript: list[tuple[str, str]] = []

    narration, state = process_input("look around", state, narrator, npc_stub)
    print(f"\n[initial] {narration}")

    for attempt in range(MAX_ATTEMPTS):
        command = player.next_command(narration)
        print("  [narrator thinking...]", flush=True)
        narration, state = process_input(command, state, narrator, npc_stub)
        transcript.append((command, narration))
        print(f"[{attempt + 1}] > {command!r}\n    {narration}", flush=True)

        if _boots_worn(state):
            print(f"\nSuccess in {attempt + 1} attempt(s).")
            break

    if not _boots_worn(state):
        lines = [
            f"  [{i + 1}] > {cmd!r}\n      {narr}"
            for i, (cmd, narr) in enumerate(transcript)
        ]
        pytest.fail(
            f"Player LLM failed to wear boots in {MAX_ATTEMPTS} attempts:\n"
            + "\n".join(lines)
        )
