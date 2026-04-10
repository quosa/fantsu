"""Deterministic end-to-end playthrough test for the feed_animals task.

Two complementary approaches:
- test_task_completes_via_tools: calls tool functions directly (zero mocking)
- test_task_completes_via_process_input: drives the full narrator pipeline via
  ScriptedNarratorClient, which returns pre-defined tool calls in sequence.
"""

import pytest

from fantsu.narrator import build_context, process_input
from fantsu.state import GameState
from fantsu.tools import move_to, open_portal, take_item, use_item
from fantsu.world import build

# ------------------------------------------------------------------ #
# Playthrough script                                                   #
# ------------------------------------------------------------------ #

# Complete route from starting room to task completion:
#   farmhand_quarters
#     → (open door) main_hall → yard → storehouse
#     → (take bucket, fill) → yard → (open door) barn
#     → (feed animals)  ✓
_PLAYTHROUGH: list[tuple[str, dict[str, object]]] = [
    ("open_portal", {"location_id": "main_hall"}),
    ("move_to", {"location_id": "main_hall"}),
    ("move_to", {"location_id": "yard"}),
    ("move_to", {"location_id": "storehouse"}),
    ("take_item", {"item_id": "bucket"}),
    ("use_item", {"item_id": "bucket", "target_id": "feed_sack"}),
    ("move_to", {"location_id": "yard"}),
    ("open_portal", {"location_id": "barn"}),
    ("move_to", {"location_id": "barn"}),
    ("use_item", {"item_id": "bucket", "target_id": "animals"}),
]

# ------------------------------------------------------------------ #
# Scripted narrator client                                             #
# ------------------------------------------------------------------ #


class ScriptedNarratorClient:
    """Returns scripted tool calls one per chat() call — no LLM required."""

    def __init__(self, script: list[tuple[str, dict[str, object]]]) -> None:
        self._script = list(script)
        self._index = 0

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        if self._index >= len(self._script):
            return {"message": {"content": "", "tool_calls": []}}
        name, args = self._script[self._index]
        self._index += 1
        return {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": name, "arguments": args}}],
            }
        }

    @property
    def exhausted(self) -> bool:
        return self._index >= len(self._script)


class MockNPCClient:
    """Stub NPC client — process_input requires one even when no NPC is spoken to."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {"message": {"content": "Aye."}}


# ------------------------------------------------------------------ #
# Fixture                                                              #
# ------------------------------------------------------------------ #


@pytest.fixture()
def state() -> GameState:
    return build()


# ------------------------------------------------------------------ #
# Test 1: direct tool calls                                            #
# ------------------------------------------------------------------ #


def test_task_completes_via_tools(state: GameState) -> None:
    """Complete the task by calling tools directly — no narrator, no mocking."""

    # Leave the starting room
    assert open_portal("main_hall", state).ok
    assert move_to("main_hall", state).ok
    assert state.player_location_id == "main_hall"

    # Navigate to storehouse
    assert move_to("yard", state).ok
    assert move_to("storehouse", state).ok
    assert state.player_location_id == "storehouse"

    # Collect and fill the bucket
    assert take_item("bucket", state).ok
    assert "bucket" in state.player_inventory
    assert use_item("bucket", "feed_sack", state).ok
    assert state.items["bucket"].state["filled"] is True

    # Enter the barn and feed the animals
    assert move_to("yard", state).ok
    assert open_portal("barn", state).ok
    assert move_to("barn", state).ok
    assert state.player_location_id == "barn"

    result = use_item("bucket", "animals", state)
    assert result.ok
    assert state.tasks[0].completed is True


# ------------------------------------------------------------------ #
# Test 2: full narrator pipeline via scripted client                  #
# ------------------------------------------------------------------ #


def test_task_completes_via_process_input(state: GameState) -> None:
    """Full playthrough through process_input() — narrator pipeline, no LLM."""
    narrator = ScriptedNarratorClient(_PLAYTHROUGH)
    npc_client = MockNPCClient()

    for step, _ in enumerate(_PLAYTHROUGH):
        _, state = process_input(f"step {step}", state, narrator, npc_client)

    assert narrator.exhausted

    # Final state assertions
    assert state.tasks[0].completed is True
    assert state.player_location_id == "barn"
    assert "bucket" in state.player_inventory
    assert state.items["bucket"].state["filled"] is False  # emptied by feeding
    assert state.time == 16  # 2 + 5 + 2 + 5 + 2 minutes from move_to calls

    # build_context reflects the final state — locations and events are visible
    ctx = build_context(state)
    assert "Barn" in ctx
    assert "wooden bucket" in ctx
    assert "Player fed the animals" in ctx
