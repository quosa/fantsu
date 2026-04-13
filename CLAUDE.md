# CLAUDE.md — Fantsu developer guide for Claude Code

## Build and test commands

```bash
make check      # lint + typecheck + tests (run this before every commit)
make test       # pytest only
make cov        # pytest with coverage report
make lint       # ruff check
make fmt        # ruff format (auto-fixes style)
make typecheck  # mypy strict
make build      # verify the wheel builds cleanly
make run        # python -m fantsu.main (uses Groq if GROQ_API_KEY is set, else local Ollama)
```

`make check` must pass before pushing. CI runs the same command.

## Package layout

```
fantsu/
  config.py       constants: model names, timing, memory limits; auto-selects backend
  state.py        all dataclasses — zero logic, always JSON-serialisable
  world.py        build() factory + tick_npcs() + advance_time()
  renderer.py     pure string formatting, no I/O
  tools.py        game actions → ToolResult; no LLM calls here
  tool_schema.py  OpenAI-compatible tool-call JSON definitions
  prompts.py      system prompt strings — tune here first
  npc.py          LLMClient protocol + NPC dialogue call
  narrator.py     process_input: LLM → tool dispatch → narration
  clients/
    groq_client.py    GroqClient — Groq cloud API (excluded from mypy)
    ollama_client.py  OllamaClient — local Ollama daemon (excluded from mypy)
    z_client.py       ZAIClient — Z.ai cloud API (excluded from mypy)
  main.py         game loop entry point (excluded from mypy)

tests/
  test_state.py / test_world.py / test_renderer.py
  test_tools.py / test_npc.py / test_narrator.py
  test_llm_player.py  Z.ai integration test (skipped without Z_API_KEY)
```

## Architecture rules

- **No circular imports.** Dependency order:
  `config → state → renderer → tools → tool_schema → prompts → npc → narrator → world → clients/* → main`
- **No LLM calls in tests.** `npc.py` and `narrator.py` accept an `LLMClient`
  argument; tests inject `MockLLMClient` / `MockNarratorClient`.
- **Tools are pure game logic.** They take `GameState`, mutate it in place,
  and return `ToolResult(ok, message)`. No network calls.
- **State is always JSON-serialisable.** `dataclasses.asdict(state)` must
  round-trip through `json.dumps` / `json.loads` without a custom encoder.

## Key extension points

### Adding a new tool

1. Implement `def my_tool(..., state: GameState) -> ToolResult` in `tools.py`
2. Add the Ollama JSON definition to `tool_schema.py`
3. Add a dispatch branch in `narrator._dispatch_tool_call`
4. Add tests in `test_tools.py` and `test_narrator.py`

### Adding a new use_item interaction

Add an entry to `_ITEM_HANDLERS` in `tools.py`:
```python
("item_id", "target_id"): _my_handler,
```
Add natural-language aliases for targets the LLM might choose.
Update the `use_item` description in `tool_schema.py` to hint at valid targets.

### Adding a new location

Add the `Location` object in `world.build()`, wire up `Exit` objects (with
`Portal` if there's a door), place items and NPCs, add the id to the locations
dict. No other files need to change.

### Adding a new NPC

Add an `NPC` dataclass in `world.build()`, set `location_id` and `schedule`,
add to `npcs` dict, and add the npc id to the starting location's `npc_ids`.

### Tuning LLM behaviour

- **Narrator prompt**: `fantsu/prompts.py` → `NARRATOR_SYSTEM`
- **NPC prompt template**: `fantsu/prompts.py` → `NPC_SYSTEM_TEMPLATE`
- **Models**: `fantsu/config.py` → `NARRATOR_MODEL` / `NPC_MODEL` (set automatically based on backend)
- **Backend**: set `GROQ_API_KEY` env var to use Groq; unset to use local Ollama

Prompt changes don't require code changes — edit and `make run` to test.

## Documentation for significant changes

For any significant change (new feature, architectural decision, prompt
tuning, behaviour fix), create a plan document in `docs/` and include it
in the same PR:

- Name it descriptively: `docs/<topic>_plan.md`
- Include: the problem being solved, the approach chosen and why, what was
  rejected and why, and a verification checklist
- Commit it alongside the code change, not as a follow-up

Minor changes (typos, dependency bumps, trivial refactors) don't need a
plan doc. When in doubt, write one — they're cheap and useful later.

## Testing philosophy

- One test file per module
- Tools are tested by calling them directly with a `build()` state fixture
- LLM paths are always mocked — `make check` never calls Ollama, Groq, or Z.ai
- Coverage target: 80 %+ on `fantsu/` excluding `main.py`

## What's intentionally not there yet

- Save / load (state is `dataclasses.asdict`-ready — just needs file I/O)
- Multiple tasks / quest chains
- Inventory limits or item weight
- Combat or skill checks
- NPC reactions to being moved by the schedule tick

## Known architectural limitation: game-state / LLM context drift

`narrator.process_input` makes a **single LLM call**, extracts any tool
calls from the response, executes them, and uses their results directly
as narration text.  The model never receives the tool results back as
grounded facts — so within a turn it plans all actions before any of
them execute, and across turns it only learns about world changes through
the `event_log[-5:]` snapshot in `_build_context`.

Consequences:
- **Within a turn**: the model decides `open_portal` + `move_to` in one
  shot, without ever confirming the door is now open.  Works when the
  model queues them in the right order; breaks if it doesn't.
- **Across turns**: fine-grained world state (portal open/closed, item
  `.state` fields, NPC positions) is invisible to the model unless it
  happens to appear in the recent event log.

The proper fix is the standard tool-calling loop:

```
call LLM → get tool_calls → execute → append {"role": "tool", ...}
messages → call LLM again for final narration
```

This gives the model grounded knowledge of what actually happened before
it writes the narration, eliminating drift.  Until then, keep
`_build_context` as informative as possible and write tool descriptions
that don't rely on the model tracking state across calls.
