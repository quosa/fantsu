# Fix: cannot talk to NPCs ("There is no one called 'Master_Aldric'")

## Problem

In the deployed game, `talk to Master Aldric` failed with
`There is no one called 'Master_Aldric'.` (and `'master_aldric'`), even though
Aldric was standing in the hall.

Root cause: `talk_to` resolves the NPC by exact id (`state.npcs.get(npc_id)`,
real id `aldric`), but the narrator model was never told the id existed.
`_build_context` listed Time / Location / Exits / Items / Containers / Carrying /
Recent events — every category except **NPCs**. Exits, items, and containers are
all rendered with an explicit `(id=...)` precisely so the model passes the right
identifier; NPCs were simply omitted from that pattern. With only the display
name "Master Aldric" available from the narration, the model fabricated an id by
normalising the name (`Master_Aldric` / `master_aldric`), which never matches the
key `aldric`.

The test suite missed it because the narrator mocks hand the dispatcher
`npc_id: "aldric"` directly, so the context gap is invisible under `make check`.

## Approach

Two complementary changes:

1. **The real fix — expose NPC ids in context.** Add an `NPCs here:` line to
   `_build_context` listing each co-located NPC as `Name (id=...)`, mirroring the
   existing exits/items/containers convention. NPCs are filtered by
   `location_id == player_location_id`, matching `validate_talk_to`'s own
   presence check so the two never disagree.

2. **Belt-and-suspenders — tolerant resolution.** Add `resolve_npc_id(ref, state)`
   in `tools.py` that matches a reference against each NPC's id, full display
   name, and individual name words (case-insensitive, underscores treated as
   spaces), preferring a co-located NPC on ambiguity. The narrator dispatch now
   resolves before validating. This is justified by the known single-LLM-call
   architecture (documented in CLAUDE.md): a turn cannot recover from a bad id
   mid-flight, so the dispatcher should accept the loose references models
   actually produce.

Also tightened the `talk_to` `npc_id` schema description to point at the
`NPCs here` line.

## Rejected alternatives

- **Resolver only, no context line.** Would paper over the symptom but leave the
  model blind to NPC ids — fragile, and inconsistent with how exits/items are
  already handled. The context line is the principled fix; the resolver is a net.
- **Rename the NPC id to match the display name.** Brittle, breaks saved-state
  expectations and every `aldric` reference in code/tests, and doesn't
  generalise to multi-word names.

## Verification

- [x] `test_build_context_shows_present_npcs_with_ids` — context contains
      `Master Aldric` and `id=aldric`.
- [x] `test_build_context_npcs_absent_when_alone` — `NPCs here: no one` when alone.
- [x] `resolve_npc_id` unit tests: exact id, `Master_Aldric`, `master aldric`,
      bare `Aldric`, and unknown/empty → `None`.
- [x] `test_process_input_talk_to_resolves_fabricated_id` — a `Master_Aldric`
      tool call now starts the dialogue with `aldric` instead of erroring.
- [x] `make check` passes.
- [ ] Redeploy to the HF Space and confirm `talk to Aldric` in the hall works.
