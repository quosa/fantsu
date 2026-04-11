"""Integration tests for GroqClient — skipped unless GROQ_API_KEY is set.

Run with a live key:
    GROQ_API_KEY=gsk_... pytest tests/test_groq_integration.py -v
"""

from __future__ import annotations

import json

import pytest

import fantsu.config as config
from fantsu import tool_schema
from fantsu.world import build

pytestmark = pytest.mark.skipif(
    not config.GROQ_API_KEY,
    reason="GROQ_API_KEY not set",
)


@pytest.fixture()
def client():  # type: ignore[return]
    from fantsu.groq_client import GroqClient

    return GroqClient()


@pytest.fixture()
def state():
    return build()


# ------------------------------------------------------------------ #
# Basic connectivity                                                   #
# ------------------------------------------------------------------ #


def test_basic_chat_returns_text(client) -> None:  # type: ignore[no-untyped-def]
    """GroqClient returns a non-empty text response for a plain message."""
    response = client.chat(
        model=config.NPC_MODEL,
        messages=[{"role": "user", "content": "Say hello."}],
    )
    message = response.get("message", {})
    assert isinstance(message, dict)
    content = message.get("content", "")
    assert isinstance(content, str)
    assert len(content) > 0


# ------------------------------------------------------------------ #
# Tool-call structure                                                  #
# ------------------------------------------------------------------ #


def test_tool_call_response_is_structured(client) -> None:  # type: ignore[no-untyped-def]
    """Tool calls arrive as proper tool_calls dicts, not inline markup.

    This is the core invariant the groq_client recovery logic enforces:
    whether the model uses native tool_calls or emits inline
    <function=…> markup, the caller always receives normalised dicts
    with string 'name' and JSON-string 'arguments'.
    """
    response = client.chat(
        model=config.NARRATOR_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a game narrator. Call move_to when the player moves."
                ),
            },
            {"role": "user", "content": "Move to the kitchen."},
        ],
        tools=tool_schema.ALL_TOOLS,
    )
    message = response.get("message", {})
    assert isinstance(message, dict)

    tool_calls = message.get("tool_calls", [])
    assert len(tool_calls) > 0, (
        "Expected at least one tool call — got plain text instead.\n"
        f"content: {message.get('content', '')!r}"
    )

    for tc in tool_calls:
        func = tc.get("function", {})
        assert isinstance(func.get("name"), str), "tool call name must be a str"
        args_raw = func.get("arguments")
        assert isinstance(args_raw, str), "arguments must be a JSON string"
        # Must be valid JSON
        args = json.loads(args_raw)
        assert isinstance(args, dict), "arguments JSON must decode to a dict"


# ------------------------------------------------------------------ #
# End-to-end: the scenario that was returning a 400 error             #
# ------------------------------------------------------------------ #


def test_open_door_and_go_to_main_hall_does_not_raise(client, state) -> None:  # type: ignore[no-untyped-def]
    """Opening the door then moving must not raise a Groq 400 error.

    Regression test for: Failed to call a function …
    'failed_generation': '<function=move_to={"location_id": …}</function>'
    """
    from fantsu.narrator import process_input

    narration, updated = process_input(
        "open the door and go to the main hall",
        state,
        client,
        client,
    )
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_sequential_commands_do_not_raise(client, state) -> None:  # type: ignore[no-untyped-def]
    """Each command in a short play session must return a non-empty narration."""
    from fantsu.narrator import process_input

    commands = [
        "look around",
        "open the door",
        "go to the main hall",
    ]
    for cmd in commands:
        narration, state = process_input(cmd, state, client, client)
        assert isinstance(narration, str) and len(narration) > 0, (
            f"Empty narration for command {cmd!r}"
        )
