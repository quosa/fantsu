"""Main game loop."""

from __future__ import annotations

from fantsu import config, world
from fantsu.clients.groq_client import GroqClient
from fantsu.clients.ollama_client import OllamaClient
from fantsu.narrator import process_input
from fantsu.npc import LLMClient
from fantsu.renderer import describe_location
from fantsu.scenes import ENDING_TEXT, OPENING_SCENE


def main() -> None:
    state = world.build()

    if config.GROQ_API_KEY:
        print("Backend: Groq API")
        narrator_client: LLMClient = GroqClient()
        npc_client: LLMClient = GroqClient()
    else:
        print("Backend: local Ollama")
        narrator_client = OllamaClient()
        npc_client = OllamaClient()

    # Opening scene — hardcoded, no LLM needed
    print(OPENING_SCENE)
    print(describe_location(state))

    seen_completed: set[str] = set()

    while True:
        if state.dialogue is not None:
            partner = state.npcs[state.dialogue.npc_id].name
            prompt = f"\n[talking to {partner}] > "
        else:
            prompt = "\n> "
        try:
            player_input = input(prompt).strip()
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
        newly_done = []
        for task in state.tasks:
            if task.completed and task.id not in seen_completed:
                seen_completed.add(task.id)
                newly_done.append(task)

        for task in newly_done:
            print(f"\n*** Task complete: {task.description} ***")

        # If every task is done, print the ending and stop
        if state.tasks and all(t.completed for t in state.tasks):
            print(f"\n{ENDING_TEXT}")
            break

        # Tick NPC schedules after each player action, but not mid-conversation
        # so the dialogue partner can't walk off between exchanges.
        if state.dialogue is None:
            world.tick_npcs(state)


if __name__ == "__main__":
    main()
