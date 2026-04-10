"""Main game loop."""

from __future__ import annotations

import ollama as ollama_lib

from fantsu import world
from fantsu.narrator import process_input
from fantsu.npc import LLMClient
from fantsu.renderer import describe_location
from fantsu.state import GameState


class OllamaClient:
    """Production LLM client backed by the local Ollama instance."""

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        kwargs = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools  # type: ignore[assignment]
        response = ollama_lib.chat(**kwargs)
        # ollama returns a ChatResponse object; normalise to plain dict
        if hasattr(response, "model_dump"):
            raw: dict[str, object] = response.model_dump()
        else:
            raw = dict(response)
        return raw


OPENING_SCENE = """\
You wake to a sharp knock at your door.

"Up with you!" Aldric's voice, gruff but not unkind. "The animals haven't
been fed. Take the bucket from the storehouse, fill it with grain, and see
to the goats and chickens in the barn. There's bread in the kitchen when
you're done."

His footsteps retreat toward the main hall.
"""


def _check_tasks(state: GameState) -> list[str]:
    """Return descriptions of any tasks just completed."""
    completed = []
    for task in state.tasks:
        if task.completed:
            completed.append(task.description)
    return completed


def main() -> None:
    state = world.build()

    narrator_client: LLMClient = OllamaClient()
    npc_client: LLMClient = OllamaClient()

    # Opening scene — hardcoded, no LLM needed
    print(OPENING_SCENE)
    print(describe_location(state))

    seen_completed: set[str] = set()

    while True:
        try:
            player_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFarewell.")
            break

        if not player_input:
            continue
        if player_input.lower() in ("quit", "exit", "q"):
            print("Farewell.")
            break

        try:
            narration, state = process_input(
                player_input, state, narrator_client, npc_client
            )
        except Exception as exc:  # noqa: BLE001
            print(f"\n[Error: {exc}]")
            continue

        print(f"\n{narration}")

        # Announce newly completed tasks
        for task in state.tasks:
            if task.completed and task.id not in seen_completed:
                seen_completed.add(task.id)
                print(f"\n[Task complete: {task.description}]")

        # Tick NPC schedules after each player action
        world.tick_npcs(state)


if __name__ == "__main__":
    main()
