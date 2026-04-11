"""Tests for the Groq client.

Unit tests (no API key needed) cover the inline-call recovery logic.
Integration tests are skipped automatically unless GROQ_API_KEY is set.

Run integration tests with a live key:
    GROQ_API_KEY=gsk_... pytest tests/test_groq_integration.py -v
"""

from __future__ import annotations

import json

import pytest

# groq_client.py does `from openai import ...` at import time, so the entire
# module is unavailable when the openai package is not installed.  Skip the
# whole file in that case rather than producing a hard ImportError.
pytest.importorskip("openai", reason="openai package not installed")

import fantsu.config as config
from fantsu import tool_schema
from fantsu.world import build

# Applied individually to integration tests so the unit tests run whenever
# openai is installed, regardless of whether GROQ_API_KEY is present.
requires_groq = pytest.mark.skipif(
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
# Unit tests: inline tool-call parsing (no network, always run)       #
# ------------------------------------------------------------------ #


def test_parse_inline_calls_greater_than_separator() -> None:
    """Parses <function=name>{"k": "v"}</function> format."""
    from fantsu.groq_client import _parse_inline_tool_calls

    calls = _parse_inline_tool_calls(
        'some text <function=move_to>{"location_id": "kitchen"}</function> more text'
    )
    assert len(calls) == 1
    func = calls[0]["function"]
    assert isinstance(func, dict)
    assert func["name"] == "move_to"
    assert json.loads(str(func["arguments"])) == {"location_id": "kitchen"}


def test_parse_inline_calls_equals_separator() -> None:
    """Parses <function=name={"k": "v"}</function> format (the variant Groq reports
    in failed_generation, using '=' instead of '>' after the function name)."""
    from fantsu.groq_client import _parse_inline_tool_calls

    calls = _parse_inline_tool_calls(
        '<function=move_to={"location_id": "main_hall"}</function>'
    )
    assert len(calls) == 1
    func = calls[0]["function"]
    assert isinstance(func, dict)
    assert func["name"] == "move_to"
    assert json.loads(str(func["arguments"])) == {"location_id": "main_hall"}


def test_parse_inline_calls_multiple() -> None:
    """Multiple inline calls are all extracted."""
    from fantsu.groq_client import _parse_inline_tool_calls

    text = (
        '<function=open_portal>{"location_id": "main_hall"}</function>'
        '<function=move_to>{"location_id": "main_hall"}</function>'
    )
    calls = _parse_inline_tool_calls(text)
    assert len(calls) == 2
    names = [str(c["function"]["name"]) for c in calls]  # type: ignore[index]
    assert names == ["open_portal", "move_to"]


def test_parse_inline_calls_invalid_json_returns_empty_args() -> None:
    """Unparseable JSON falls back to an empty args dict rather than crashing."""
    from fantsu.groq_client import _parse_inline_tool_calls

    calls = _parse_inline_tool_calls("<function=look>not valid json</function>")
    assert len(calls) == 1
    assert json.loads(str(calls[0]["function"]["arguments"])) == {}  # type: ignore[index]


def test_parse_inline_calls_empty_string() -> None:
    from fantsu.groq_client import _parse_inline_tool_calls

    assert _parse_inline_tool_calls("") == []


def test_bad_request_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """GroqClient recovers from a 400 BadRequestError containing failed_generation."""
    from openai import BadRequestError

    from fantsu.groq_client import GroqClient

    fake_error = BadRequestError(
        message="Failed to call a function.",
        response=None,  # type: ignore[arg-type]
        body={
            "error": {
                "message": "Failed to call a function.",
                "code": "tool_use_failed",
                "failed_generation": (
                    '<function=move_to={"location_id": "main_hall"}</function>'
                ),
            }
        },
    )

    client = object.__new__(GroqClient)  # skip __init__ / no real API key needed

    class _FakeInner:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs: object) -> object:
                    raise fake_error

    client._client = _FakeInner()  # type: ignore[attr-defined]

    response = client.chat(
        model="any",
        messages=[{"role": "user", "content": "go"}],
        tools=tool_schema.ALL_TOOLS,
    )
    message = response.get("message", {})
    assert isinstance(message, dict)
    tool_calls = message.get("tool_calls", [])
    assert len(tool_calls) == 1
    func = tool_calls[0]["function"]
    assert isinstance(func, dict)
    assert func["name"] == "move_to"
    assert json.loads(str(func["arguments"])) == {"location_id": "main_hall"}


# ------------------------------------------------------------------ #
# Integration tests: live Groq API (skipped without GROQ_API_KEY)     #
# ------------------------------------------------------------------ #


@requires_groq
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


@requires_groq
def test_tool_call_structure_when_returned(client) -> None:  # type: ignore[no-untyped-def]
    """When the model returns tool calls they must be properly structured dicts.

    Note: we do not assert that the model *must* call a tool — LLMs are
    non-deterministic and may choose to respond with plain text.  The unit
    test test_bad_request_recovery covers the recovery path without a live key.
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
    # Either a text response or structured tool calls — both are acceptable.
    tool_calls = message.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        assert isinstance(func.get("name"), str), "tool call name must be a str"
        args_raw = func.get("arguments")
        assert isinstance(args_raw, str), "arguments must be a JSON string"
        assert isinstance(json.loads(args_raw), dict), "arguments must decode to a dict"


@requires_groq
def test_open_door_and_go_to_main_hall_does_not_raise(  # type: ignore[no-untyped-def]
    client, state
) -> None:
    """Regression: open door + move must not raise a Groq 400 error.

    Was failing with:
      failed_generation: '<function=move_to={"location_id": ...}</function>'
    """
    from fantsu.narrator import process_input

    narration, _ = process_input(
        "open the door and go to the main hall",
        state,
        client,
        client,
    )
    assert isinstance(narration, str)
    assert len(narration) > 0


@requires_groq
def test_sequential_commands_do_not_raise(client, state) -> None:  # type: ignore[no-untyped-def]
    """Each command in a short play session returns a non-empty narration."""
    from fantsu.narrator import process_input

    commands = ["look around", "open the door", "go to the main hall"]
    for cmd in commands:
        narration, state = process_input(cmd, state, client, client)
        assert isinstance(narration, str) and len(narration) > 0, (
            f"Empty narration for command {cmd!r}"
        )
