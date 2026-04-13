# Entity & Map System Redesign

## Problem

The original design gave each directional exit its own `Portal` instance. Opening
a door from room A mutated that exit's Portal but left the reverse exit's Portal
untouched, so the door appeared closed again when viewed from room B. Additionally,
there was no data model for containers (chests, cabinets, drawers), item state was
not visible in room descriptions, and the outdoor zone beyond the farm gate was a
dead stub with no navigable sub-locations.

## Approach

### Shared door state via `Door` entity

Replaced the inline `Portal` dataclass on `Exit` with a foreign key `door_id: str | None`
that references a `Door` object stored in `GameState.doors`. Both directions of a
bidirectional door reference the **same** `door_id`, so mutating `door.state` is
immediately visible from either side.

One-way and asymmetric passages are handled by the same model without special-casing:

| Pattern | Forward exit | Reverse exit |
|---|---|---|
| Bidirectional door | `door_id="X"` | `door_id="X"` (same object) |
| True one-way | `door_id="X"` (or None) | no exit exists |
| Asymmetric valve (trapdoor) | `door_id=None` (always passable) | `door_id="X"` (blocks return) |
| Independent sides (portcullis) | `door_id="X"` | `door_id="Y"` (separate object) |

### Container entity

Added a `Container` dataclass with `state` (open/closed/locked), `locked_by`,
`item_ids`, and `portable`. Containers live in `GameState.containers` and are
referenced from `Location.container_ids`. Portable containers additionally appear
in `Location.item_ids` / `player_inventory` for movement tracking.

"Light containers" that just track fill state (bucket, mug) remain plain `Item`
objects with `state_labels`; they do not need `Container`.

### Renderer

A single flat "You see:" line merges items and containers. Items use `_item_label`
to show active `state_labels` annotations (e.g. "bucket (filled with grain)");
containers use `_container_label` to show their state (e.g. "old chest (closed)").
Inventory rendering also uses `_item_label`.

### Outdoor zone extension

`road_south` was upgraded from a dead stub to a real navigable zone. Four new
locations were added:

```
yard
  └─[farm_gate]─► road_south (zone)
                       ├── woods_edge (room) — dark tree-line
                       └── field_path (zone) — open sky
                                └── field_end (room, stub)
```

`road_south` Features gained `enterable=True` + `destination` so the existing
Feature machinery (enter the woods / walk into the fields) works without new tools.

## Rejected alternatives

**Unified `WorldObject` (doors + containers in one dict with `kind` discriminator)**:
Too much blast radius — every portal reference across all layers would change, and
mypy type narrowing becomes awkward with a discriminated union.

**Post-move sync**: Fragile. Requires knowing which exit is the "reverse", silently
breaks for one-way passages, and leaves stale state visible between sync points.

**Container as special Item subtype**: Muddies `take_item` — every item tool would
need to defensively check `container=True`. Separate `Container` keeps type roles
unambiguous.

## Files changed

- `fantsu/state.py` — `Portal` deleted; `Door`, `Container` added; `Exit.portal` →
  `Exit.door_id`; `Location.container_ids` added; `GameState.doors` / `.containers` added
- `fantsu/world.py` — shared `Door` objects; four new outdoor locations; `gnarled_stick` item
- `fantsu/tools.py` — `open_portal`, `close_portal`, `move_to` updated for door lookup;
  `open_container`, `take_from`, `put_into` added
- `fantsu/renderer.py` — exit rendering via `state.doors`; `_item_label`; containers in "You see:"
- `fantsu/tool_schema.py` — `open_container`, `take_from`, `put_into` definitions added
- `fantsu/narrator.py` — imports, dispatch branches, context containers block updated
- `tests/test_state.py`, `tests/test_tools.py`, `tests/test_renderer.py`, `tests/test_world.py`

## Verification checklist

- [ ] `make check` passes (lint + typecheck + tests)
- [ ] Open wooden door, step to main hall, look back — door shows open from both sides
- [ ] Step through front door to yard, look back — front door shows open
- [ ] New outdoor zones navigable: farmhand → yard → road → woods_edge / field_path
- [ ] Bucket renders as "wooden bucket (filled with grain)" when filled
- [ ] Container open/closed state shown in "You see:" line
- [ ] `take_from` / `put_into` work end-to-end once a container is added to the world
