"""Tests for fantsu.web pure session logic — LLM clients are mocked.

The Gradio glue (build_app/main) is not imported here; gradio is not a test
dependency. Only the framework-free helpers are exercised.
"""

from fantsu.web import Session, intro_text, new_session, play_turn


class MockNarratorClient:
    """Returns a configurable Ollama-style response (no tool calls)."""

    def __init__(self, content: str = "You look around.") -> None:
        self.content = content

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {"message": {"content": self.content, "tool_calls": []}}


class MockNPCClient:
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {"message": {"content": "Aye."}}


def test_new_session_starts_fresh() -> None:
    session = new_session()
    assert isinstance(session, Session)
    assert session.over is False
    assert session.seen_completed == set()
    assert session.state.player_location_id


def test_intro_text_includes_opening_and_location() -> None:
    session = new_session()
    text = intro_text(session)
    assert "Aldric" in text  # from the opening scene
    assert len(text) > 0


def test_play_turn_returns_narration() -> None:
    session = new_session()
    narration = play_turn(
        "look around", session, MockNarratorClient("A quiet room."), MockNPCClient()
    )
    assert "A quiet room." in narration
    assert session.over is False


def test_play_turn_announces_completed_task_and_ends() -> None:
    session = new_session()
    # Force every task complete, then take a turn: the ending should fire once.
    for task in session.state.tasks:
        task.completed = True
    narration = play_turn(
        "feed the animals", session, MockNarratorClient(), MockNPCClient()
    )
    assert session.over is True
    assert "completed all tasks" in narration
    # Each completed task is announced exactly once.
    for task in session.state.tasks:
        assert task.id in session.seen_completed


def test_play_turn_skips_npc_tick_during_dialogue() -> None:
    session = new_session()
    # Open a conversation with Jakob, then advance time so his schedule
    # would normally move him out of the barn on the next tick.
    from fantsu.npc import start_dialogue

    start_dialogue("jakob", session.state)
    session.state.time = 600
    before = session.state.npcs["jakob"].location_id
    play_turn("how goes it?", session, MockNarratorClient(), MockNPCClient())
    assert session.state.npcs["jakob"].location_id == before


def test_play_turn_is_noop_after_game_over() -> None:
    session = new_session()
    session.over = True
    narration = play_turn(
        "look", session, MockNarratorClient(), MockNPCClient()
    )
    assert "New game" in narration
