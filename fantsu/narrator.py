"""Narrator LLM loop: interprets player input, calls tools, returns narration.

The public function `process_input` accepts an LLMClient and an NPCLLMClient
so that tests can inject mocks without any network calls.
"""

from __future__ import annotations

import json

from fantsu import config, prompts, tool_schema
from fantsu.npc import LLMClient, get_response
from fantsu.renderer import format_time
from fantsu.state import GameState
from fantsu.tools import (
    ToolResult,
    drop_item,
    get_time,
    look,
    move_to,
    open_portal,
    record_talk,
    take_item,
    use_item,
    validate_talk_to,
)


def _build_context(state: GameState) -> str:
    """Summarise the current game state for the narrator prompt."""
    loc = state.locations.get(state.player_location_id)
    loc_name = loc.name if loc else state.player_location_id

    inventory_names = [
        state.items[i].name
        for i in state.player_inventory
        if i in state.items
    ]
    inventory_text = ", ".join(inventory_names) if inventory_names else "nothing"

    recent_events = state.event_log[-5:] if state.event_log else []
    events_text = (
        "\n".join(f"- {e}" for e in recent_events) if recent_events else "(none)"
    )

    # Include exit destination IDs explicitly so the model passes the correct
    # location_id to open_portal / move_to rather than guessing from the label.
    exit_parts: list[str] = []
    if loc:
        for ex in loc.exits:
            portal_info = (
                f" [{ex.portal.description}, {ex.portal.state}]"
                if ex.portal
                else ""
            )
            exit_parts.append(f"{ex.label} (id={ex.destination}){portal_info}")
    exits_text = "; ".join(exit_parts) if exit_parts else "none"

    return (
        f"Time: {format_time(state.time)}\n"
        f"Location: {loc_name}\n"
        f"Exits: {exits_text}\n"
        f"Carrying: {inventory_text}\n"
        f"Recent events:\n{events_text}"
    )


def _dispatch_tool_call(
    name: str,
    args: dict[str, object],
    state: GameState,
    npc_client: LLMClient,
) -> ToolResult:
    """Execute one tool call and return the result."""
    if name == "move_to":
        return move_to(str(args["location_id"]), state)
    if name == "open_portal":
        return open_portal(str(args["location_id"]), state)
    if name == "take_item":
        return take_item(str(args["item_id"]), state)
    if name == "drop_item":
        return drop_item(str(args["item_id"]), state)
    if name == "use_item":
        return use_item(str(args["item_id"]), str(args["target_id"]), state)
    if name == "talk_to":
        npc_id = str(args["npc_id"])
        message = str(args["message"])
        error = validate_talk_to(npc_id, state)
        if error is not None:
            return error
        dialogue = get_response(
            npc_id, message, state, npc_client, config.NPC_MODEL
        )
        record_talk(npc_id, dialogue, state)
        return ToolResult(ok=True, message=dialogue)
    if name == "look":
        return look(state)
    if name == "get_time":
        return get_time(state)
    return ToolResult(ok=False, message=f"Unknown tool: {name}")


def _extract_tool_calls(
    response: dict[str, object],
) -> list[tuple[str, dict[str, object]]]:
    """Extract (name, args) pairs from an Ollama chat response."""
    message = response.get("message", {})
    if not isinstance(message, dict):
        return []
    raw_calls = message.get("tool_calls", [])
    if not isinstance(raw_calls, list):
        return []

    result: list[tuple[str, dict[str, object]]] = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        func = call.get("function", {})
        if not isinstance(func, dict):
            continue
        name = func.get("name", "")
        raw_args = func.get("arguments", {})
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            args = {}
        result.append((str(name), args))
    return result


def _extract_text(response: dict[str, object]) -> str:
    """Extract the text content from an Ollama chat response."""
    message = response.get("message", {})
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def process_input(
    player_input: str,
    state: GameState,
    narrator_client: LLMClient,
    npc_client: LLMClient,
) -> tuple[str, GameState]:
    """Interpret player input, execute tools, return narration and updated state."""
    context = _build_context(state)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": prompts.NARRATOR_SYSTEM},
        {"role": "user", "content": f"{context}\n\nPlayer: {player_input}"},
    ]

    response = narrator_client.chat(
        model=config.NARRATOR_MODEL,
        messages=messages,
        tools=tool_schema.ALL_TOOLS,
    )

    tool_calls = _extract_tool_calls(response)
    tool_results: list[str] = []

    for name, args in tool_calls:
        result = _dispatch_tool_call(name, args, state, npc_client)
        tool_results.append(result.message)

    # If the narrator returned tool calls, use their results as narration;
    # otherwise fall back to the raw text content.
    if tool_results:
        narration = "\n\n".join(tool_results)
    else:
        narration = _extract_text(response)
        if not narration:
            narration = "Nothing happens."

    return narration, state


def build_context(state: GameState) -> str:
    """Public alias used in tests."""
    return _build_context(state)
