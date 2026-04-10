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
  groq_client.py  GroqClient — calls Groq cloud API (excluded from mypy)
  ollama_client.py  OllamaClient — calls local Ollama daemon (excluded from mypy)
  main.py         game loop entry point (excluded from mypy)

tests/
  test_state.py / test_world.py / test_renderer.py
  test_tools.py / test_npc.py / test_narrator.py
```

## Architecture rules

- **No circular imports.** Dependency order:
  `config → state → renderer → tools → tool_schema → prompts → npc → narrator → world → groq_client / ollama_client → main`
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

## Testing philosophy

- One test file per module
- Tools are tested by calling them directly with a `build()` state fixture
- LLM paths are always mocked — `make check` never calls Ollama or Groq
- Coverage target: 80 %+ on `fantsu/` excluding `main.py`

## What's intentionally not there yet

- Save / load (state is `dataclasses.asdict`-ready — just needs file I/O)
- Multiple tasks / quest chains
- Inventory limits or item weight
- Combat or skill checks
- NPC reactions to being moved by the schedule tick
