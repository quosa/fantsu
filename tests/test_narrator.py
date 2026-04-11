"""Tests for narrator.py — both LLM clients are mocked."""

import pytest

from fantsu.narrator import build_context, process_input
from fantsu.state import GameState
from fantsu.world import build

# ------------------------------------------------------------------ #
# Mock LLM clients                                                     #
# ------------------------------------------------------------------ #


class MockNarratorClient:
    """Returns a configurable Ollama-style response."""

    def __init__(
        self,
        content: str = "",
        tool_calls: list[dict[str, object]] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.calls: list[dict[str, object]] = []

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        self.calls.append({"model": model, "messages": messages, "tools": tools})
        return {
            "message": {
                "content": self.content,
                "tool_calls": self.tool_calls,
            }
        }


class MockNPCClient:
    """Always returns the same NPC dialogue."""

    def __init__(self, content: str = "Aye.") -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        self.calls.append({"model": model, "messages": messages})
        return {"message": {"content": self.content}}


def _tool_call(name: str, args: dict[str, object]) -> dict[str, object]:
    """Helper to build an Ollama-format tool call dict."""
    return {"function": {"name": name, "arguments": args}}


@pytest.fixture()
def state() -> GameState:
    return build()


@pytest.fixture()
def npc_client() -> MockNPCClient:
    return MockNPCClient()


# ------------------------------------------------------------------ #
# build_context                                                        #
# ------------------------------------------------------------------ #


def test_build_context_contains_location(state: GameState) -> None:
    ctx = build_context(state)
    assert "Farmhand" in ctx


def test_build_context_contains_time(state: GameState) -> None:
    ctx = build_context(state)
    assert "dawn" in ctx.lower()


def test_build_context_shows_inventory(state: GameState) -> None:
    state.player_inventory.append("bucket")
    ctx = build_context(state)
    assert "wooden bucket" in ctx


def test_build_context_empty_inventory(state: GameState) -> None:
    ctx = build_context(state)
    assert "nothing" in ctx


def test_build_context_shows_recent_events(state: GameState) -> None:
    state.event_log.append("Player took bucket.")
    ctx = build_context(state)
    assert "Player took bucket." in ctx


def test_build_context_includes_exit_destination_ids(state: GameState) -> None:
    # Player starts in farmhand_quarters; the exit to main_hall must appear
    # with its exact destination id so the model passes the right location_id
    # to open_portal / move_to.
    ctx = build_context(state)
    assert "id=main_hall" in ctx


def test_build_context_includes_portal_state(state: GameState) -> None:
    ctx = build_context(state)
    # The wooden door starts closed — that must be visible in the context
    assert "closed" in ctx


# ------------------------------------------------------------------ #
# process_input — no tool calls (plain narration)                      #
# ------------------------------------------------------------------ #


def test_process_input_returns_text_when_no_tool_calls(
    state: GameState, npc_client: MockNPCClient
) -> None:
    narrator = MockNarratorClient(content="The farmyard is quiet.")
    narration, _ = process_input("look around", state, narrator, npc_client)
    assert narration == "The farmyard is quiet."


def test_process_input_returns_nothing_happens_on_empty_response(
    state: GameState, npc_client: MockNPCClient
) -> None:
    narrator = MockNarratorClient(content="")
    narration, _ = process_input("do something odd", state, narrator, npc_client)
    assert narration == "Nothing happens."


def test_process_input_passes_player_input_to_llm(
    state: GameState, npc_client: MockNPCClient
) -> None:
    narrator = MockNarratorClient(content="OK.")
    process_input("go north", state, narrator, npc_client)
    user_msg = narrator.calls[0]["messages"][-1]
    assert "go north" in str(user_msg.get("content", ""))


# ------------------------------------------------------------------ #
# process_input — tool call: look                                      #
# ------------------------------------------------------------------ #


def test_process_input_look_tool_returns_location(
    state: GameState, npc_client: MockNPCClient
) -> None:
    narrator = MockNarratorClient(tool_calls=[_tool_call("look", {})])
    narration, _ = process_input("look", state, narrator, npc_client)
    assert "Farmhand" in narration


# ------------------------------------------------------------------ #
# process_input — tool call: move_to                                   #
# ------------------------------------------------------------------ #


def test_process_input_move_to_updates_state(
    state: GameState, npc_client: MockNPCClient
) -> None:
    state.player_location_id = "main_hall"
    narrator = MockNarratorClient(
        tool_calls=[_tool_call("move_to", {"location_id": "kitchen"})]
    )
    _, updated = process_input("go to kitchen", state, narrator, npc_client)
    assert updated.player_location_id == "kitchen"


def test_process_input_move_blocked_returns_error(
    state: GameState, npc_client: MockNPCClient
) -> None:
    # farmhand_quarters → main_hall is blocked by closed door
    narrator = MockNarratorClient(
        tool_calls=[_tool_call("move_to", {"location_id": "main_hall"})]
    )
    narration, updated = process_input("go to main hall", state, narrator, npc_client)
    assert updated.player_location_id == "farmhand_quarters"
    assert "closed" in narration


# ------------------------------------------------------------------ #
# process_input — tool call: take_item                                 #
# ------------------------------------------------------------------ #


def test_process_input_take_item_adds_to_inventory(
    state: GameState, npc_client: MockNPCClient
) -> None:
    state.player_location_id = "storehouse"
    narrator = MockNarratorClient(
        tool_calls=[_tool_call("take_item", {"item_id": "bucket"})]
    )
    _, updated = process_input("take the bucket", state, narrator, npc_client)
    assert "bucket" in updated.player_inventory


# ------------------------------------------------------------------ #
# process_input — tool call: open_portal                               #
# ------------------------------------------------------------------ #


def test_process_input_open_portal_then_move(
    state: GameState, npc_client: MockNPCClient
) -> None:
    narrator = MockNarratorClient(
        tool_calls=[
            _tool_call("open_portal", {"location_id": "main_hall"}),
            _tool_call("move_to", {"location_id": "main_hall"}),
        ]
    )
    _, updated = process_input(
        "open door and go to main hall", state, narrator, npc_client
    )
    assert updated.player_location_id == "main_hall"


# ------------------------------------------------------------------ #
# process_input — tool call: talk_to                                   #
# ------------------------------------------------------------------ #


def test_process_input_talk_to_present_npc(
    state: GameState,
) -> None:
    state.player_location_id = "main_hall"
    npc_client = MockNPCClient("The harvest worries me greatly.")
    narrator = MockNarratorClient(
        tool_calls=[_tool_call("talk_to", {"npc_id": "aldric", "message": "Hello"})]
    )
    narration, _ = process_input("talk to Aldric", state, narrator, npc_client)
    assert "harvest" in narration


def test_process_input_talk_to_absent_npc_returns_error(
    state: GameState, npc_client: MockNPCClient
) -> None:
    # Player is in farmhand_quarters, aldric is in main_hall
    narrator = MockNarratorClient(
        tool_calls=[_tool_call("talk_to", {"npc_id": "aldric", "message": "Hello"})]
    )
    narration, _ = process_input("talk to Aldric", state, narrator, npc_client)
    assert "not here" in narration


# ------------------------------------------------------------------ #
# process_input — tool call: use_item feeding sequence                 #
# ------------------------------------------------------------------ #


def test_process_input_full_feeding_sequence(
    state: GameState, npc_client: MockNPCClient
) -> None:
    # Set up: player in storehouse with bucket in hand
    state.player_location_id = "storehouse"
    state.player_inventory.append("bucket")

    # Step 1: fill bucket
    narrator_fill = MockNarratorClient(
        tool_calls=[
            _tool_call("use_item", {"item_id": "bucket", "target_id": "feed_sack"})
        ]
    )
    _, state = process_input("fill bucket", state, narrator_fill, npc_client)
    assert state.items["bucket"].state["filled"] is True

    # Step 2: move to barn (open door first)
    open_exit = state.locations["yard"].exits
    barn_exit = next(e for e in open_exit if e.destination == "barn")
    assert barn_exit.portal is not None
    barn_exit.portal.state = "open"
    state.player_location_id = "barn"

    # Step 3: feed animals
    narrator_feed = MockNarratorClient(
        tool_calls=[
            _tool_call("use_item", {"item_id": "bucket", "target_id": "animals"})
        ]
    )
    _, state = process_input("feed animals", state, narrator_feed, npc_client)
    task = next(t for t in state.tasks if t.id == "feed_animals")
    assert task.completed is True
