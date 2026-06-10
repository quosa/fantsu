"""Tests for npc.py — LLM calls are replaced with a MockLLMClient."""

import pytest

from fantsu import config
from fantsu.npc import (
    LLMClient,
    build_npc_system_prompt,
    dialogue_turn,
    end_dialogue,
    is_farewell,
    relevant_facts,
    start_dialogue,
)
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


class FailingLLMClient:
    """Raises on every call — used to test the summary fallback."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        raise ConnectionError("backend down")


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


def test_system_prompt_contains_worldview(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state)
    assert "never travelled" in prompt


def test_system_prompt_contains_knowledge(state: GameState) -> None:
    prompt = build_npc_system_prompt("jakob", state)
    assert "haying" in prompt


def test_system_prompt_contains_preoccupation(state: GameState) -> None:
    prompt = build_npc_system_prompt("marta", state)
    assert "goose" in prompt


def test_system_prompt_default_preoccupation_when_blank(state: GameState) -> None:
    state.npcs["aldric"].preoccupation = ""
    prompt = build_npc_system_prompt("aldric", state)
    assert "the day's chores" in prompt


def test_system_prompt_injects_matching_fact(state: GameState) -> None:
    prompt = build_npc_system_prompt(
        "aldric", state, player_message="When is the next fair?"
    )
    assert "Greenhollow" in prompt


def test_system_prompt_omits_unrelated_facts(state: GameState) -> None:
    prompt = build_npc_system_prompt(
        "aldric", state, player_message="Nice boots you have."
    )
    assert "Greenhollow" not in prompt


def test_system_prompt_wrap_up_instruction(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state, wrap_up=True)
    assert "back to work" in prompt


def test_system_prompt_no_wrap_up_by_default(state: GameState) -> None:
    prompt = build_npc_system_prompt("aldric", state)
    assert "back to work" not in prompt


# ------------------------------------------------------------------ #
# relevant_facts                                                       #
# ------------------------------------------------------------------ #


def test_relevant_facts_matches_keyword(state: GameState) -> None:
    facts = relevant_facts("how goes the harvest?", state)
    assert any(f.topic == "harvest" for f in facts)


def test_relevant_facts_word_boundary(state: GameState) -> None:
    # "fairly" must not match the keyword "fair"
    facts = relevant_facts("that is fairly good work", state)
    assert facts == []


def test_relevant_facts_no_match(state: GameState) -> None:
    assert relevant_facts("hello there", state) == []


def test_relevant_facts_case_insensitive(state: GameState) -> None:
    facts = relevant_facts("Tell me about the FAIR", state)
    assert any(f.topic == "town fair" for f in facts)


# ------------------------------------------------------------------ #
# is_farewell                                                          #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    "message",
    ["Goodbye then", "farewell, Marta", "bye!", "I must go now", "never mind"],
)
def test_is_farewell_true(message: str) -> None:
    assert is_farewell(message) is True


@pytest.mark.parametrize(
    "message",
    ["maybe later", "how are you?", "tell me about the harvest"],
)
def test_is_farewell_false(message: str) -> None:
    assert is_farewell(message) is False


# ------------------------------------------------------------------ #
# start_dialogue / dialogue_turn                                       #
# ------------------------------------------------------------------ #


def test_start_dialogue_sets_state(state: GameState) -> None:
    start_dialogue("aldric", state)
    assert state.dialogue is not None
    assert state.dialogue.npc_id == "aldric"
    assert state.dialogue.transcript == []
    assert state.dialogue.turns == 0


def test_dialogue_turn_returns_reply(state: GameState) -> None:
    start_dialogue("aldric", state)
    client = MockLLMClient("The harvest is late this year.")
    reply = dialogue_turn("How are you?", state, client, config.NPC_MODEL)
    assert reply == "The harvest is late this year."


def test_dialogue_turn_requires_active_dialogue(state: GameState) -> None:
    with pytest.raises(RuntimeError):
        dialogue_turn("Hello", state, MockLLMClient(), config.NPC_MODEL)


def test_dialogue_turn_appends_transcript(state: GameState) -> None:
    start_dialogue("aldric", state)
    client = MockLLMClient("Aye.")
    dialogue_turn("Hello.", state, client, config.NPC_MODEL)
    assert state.dialogue is not None
    assert [line.speaker for line in state.dialogue.transcript] == ["player", "npc"]
    assert state.dialogue.transcript[0].text == "Hello."
    assert state.dialogue.transcript[1].text == "Aye."
    assert state.dialogue.turns == 1


def test_dialogue_turn_sends_history(state: GameState) -> None:
    start_dialogue("aldric", state)
    client = MockLLMClient("Aye.")
    dialogue_turn("First message.", state, client, config.NPC_MODEL)
    dialogue_turn("Second message.", state, client, config.NPC_MODEL)
    messages = client.calls[1]["messages"]
    assert isinstance(messages, list)
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "First message."
    assert messages[2]["content"] == "Aye."
    assert messages[3]["content"] == "Second message."


def test_dialogue_turn_passes_model(state: GameState) -> None:
    start_dialogue("aldric", state)
    client = MockLLMClient()
    dialogue_turn("Hello.", state, client, "custom-model")
    assert client.calls[0]["model"] == "custom-model"


def test_dialogue_turn_injects_fact_for_topic(state: GameState) -> None:
    start_dialogue("aldric", state)
    client = MockLLMClient()
    dialogue_turn("When is the fair?", state, client, config.NPC_MODEL)
    messages = client.calls[0]["messages"]
    assert isinstance(messages, list)
    assert "Greenhollow" in str(messages[0]["content"])


# ------------------------------------------------------------------ #
# end_dialogue                                                         #
# ------------------------------------------------------------------ #


def _run_short_conversation(state: GameState) -> None:
    start_dialogue("aldric", state)
    dialogue_turn(
        "Can I borrow the cart?", state, MockLLMClient("Aye."), config.NPC_MODEL
    )


def test_end_dialogue_clears_state(state: GameState) -> None:
    _run_short_conversation(state)
    end_dialogue(state, MockLLMClient("Summary."), config.NPC_MODEL)
    assert state.dialogue is None


def test_end_dialogue_appends_llm_summary_to_memory(state: GameState) -> None:
    _run_short_conversation(state)
    summariser = MockLLMClient("The new hand asked to borrow the cart.")
    end_dialogue(state, summariser, config.NPC_MODEL)
    assert "The new hand asked to borrow the cart." in state.npcs["aldric"].memory


def test_end_dialogue_summary_call_includes_transcript(state: GameState) -> None:
    _run_short_conversation(state)
    summariser = MockLLMClient("Summary.")
    end_dialogue(state, summariser, config.NPC_MODEL)
    messages = summariser.calls[0]["messages"]
    assert isinstance(messages, list)
    assert "borrow the cart" in str(messages[1]["content"])


def test_end_dialogue_appends_event_log(state: GameState) -> None:
    _run_short_conversation(state)
    end_dialogue(state, MockLLMClient("Summary."), config.NPC_MODEL)
    assert any("Summary." in e for e in state.event_log)


def test_end_dialogue_fallback_on_llm_failure(state: GameState) -> None:
    _run_short_conversation(state)
    end_dialogue(state, FailingLLMClient(), config.NPC_MODEL)
    assert state.dialogue is None
    assert any("borrow the cart" in m for m in state.npcs["aldric"].memory)


def test_end_dialogue_trims_memory(state: GameState) -> None:
    state.npcs["aldric"].memory = [f"Old {i}" for i in range(config.NPC_MEMORY_LENGTH)]
    _run_short_conversation(state)
    end_dialogue(state, MockLLMClient("Newest memory."), config.NPC_MODEL)
    memory = state.npcs["aldric"].memory
    assert len(memory) == config.NPC_MEMORY_LENGTH
    assert memory[-1] == "Newest memory."
    assert "Old 0" not in memory


def test_end_dialogue_empty_transcript_no_memory(state: GameState) -> None:
    start_dialogue("aldric", state)
    end_dialogue(state, MockLLMClient("Summary."), config.NPC_MODEL)
    assert state.npcs["aldric"].memory == []
    assert state.dialogue is None


def test_end_dialogue_without_active_dialogue_is_noop(state: GameState) -> None:
    end_dialogue(state, MockLLMClient(), config.NPC_MODEL)
    assert state.dialogue is None
