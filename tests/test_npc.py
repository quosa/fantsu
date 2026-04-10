"""Tests for npc.py — LLM calls are replaced with a MockLLMClient."""

import pytest

from fantsu import config
from fantsu.npc import LLMClient, build_npc_system_prompt, get_response
from fantsu.state import GameState
from fantsu.world import build


class MockLLMClient:
    """Canned LLM responses for testing."""

    def __init__(self, content: str = "Aye, good morning to you.") -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        self.calls.append({"model": model, "messages": messages, "tools": tools})
        return {"message": {"content": self.content}}


def _assert_implements_protocol(client: LLMClient) -> None:
    """Static check that MockLLMClient satisfies LLMClient protocol."""
    pass


@pytest.fixture()
def state() -> GameState:
    return build()


# ------------------------------------------------------------------ #
# build_npc_system_prompt                                              #
# ------------------------------------------------------------------ #


def test_system_prompt_contains_npc_name(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state)
    assert "Master Aldric" in prompt


def test_system_prompt_contains_occupation(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state)
    assert "farmer" in prompt


def test_system_prompt_contains_location(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state)
    assert "Main Hall" in prompt


def test_system_prompt_contains_time(state: GameState) -> None:
    state.time = 0
    prompt = build_npc_system_prompt("aldric", state)
    assert "dawn" in prompt.lower()


def test_system_prompt_shows_memory(state: GameState) -> None:
    state.npcs["aldric"].memory = ["Player arrived at dawn."]
    prompt = build_npc_system_prompt("aldric", state)
    assert "Player arrived at dawn." in prompt


def test_system_prompt_memory_none_when_empty(state: GameState) -> None:
    state.npcs["aldric"].memory = []
    prompt = build_npc_system_prompt("aldric", state)
    assert "(none)" in prompt


def test_system_prompt_shows_nearby_npcs(state: GameState) -> None:
    # Put marta in main_hall alongside aldric
    state.npcs["marta"].location_id = "main_hall"
    state.locations["main_hall"].npc_ids.append("marta")
    prompt = build_npc_system_prompt("aldric", state)
    assert "Marta" in prompt


def test_system_prompt_nearby_nobody_when_alone(state: GameState) -> None:
    prompt = build_npc_system_prompt("marta", state)
    assert "nobody" in prompt


def test_system_prompt_memory_capped_at_five(state: GameState) -> None:
    state.npcs["aldric"].memory = [f"Event {i}" for i in range(10)]
    prompt = build_npc_system_prompt("aldric", state)
    # Only last 5 should appear
    assert "Event 9" in prompt
    assert "Event 0" not in prompt


# ------------------------------------------------------------------ #
# get_response                                                         #
# ------------------------------------------------------------------ #


def test_get_response_returns_content(state: GameState) -> None:
    client = MockLLMClient("The harvest is late this year.")
    result = get_response("aldric", "How are you?", state, client, config.NPC_MODEL)
    assert result == "The harvest is late this year."


def test_get_response_calls_llm_once(state: GameState) -> None:
    client = MockLLMClient()
    get_response("aldric", "Hello.", state, client, config.NPC_MODEL)
    assert len(client.calls) == 1


def test_get_response_passes_model(state: GameState) -> None:
    client = MockLLMClient()
    get_response("aldric", "Hello.", state, client, "custom-model")
    assert client.calls[0]["model"] == "custom-model"


def test_get_response_includes_player_message_in_messages(state: GameState) -> None:
    client = MockLLMClient()
    get_response(
        "aldric", "Tell me about the harvest.", state, client, config.NPC_MODEL
    )
    messages = client.calls[0]["messages"]
    assert isinstance(messages, list)
    user_messages = [m for m in messages if m.get("role") == "user"]
    assert any("harvest" in str(m.get("content", "")) for m in user_messages)


def test_get_response_system_message_present(state: GameState) -> None:
    client = MockLLMClient()
    get_response("marta", "Good day.", state, client, config.NPC_MODEL)
    messages = client.calls[0]["messages"]
    assert isinstance(messages, list)
    system_messages = [m for m in messages if m.get("role") == "system"]
    assert len(system_messages) == 1
    assert "Marta" in str(system_messages[0].get("content", ""))
