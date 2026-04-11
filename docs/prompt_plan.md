# Narrator system prompt: rationale and design

## Problem

The narrator LLM was occasionally producing prose narration without calling any
tool, causing game state to drift — the player was told something happened when
it didn't.

This was exacerbated by a subtle mismatch in the original prompt:

- The old `NARRATOR_SYSTEM` said *"Describe results in second person, past
  tense, 2-3 sentences"* — implying the model's primary job is to write prose.
- In practice (`narrator.py`), **tool results are the narration**. The LLM's
  text content is only used as a fallback when *no* tool calls were made at all.
- So the model's prose is silently discarded on tool-call turns, but the
  instruction still encouraged the model to focus on narrative writing rather
  than tool invocation — likely reinforcing the drift behaviour.

## Goal

Rewrite `NARRATOR_SYSTEM` (`fantsu/prompts.py`) to:

1. Make tool invocation the explicit primary job.
2. State clearly that world state changes *only* through tool calls — never
   through narrated outcomes.
3. Reserve text-only responses strictly for the impossible-action case.
4. Remove the misleading style instruction that implied narration is the LLM's
   output on normal turns.

## Before → after

**Old prompt:**

```
You are the narrator of a medieval text adventure set on a farmstead.
Interpret the player's intent and call the appropriate game tools.
Describe results in second person, past tense, 2-3 sentences.
Be atmospheric but brief. Do not invent facts not in the game state.
If the player tries something impossible, call no tools and explain why briefly.
Never break the fourth wall or mention game mechanics directly.
```

**New prompt:**

```
You are the narrator of a medieval text adventure set on a farmstead.
Your primary job is to map the player's input to the correct tool call(s).

Rules:
- ALWAYS call the matching tool when the player attempts any action. Movement,
  items, doors, and dialogue ALL require a tool call — never describe an action
  as happening without calling the corresponding tool.
- Game world state changes ONLY through tool calls. Do not narrate outcomes
  you have not produced via a tool. Do not invent facts not in the game state.
- Only produce text without a tool call when the player's request is genuinely
  impossible given the current state. In that case, explain briefly why in
  second person (2-3 sentences max).
- Do not call tools for actions the player did not request.
- Never break the fourth wall or mention tools, mechanics, or the game system.
```

## What changed and why

| Old line | Issue | Fix |
|---|---|---|
| "Describe results in second person…" | Misleads the model into writing prose instead of calling tools; that prose is discarded by the code | Removed |
| "Be atmospheric but brief." | Style guidance that encourages narrative over tool calls | Removed — `tools.py` messages handle the player-facing text |
| "Interpret the player's intent and call the appropriate game tools." | Soft, buried alongside style instructions | Replaced with an explicit primary statement |
| "If the player tries something impossible, call no tools and explain why briefly." | Presented as a peer option alongside tool-calling | Reframed as the *exception* case |
| (new) "ALWAYS call the matching tool…" | Directly addresses the hallucination / no-tool-call bug | Added |
| (new) "Game world state changes ONLY through tool calls." | Tells the model not to narrate unexecuted outcomes | Added |

## Architectural note

`narrator.process_input` makes a **single LLM call**, extracts tool calls, and
uses their results as narration. The model's prose content is only shown to the
player when *no* tools were called (the impossible-action fallback path).

This means the style guidance ("second person, past tense") only matters for
that fallback path — which is why it was removed from the general rules and
scoped to the impossible-action carve-out.

The proper long-term fix is a tool-calling loop (call LLM → execute tools →
feed results back → call LLM again for final narration), described in
`CLAUDE.md` under "Known architectural limitation". Until then, the prompt
keeps `NARRATOR_SYSTEM` as directive as possible about when to call tools vs
when to produce text.

## Verification

1. `make check` — must pass (prompt is just a string constant; no LLM calls
   in the test suite).
2. `make run` — try commands that previously hallucinated (e.g. "go to the
   barn", "pick up the bucket") and verify the `event_log` reflects real tool
   calls, not invented narration.
3. Verify the impossible-action path still works: attempt something locked or
   absent and confirm a brief text explanation appears with no state change.
