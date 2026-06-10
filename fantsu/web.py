"""Gradio chat UI that wraps the game loop for online play.

The pure session helpers (``new_session`` / ``play_turn`` / ``intro_text``)
contain all the game-loop logic and import no web framework, so they are
unit-tested with mock LLM clients exactly like ``narrator.process_input``.

The Gradio glue (``build_app`` / ``main``) imports ``gradio`` lazily so that
``make check`` and the test-suite never need it installed; install the optional
``web`` extra to actually run the server::

    pip install -e ".[web]"
    GROQ_API_KEY=gsk_... python -m fantsu.web

Backend selection mirrors ``main.py``: Groq if ``GROQ_API_KEY`` is set, else
the local Ollama daemon.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fantsu import config, world
from fantsu.narrator import process_input
from fantsu.npc import LLMClient
from fantsu.renderer import describe_location
from fantsu.scenes import ENDING_TEXT, OPENING_SCENE
from fantsu.state import GameState

# ------------------------------------------------------------------ #
# Pure session logic (no web framework, fully testable)               #
# ------------------------------------------------------------------ #


@dataclass
class Session:
    """One player's in-memory game, mirroring main.py's loop variables."""

    state: GameState
    seen_completed: set[str] = field(default_factory=set)
    over: bool = False


def new_session() -> Session:
    """Start a fresh game."""
    return Session(state=world.build())


def intro_text(session: Session) -> str:
    """The opening scene plus the starting location description."""
    return f"{OPENING_SCENE}\n{describe_location(session.state)}"


def play_turn(
    player_input: str,
    session: Session,
    narrator_client: LLMClient,
    npc_client: LLMClient,
) -> str:
    """Advance one turn, mutating ``session``, and return the narration text.

    Mirrors the body of ``main.main``'s loop: run the narrator, announce newly
    completed tasks, append the ending when every task is done, otherwise tick
    NPC schedules.
    """
    if session.over:
        return 'The game is over. Press "New game" to play again.'

    narration, session.state = process_input(
        player_input, session.state, narrator_client, npc_client
    )
    parts = [narration]

    for task in session.state.tasks:
        if task.completed and task.id not in session.seen_completed:
            session.seen_completed.add(task.id)
            parts.append(f"*** Task complete: {task.description} ***")

    if session.state.tasks and all(t.completed for t in session.state.tasks):
        parts.append(ENDING_TEXT)
        session.over = True
    else:
        world.tick_npcs(session.state)

    return "\n\n".join(parts)


# ------------------------------------------------------------------ #
# Gradio glue (lazy import; needs the optional `web` extra)            #
# ------------------------------------------------------------------ #

INTRO_MARKDOWN = (
    "# Fantsu\n"
    "A text adventure with LLM-backed NPCs. Type naturally — the narrator "
    "interprets your intent. Try `look`, `take the bucket`, "
    "`open the wooden door`, `talk to Aldric`."
)


def _build_clients() -> tuple[LLMClient, LLMClient]:
    """Pick the Groq or Ollama backend exactly as main.py does."""
    if config.GROQ_API_KEY:
        from fantsu.clients.groq_client import GroqClient

        return GroqClient(), GroqClient()
    from fantsu.clients.ollama_client import OllamaClient

    return OllamaClient(), OllamaClient()


def build_app():  # type: ignore[no-untyped-def]
    """Construct the Gradio Blocks app. Each browser session gets its own game."""
    import gradio as gr

    narrator_client, npc_client = _build_clients()

    def _start() -> tuple[Session, list[dict[str, str]]]:
        session = new_session()
        return session, [{"role": "assistant", "content": intro_text(session)}]

    def _respond(
        player_input: str,
        history: list[dict[str, str]],
        session: Session | None,
    ) -> tuple[list[dict[str, str]], Session, str]:
        if session is None:
            session, history = _start()
        text = player_input.strip()
        if not text:
            return history, session, ""
        history = history + [{"role": "user", "content": text}]
        try:
            narration = play_turn(text, session, narrator_client, npc_client)
        except Exception as exc:  # noqa: BLE001
            narration = f"[Error: {exc}]"
        history = history + [{"role": "assistant", "content": narration}]
        return history, session, ""

    with gr.Blocks(title="Fantsu") as demo:
        gr.Markdown(INTRO_MARKDOWN)
        session_state = gr.State()
        chatbot = gr.Chatbot(height=460, label="Fantsu")
        msg = gr.Textbox(
            placeholder="What do you do?",
            autofocus=True,
            show_label=False,
        )
        new_game = gr.Button("New game")

        demo.load(_start, outputs=[session_state, chatbot])
        msg.submit(
            _respond,
            [msg, chatbot, session_state],
            [chatbot, session_state, msg],
        )
        new_game.click(_start, outputs=[session_state, chatbot])

    return demo


def main() -> None:
    """Run the web server (Hugging Face Spaces / local)."""
    build_app().launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
