"""fanturer — run an LLM player against the game from the command line.

Usage:
    fanturer "go talk to Jakob"
    fanturer "wear the boots" --max-turns 5
    fanturer "feed the animals" --max-turns 20 --timeout 120
"""

from __future__ import annotations

import argparse
import re
import signal
import sys
import time

from fantsu import config, prompts, world
from fantsu.clients.ollama_client import OllamaClient
from fantsu.clients.z_client import ZAIClient
from fantsu.narrator import process_input
from fantsu.npc import LLMClient
from fantsu.renderer import describe_location
from fantsu.state import GameState


class _MockNPCClient:
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {"message": {"content": "Aye."}}


def _parse_action(content: str) -> str:
    m = re.search(r"^Action:\s*(.+)", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else content.strip()


def _parse_status(content: str) -> str:
    """Return 'DONE', 'FAILED', or 'ONGOING'."""
    m = re.search(r"^Status:\s*(\w+)", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1).upper() if m else "ONGOING"


def _run(
    goal: str,
    max_turns: int,
    timeout: float,
    narrator: LLMClient,
    npc_client: LLMClient,
    player_client: LLMClient,
) -> None:
    state: GameState = world.build()
    history: list[dict[str, str]] = [
        {"role": "system", "content": prompts.LLM_PLAYER_SYSTEM.format(goal=goal)},
    ]

    print(f"\nGoal: {goal}")
    print(f"Max turns: {max_turns}  |  Timeout: {timeout}s\n")
    print("─" * 60)
    print(describe_location(state))
    print("─" * 60)

    start = time.monotonic()

    narration, state = process_input("look around", state, narrator, npc_client)
    print(f"\n{narration}\n")

    for turn in range(1, max_turns + 1):
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            print(f"\n[timeout after {elapsed:.0f}s]")
            break

        print(f"Turn {turn}/{max_turns}  ({elapsed:.0f}s elapsed)")

        history.append({"role": "user", "content": narration})
        print("  [player...]", end=" ", flush=True)
        player_response = player_client.chat(model="", messages=history)
        player_msg = player_response.get("message", {})
        player_text = (
            str(player_msg.get("content", ""))
            if isinstance(player_msg, dict)
            else str(player_msg)
        )
        history.append({"role": "assistant", "content": player_text})

        command = _parse_action(player_text)
        status = _parse_status(player_text)

        for line in player_text.splitlines():
            print(f"  {line}")
        print(f"\n  > {command!r}")

        if status == "DONE":
            print("\n✓ Player reports goal achieved.")
            break
        if status == "FAILED":
            print("\n✗ Player reports it cannot make progress.")
            break

        print("  [narrator...]", end=" ", flush=True)
        narration, state = process_input(command, state, narrator, npc_client)
        print(f"\n  {narration}\n")
        print("─" * 60)
    else:
        print(f"\n[reached max turns: {max_turns}]")


def _timeout_handler(signum: int, frame: object) -> None:  # noqa: ARG001
    print("\n[hard timeout — exiting]")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fanturer",
        description="Run an LLM player against the Fantsu game.",
    )
    parser.add_argument("goal", help="Natural language goal for the player LLM")
    parser.add_argument(
        "--max-turns", type=int, default=20, metavar="N",
        help="Maximum number of turns (default: 20)",
    )
    parser.add_argument(
        "--timeout", type=float, default=300, metavar="SECONDS",
        help="Total wall-clock timeout in seconds (default: 300)",
    )
    args = parser.parse_args()

    if config.Z_API_KEY:
        print("Backend: Z.ai (glm-4.7)")
        narrator: LLMClient = ZAIClient()
        player_client: LLMClient = ZAIClient()
    else:
        print("Backend: local Ollama (Z_API_KEY not set)")
        narrator = OllamaClient()
        player_client = OllamaClient()

    # SIGALRM fires 30s after the timeout as a hard backstop if an API call hangs
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(int(args.timeout) + 30)

    npc_client: LLMClient = _MockNPCClient()

    try:
        _run(
            goal=args.goal,
            max_turns=args.max_turns,
            timeout=args.timeout,
            narrator=narrator,
            npc_client=npc_client,
            player_client=player_client,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
