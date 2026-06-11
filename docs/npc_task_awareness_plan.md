# Fix: NPCs invent uncompletable tasks instead of tracking real ones

## Problem

When the player has an assigned task (`feed_animals`, given by Aldric) and talks
to Aldric, he invents a *different*, uncompletable errand — e.g. "Barn roof's
been troubling me … get that done first, 'fore helpin' with the chores in the
yard." The game engine cannot track or complete "mend the barn roof", so the
player is sent after a dead-end and the real task is buried.

Two causes in the NPC dialogue prompt:

1. `build_npc_system_prompt` never told the NPC about the player's outstanding
   tasks — including the ones that NPC personally set. The NPC had no idea a
   chore was already pending.
2. `NPC_SYSTEM_TEMPLATE` ended with *"You may hint at tasks, rumours, or needs"*,
   actively inviting the model to fabricate new chores.

## Approach

1. **Give the NPC its own open tasks.** In `build_npc_system_prompt`, collect
   `state.tasks` where `giver_id == npc_id and not completed` and render them in
   a new template section, "Tasks you have set the new hand, still unfinished".
   The list is recomputed every turn, so a task drops off as soon as it is
   completed (`tools._feed_animals` sets `completed = True`).

2. **Forbid inventing new tasks.** Replace the task-hinting line with guidance to
   keep the player pointed at the listed tasks and explicitly NOT to invent new
   chores, errands, or quests — "the tasks listed above are the only work that
   counts." Rumours / news / worries are still allowed, preserving flavour.

Scope is deliberately the *giver's own* tasks (per the observed bug), not every
task in the game — an NPC shouldn't recite chores another NPC set.

## Rejected alternatives

- **Only edit the prompt wording, no task injection.** Telling the model "don't
  invent tasks" without showing the real one would leave it with nothing to
  steer toward; it would likely still improvise.
- **Inject all tasks regardless of giver.** Would have NPCs reference work they
  never assigned, which reads oddly and risks cross-talk between givers.
- **Hard-code task text in the prompt.** Breaks as soon as tasks change; the
  fix reads live from `state.tasks` so new tasks need no prompt edits.

## Verification

- [x] `test_system_prompt_lists_givers_open_tasks` — Aldric's prompt shows the
      feed_animals description.
- [x] `test_system_prompt_omits_completed_tasks` — completed tasks drop off.
- [x] `test_system_prompt_omits_other_givers_tasks` — Marta's prompt omits
      Aldric's task.
- [x] `test_system_prompt_discourages_inventing_tasks` — the "do NOT invent new
      chores" guidance is present.
- [x] `make check` passes.
- [ ] Redeploy and confirm Aldric steers the player to feeding the animals
      rather than the barn roof.
