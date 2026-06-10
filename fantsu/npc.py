"""NPC dialogue system: conversation mode, memories, world-fact retrieval.

All public functions accept an LLMClient so that tests can inject a mock
without any network calls.

A conversation is opened with `start_dialogue`, advanced one exchange at a
time with `dialogue_turn`, and closed with `end_dialogue`, which condenses
the transcript into a single memory line via one extra LLM call.
"""

from __future__ import annotations

import re
from typing import Protocol

from fantsu import config, prompts
from fantsu.renderer import format_time
from fantsu.state import DialogueLine, DialogueState, GameState, WorldFact


class LLMClient(Protocol):
    """Minimal interface required for LLM calls."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]: ...


def _message_content(response: dict[str, object]) -> str:
    """Extract the text content from an Ollama-style chat response."""
    message = response.get("message", {})
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def _nearby_names(npc_id: str, state: GameState) -> str:
    """Return comma-separated names of other NPCs in the same location."""
    npc = state.npcs[npc_id]
    names = [
        state.npcs[n].name
        for n in state.locations[npc.location_id].npc_ids
        if n != npc_id and n in state.npcs
    ]
    return ", ".join(names) if names else "nobody"


# ------------------------------------------------------------------ #
# World-fact retrieval                                                 #
# ------------------------------------------------------------------ #


def relevant_facts(message: str, state: GameState) -> list[WorldFact]:
    """Return world facts whose keywords appear in the player's message."""
    text = message.lower()
    matched: list[WorldFact] = []
    for fact in state.world_facts:
        for keyword in fact.keywords:
            if re.search(rf"\b{re.escape(keyword.lower())}\b", text):
                matched.append(fact)
                break
    return matched


def is_farewell(message: str) -> bool:
    """True if the player's message contains a farewell phrase."""
    text = message.lower()
    return any(
        re.search(rf"\b{re.escape(phrase)}\b", text)
        for phrase in config.FAREWELL_PHRASES
    )


# ------------------------------------------------------------------ #
# Prompt building                                                      #
# ------------------------------------------------------------------ #


def build_npc_system_prompt(
    npc_id: str,
    state: GameState,
    player_message: str = "",
    wrap_up: bool = False,
) -> str:
    """Build the system prompt for an NPC dialogue call.

    Facts matching `player_message` are injected for this turn only;
    `wrap_up` appends the instruction to end the conversation politely.
    """
    npc = state.npcs[npc_id]
    location = state.locations[npc.location_id]
    memory_text = (
        "\n".join(f"- {m}" for m in npc.memory[-5:]) if npc.memory else "(none)"
    )
    knowledge_text = (
        "\n".join(f"- {k}" for k in npc.knowledge) if npc.knowledge else "(none)"
    )
    prompt = prompts.NPC_SYSTEM_TEMPLATE.format(
        name=npc.name,
        occupation=npc.occupation,
        profile=npc.profile,
        worldview=prompts.FARM_FOLK_WORLDVIEW,
        knowledge=knowledge_text,
        preoccupation=npc.preoccupation or "the day's chores",
        time_label=format_time(state.time),
        location_name=location.name,
        nearby=_nearby_names(npc_id, state),
        memory=memory_text,
    )
    facts = relevant_facts(player_message, state) if player_message else []
    if facts:
        facts_text = "\n".join(f"- {f.text}" for f in facts)
        prompt += prompts.NPC_FACTS_TEMPLATE.format(facts=facts_text)
    if wrap_up:
        prompt += prompts.DIALOGUE_WRAP_UP
    return prompt


# ------------------------------------------------------------------ #
# Conversation lifecycle                                               #
# ------------------------------------------------------------------ #


def start_dialogue(npc_id: str, state: GameState) -> None:
    """Open a conversation with the given NPC."""
    state.dialogue = DialogueState(npc_id=npc_id)


def dialogue_turn(
    player_message: str,
    state: GameState,
    client: LLMClient,
    model: str,
    wrap_up: bool = False,
) -> str:
    """Run one exchange of the active conversation and return the NPC reply."""
    dialogue = state.dialogue
    if dialogue is None:
        raise RuntimeError("dialogue_turn called with no active dialogue")
    npc_id = dialogue.npc_id

    system = build_npc_system_prompt(
        npc_id, state, player_message=player_message, wrap_up=wrap_up
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for line in dialogue.transcript:
        role = "user" if line.speaker == "player" else "assistant"
        messages.append({"role": role, "content": line.text})
    messages.append({"role": "user", "content": player_message})

    response = client.chat(model=model, messages=messages)
    reply = _message_content(response).strip()

    dialogue.transcript.append(DialogueLine(speaker="player", text=player_message))
    dialogue.transcript.append(DialogueLine(speaker="npc", text=reply))
    dialogue.turns += 1
    return reply


def _fallback_summary(dialogue: DialogueState) -> str:
    """Rule-based memory line used when the summary LLM call fails."""
    first_player_line = next(
        (line.text for line in dialogue.transcript if line.speaker == "player"),
        "",
    )
    return f'The player spoke with me: "{first_player_line[:60]}"'


def end_dialogue(state: GameState, client: LLMClient, model: str) -> None:
    """Close the active conversation, summarising it into NPC memory."""
    dialogue = state.dialogue
    if dialogue is None:
        return
    npc = state.npcs[dialogue.npc_id]
    if dialogue.transcript:
        transcript_text = "\n".join(
            f"{'Player' if line.speaker == 'player' else npc.name}: {line.text}"
            for line in dialogue.transcript
        )
        try:
            response = client.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": prompts.DIALOGUE_SUMMARY_SYSTEM.format(
                            name=npc.name
                        ),
                    },
                    {"role": "user", "content": transcript_text},
                ],
            )
            summary = _message_content(response).strip()
        except Exception:  # noqa: BLE001 — never crash on conversation end
            summary = ""
        if not summary:
            summary = _fallback_summary(dialogue)
        npc.memory.append(summary)
        if len(npc.memory) > config.NPC_MEMORY_LENGTH:
            npc.memory = npc.memory[-config.NPC_MEMORY_LENGTH :]
        state.event_log.append(f"{npc.name} remembers: {summary[:80]}")
    state.dialogue = None
