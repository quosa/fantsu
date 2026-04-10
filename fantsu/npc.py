"""NPC dialogue via LLM.

The public function `get_response` accepts an LLMClient so that tests can
inject a mock without any network calls.
"""

from __future__ import annotations

from typing import Protocol

from fantsu import prompts
from fantsu.renderer import format_time
from fantsu.state import GameState


class LLMClient(Protocol):
    """Minimal interface required for LLM calls."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]: ...


def _nearby_names(npc_id: str, state: GameState) -> str:
    """Return comma-separated names of other NPCs in the same location."""
    npc = state.npcs[npc_id]
    names = [
        state.npcs[n].name
        for n in state.locations[npc.location_id].npc_ids
        if n != npc_id and n in state.npcs
    ]
    return ", ".join(names) if names else "nobody"


def build_npc_system_prompt(npc_id: str, state: GameState) -> str:
    """Build the system prompt for an NPC dialogue call."""
    npc = state.npcs[npc_id]
    location = state.locations[npc.location_id]
    memory_text = (
        "\n".join(f"- {m}" for m in npc.memory[-5:]) if npc.memory else "(none)"
    )
    return prompts.NPC_SYSTEM_TEMPLATE.format(
        name=npc.name,
        occupation=npc.occupation,
        profile=npc.profile,
        time_label=format_time(state.time),
        location_name=location.name,
        nearby=_nearby_names(npc_id, state),
        memory=memory_text,
    )


def get_response(
    npc_id: str,
    player_message: str,
    state: GameState,
    client: LLMClient,
    model: str,
) -> str:
    """Call the LLM and return the NPC's dialogue string."""
    system = build_npc_system_prompt(npc_id, state)
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": player_message},
        ],
    )
    message = response.get("message", {})
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)
