# Fantsu — Technical Implementation Plan

## Package Layout

Everything lives in a `fantsu/` package. This keeps imports clean and test
discovery simple. The repo root holds project configuration only.

```
fantsu/
  __init__.py
  config.py          # constants only
  state.py           # dataclasses only, zero logic
  renderer.py        # pure string formatting, no I/O
  tools.py           # game actions — mutate GameState, return ToolResult
  tool_schema.py     # Ollama/OpenAI tool-call JSON definitions
  prompts.py         # all system prompt strings
  npc.py             # NPC dialogue via LLM
  narrator.py        # narrator LLM loop with tool dispatch
  world.py           # build() + tick_npcs()
  main.py            # game loop entry point

tests/
  __init__.py
  test_state.py      # dataclass construction & JSON round-trip
  test_world.py      # world structure, NPC tick
  test_renderer.py   # location text, format_time
  test_tools.py      # each tool against real GameState, no LLM
  test_narrator.py   # narrator with mock LLM

pyproject.toml       # dependencies, build backend, tool config
Makefile             # dev shortcuts: test, lint, fmt, run, build
.github/workflows/ci.yml
```

---

## Key Design Decisions

### 1. `ToolResult` type

Tools return a structured result instead of a raw string so the narrator can
distinguish success from failure without string-parsing:

```python
@dataclass
class ToolResult:
    ok: bool
    message: str
```

### 2. `LLMClient` protocol for testability

A thin protocol decouples all LLM-calling code from the real Ollama client.
Tests inject a `MockLLMClient`; production code passes an `OllamaClient`.
No network calls in unit tests.

```python
class LLMClient(Protocol):
    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict: ...
```

### 3. Dependency order (no circular imports)

```
config → state → renderer → tools → tool_schema → prompts → npc → narrator → world → main
```

`world.py` imports from `state`, `config`, and `tools` (for tick).
`main.py` imports everything at the top level.

### 4. NPC location tracking

`Location.npc_ids` is the single source of truth for rendering.
`NPC.location_id` is always kept in sync with it.
`world.tick_npcs` is the only function that moves NPCs;
game tools never relocate NPCs directly.

### 5. `use_item` dispatch table

Instead of a chain of `if/elif`, `use_item` resolves `(item_id, target_id)`
against a dict of handler functions:

```python
ITEM_HANDLERS: dict[tuple[str, str], Callable[[GameState], ToolResult]] = {
    ("bucket", "feed_sack"): _fill_bucket,
    ("bucket", "animals"):   _feed_animals,
}
```

Each handler is a small, independently testable function. New interactions
are added by inserting a key — existing handlers are untouched.

### 6. State is always JSON-serialisable

`GameState` uses only `str`, `int`, `bool`, `list`, and `dict`.
`Literal` types are used only as type hints and do not appear in runtime data.
`dataclasses.asdict(state)` produces a plain dict that round-trips through
`json.dumps` / `json.loads` with no custom encoder, keeping save/load trivial.

---

## Build Pipeline

### `pyproject.toml`

- Build backend: `hatchling`
- Console entry point: `fantsu = "fantsu.main:main"` (so `pip install fantsu`
  exposes the `fantsu` command)
- Runtime dep: `ollama`
- Dev deps: `pytest`, `pytest-cov`, `ruff`, `mypy`, `build`

### `Makefile` targets

| Target | Command |
|--------|---------|
| `make test` | `pytest --tb=short -q` |
| `make cov` | `pytest --cov=fantsu --cov-report=term-missing` |
| `make lint` | `ruff check fantsu/ tests/` |
| `make fmt` | `ruff format fantsu/ tests/` |
| `make typecheck` | `mypy fantsu/` |
| `make check` | `lint` + `typecheck` + `test` (pre-push gate) |
| `make build` | `python -m build` (verifies wheel builds cleanly) |
| `make run` | `python -m fantsu.main` |

### GitHub Actions CI (`.github/workflows/ci.yml`)

Triggered on push and pull_request to `main`:

1. Checkout
2. Set up Python 3.11
3. `pip install -e ".[dev]"`
4. `make check`
5. `make build` (verify wheel is buildable)

Ollama is **not** required in CI — all LLM calls are mocked in tests.

### Distribution

- `python -m build` produces `dist/fantsu-<ver>-py3-none-any.whl`
- Wheel can be shared directly (`pip install fantsu-*.whl`) or uploaded to PyPI
  via `twine`
- GitHub Release workflow (future): publish wheel as a release asset on a
  version tag

---

## Implementation Phases

| Phase | Deliverable | Tests added |
|-------|-------------|-------------|
| 1 | Scaffolding: `pyproject.toml`, Makefile, CI, `tests/` skeleton | `make check` passes on empty suite |
| 2 | `config.py` + `state.py` | `test_state.py`: construct every dataclass, JSON round-trip |
| 3 | `world.py` (`build()` only) | `test_world.py`: 6 locations, items in right place, NPCs at dawn positions |
| 4 | `renderer.py` | `test_renderer.py`: `format_time` full coverage, location text contains exits/items/NPCs |
| 5 | `tools.py` + `tool_schema.py` | `test_tools.py`: move (valid/blocked/missing), take/drop, use_item pairs, talk_to absent-NPC error |
| 6 | `prompts.py` + `npc.py` | `test_npc.py`: mock LLM, assert system prompt contains NPC name and memory |
| 7 | `narrator.py` | `test_narrator.py`: mock LLM returning a tool call → correct state mutation + narration |
| 8 | `world.tick_npcs` | extend `test_world.py`: Jakob moves to barn at correct time |
| 9 | `main.py` game loop | smoke test: `echo -e "look\nquit" \| python -m fantsu.main` exits 0 |

---

## Testing Philosophy

- **No LLM calls in tests.** `npc.py` and `narrator.py` receive an `LLMClient`
  argument; tests inject a `MockLLMClient` with canned responses.
- **Tools tested in isolation.** Call `tools.move_to("barn", state)` directly —
  no narrator involved.
- **Renderer tested with fixed fixtures.** Construct minimal `GameState` objects
  in each test; do not rely on `world.build()`.
- **One test file per module.** Failures point immediately to the affected layer.
- **Coverage target:** 80%+ on `fantsu/`, excluding the `if __name__ == "__main__"`
  block in `main.py` and the real-Ollama paths in `npc.py` / `narrator.py`.
