# Deterministic Game Test Driver

## Context

The game is playable locally but needs a deterministic end-to-end test that
verifies the core task ("feed the animals") can be completed from start to
finish. The existing tests in `test_tools.py` and `test_narrator.py` cover
individual actions and short sequences but nothing exercises the full walkthrough.

The goal is `tests/test_playthrough.py`, which:
1. Drives the game through all 10 steps to task completion with **no LLM calls**
2. Provides rich state assertions at each checkpoint so regressions are easy to pinpoint
3. Also tests the full narrator pipeline (context building + tool dispatch) via a
   `ScriptedNarratorClient` that returns pre-defined tool calls in sequence

---

## Walkthrough route (verified against world.py)

```
farmhand_quarters
  │ open_portal("main_hall")   — wooden door starts closed
  ↓ move_to("main_hall")       — room → +2 min
  ↓ move_to("yard")            — zone → +5 min  (front door already open)
  ↓ move_to("storehouse")      — room → +2 min  (no portal)
  → take_item("bucket")
  → use_item("bucket", "feed_sack")   — bucket.state["filled"] = True
  ↓ move_to("yard")            — zone → +5 min
  → open_portal("barn")        — barn door starts closed
  ↓ move_to("barn")            — room → +2 min
  → use_item("bucket", "animals")    — task.completed = True ✓
```

Total time elapsed: 16 in-game minutes
(`TIME_PER_ROOM_ACTION = 2`, `TIME_PER_ZONE_TRAVERSAL = 5` per `config.py`).

---

## Implementation

### `ScriptedNarratorClient`

Minimal `LLMClient` implementation that takes a list of `(tool_name, args)` pairs
and returns them one per `chat()` call in Ollama-format `tool_calls`. When the
script is exhausted it returns an empty `tool_calls` list so `process_input`
falls back to `"Nothing happens."` safely. Has an `exhausted` property for
post-loop assertions.

### `MockNPCClient`

Stub required because `process_input` always takes two clients. Returns a
fixed `"Aye."` response; identical pattern to `test_narrator.py`.

### Test 1: `test_task_completes_via_tools`

Calls tool functions **directly** — no narrator, no mocking at all. Assertions
after every major milestone so a failure message immediately identifies the
broken step:

- Leave quarters: `open_portal` + `move_to("main_hall")`
- Reach storehouse: `move_to("yard")` + `move_to("storehouse")`
- Get grain: `take_item("bucket")` + `use_item("bucket", "feed_sack")`
- Feed animals: `move_to("yard")` + `open_portal("barn")` + `move_to("barn")` + `use_item("bucket", "animals")`

### Test 2: `test_task_completes_via_process_input`

Uses `ScriptedNarratorClient` with `process_input()` to exercise the full
narrator pipeline (context building, `_dispatch_tool_call`, response
formatting) without any real LLM. After all 10 steps:

```python
assert narrator.exhausted
assert state.tasks[0].completed is True
assert state.player_location_id == "barn"
assert state.items["bucket"].state["filled"] is False  # emptied by feeding
assert state.time == 16
```

Asserts on `build_context(state)` to verify the raw context visible to the
narrator reflects the final state:

```python
ctx = build_context(state)
assert "Barn" in ctx
assert "wooden bucket" in ctx          # still in inventory
assert "Player fed the animals" in ctx  # event log entry
```

---

## Files

| File | Role |
|------|------|
| `tests/test_playthrough.py` | New test driver |
| `fantsu/tools.py` | Tool functions called directly in test 1 |
| `fantsu/narrator.py` | `process_input` and `build_context` used in test 2 |
| `fantsu/world.py` | `build()` fixture |
| `fantsu/config.py` | `TIME_PER_ROOM_ACTION`, `TIME_PER_ZONE_TRAVERSAL` constants |

No existing files were modified.
