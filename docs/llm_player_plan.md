# LLM Player Integration Test

## Problem

The game had no way to verify that a real LLM could actually navigate it via natural language. Unit tests use scripted or mocked clients; they confirm the game engine works but say nothing about whether the prompts and tool schema are clear enough for a live model to use.

## Approach

A Z.ai GLM-4.7 model acts as the "player" — it receives game narration, forms an expectation, and issues natural language commands. A second GLM-4.7 instance acts as the narrator, interpreting those commands into tool calls via the existing `process_input` pipeline. No changes to game logic were needed.

The player drives the loop directly in-process (not as a separate subprocess). This keeps the setup simple: `world.build()` creates a fresh state, and `process_input` is called in a loop until the success condition is met or attempts are exhausted.

### Why not a separate process?

A separate process would replicate the CLI's `main()` loop and require parsing stdout. In-process is simpler, gives direct access to `GameState` for success checking, and produces a clean transcript for failure messages.

### Why GLM-4.7 for both roles?

It is the most capable model available on the Z.ai lite coding plan and supports function calling (required by the narrator role). Using a single model for both keeps the setup self-contained.

## Rejected alternatives

- **ScriptedNarratorClient for narrator**: would test only the player's phrasing, not the narrator's ability to parse it — less realistic.
- **zai-sdk**: `openai` is already a dependency; adding a second SDK for the same API adds no value.
- **Test in main test suite**: live LLM calls must not run in CI. The test is guarded by `pytestmark = pytest.mark.skipif(not config.Z_API_KEY, ...)` so `make check` always passes without the key.

## Files changed

- `fantsu/clients/` — new package containing `groq_client.py`, `ollama_client.py` (moved), and `z_client.py` (new)
- `fantsu/config.py` — added `Z_API_KEY`
- `fantsu/main.py` — updated imports
- `tests/test_groq_integration.py` — updated imports
- `tests/test_llm_player.py` — new integration test
- `pyproject.toml` — updated mypy excludes

## Verification checklist

- [ ] `make check` passes without `Z_API_KEY` set
- [ ] `Z_API_KEY=... pytest tests/test_llm_player.py -v -s` runs and prints a turn-by-turn transcript
- [ ] Test passes: boots are worn within `MAX_ATTEMPTS = 10` turns
- [ ] On failure, the transcript is printed to aid debugging
