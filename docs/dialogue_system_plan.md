# Dialogue system plan

## Problem

NPC interaction was a single one-shot LLM call per `talk_to` tool call:
no conversation history, no lasting memory beyond a clipped event-log
line, and a thin persona prompt. NPCs felt like vending machines, and
nothing constrained their worldview — the model would happily discuss
dragons, kings, or far-off cities.

Design goals (from the game's premise):

- NPCs are **limited in worldview**: never travelled further than the
  village market and a couple of neighbouring farms; ignorant of the
  wider world.
- NPCs are **expert** in farming and farmhouse upkeep.
- NPCs answer **briefly** — there is always a chore waiting.
- NPCs anticipate the **next town fair** and the **coming harvest**.

## Approach chosen

### 1. Dedicated dialogue mode

Saying something to an NPC (narrator routes the first utterance via the
existing `talk_to` tool) opens a conversation. While a conversation is
active, `process_input` sends player input **straight to the NPC's LLM**,
skipping the narrator call entirely — one LLM call per dialogue turn,
natural back-and-forth, full transcript in context.

A conversation ends when:

- the player says a farewell phrase (`config.FAREWELL_PHRASES`,
  word-boundary matched), or
- the turn cap (`config.DIALOGUE_MAX_TURNS`) is reached — on the final
  turn the NPC is instructed to excuse itself and mention the chore it
  is off to do, which enforces the "always something to do next" feel.

Conversation state lives in `GameState.dialogue` (`DialogueState`:
npc_id, transcript, turn count) and is JSON-serialisable like the rest
of the state. NPC schedule ticks are paused while a dialogue is active
so the conversation partner cannot walk away mid-sentence.

### 2. LLM-summarised memories

When a conversation ends, one extra LLM call condenses the transcript
into a single first-person memory sentence appended to `npc.memory`
(trimmed to `NPC_MEMORY_LENGTH`) and to the event log (so the narrator
sees it too). If the summary call fails or returns nothing, a rule-based
fallback (clipped first player line) is used so the game never crashes
on conversation end. The summariser is called through the injected
`LLMClient`, so tests mock it like every other LLM path.

### 3. Shared worldview prompt + per-NPC knowledge fields

`prompts.FARM_FOLK_WORLDVIEW` is a shared block encoding the
constraints: never travelled past the market, ignorant of the wider
world (admit it or repeat hearsay, steer talk back to familiar things),
confident about farm matters, brief answers, fair/harvest on the mind.

Two new structured `NPC` fields individualise it:

- `knowledge: list[str]` — domains this NPC speaks on with authority
- `preoccupation: str` — the chore currently on their mind, used both
  for flavour and for the wrap-up line

### 4. Keyword-triggered world facts (RAG-lite)

Shared lore (fair date, harvest outlook, neighbours) lives in
`GameState.world_facts` as `WorldFact(topic, keywords, text)` entries.
On each dialogue turn, facts whose keywords match the player's message
are injected into the NPC system prompt for that turn only. All NPCs
therefore agree on the details, the facts can evolve during play, and
the prompt stays small when the topic doesn't come up.

## Rejected alternatives

- **Routing every dialogue turn through the narrator** — two LLM calls
  per turn and the narrator paraphrasing dialogue; rejected for latency
  and for muddying the NPC voice.
- **Full transcripts kept forever** — unbounded prompt growth; old
  chatter crowds out the persona.
- **World facts as an NPC-side tool call** — would double latency per
  turn and small local models (qwen3 on Ollama) are unreliable at tool
  calling mid-roleplay. Keyword retrieval costs zero extra calls and is
  trivially testable.
- **Prompt-only worldview (no new NPC fields)** — knowledge would be
  prose only, impossible to vary per NPC or inspect in code.

## Implementation map

| File | Change |
|---|---|
| `state.py` | `DialogueLine`, `DialogueState`, `WorldFact`; `NPC.knowledge`, `NPC.preoccupation`; `GameState.world_facts`, `GameState.dialogue` |
| `config.py` | `DIALOGUE_MAX_TURNS`, `FAREWELL_PHRASES` |
| `prompts.py` | `FARM_FOLK_WORLDVIEW`, reworked `NPC_SYSTEM_TEMPLATE`, `DIALOGUE_WRAP_UP`, `DIALOGUE_SUMMARY_SYSTEM` |
| `npc.py` | `relevant_facts`, `is_farewell`, `start_dialogue`, `dialogue_turn`, `end_dialogue`; richer `build_npc_system_prompt` (replaces one-shot `get_response`) |
| `narrator.py` | dialogue-mode routing at the top of `process_input`; `talk_to` dispatch starts a dialogue |
| `tools.py` | `record_talk` removed (superseded by summarised memories) |
| `tool_schema.py` | `talk_to` description now says it starts a conversation |
| `world.py` | knowledge/preoccupation for Aldric, Marta, Jakob; starting `world_facts` |
| `main.py` | dialogue-aware input prompt; schedule tick paused during dialogue |

## Verification checklist

- [x] `make check` passes (lint, mypy strict, tests)
- [x] No LLM calls in tests — dialogue + summary paths use mock clients
- [x] `GameState` with an active dialogue round-trips `asdict` → `json.dumps` → `json.loads`
- [x] Farewell phrase ends the conversation and writes an NPC memory
- [x] Turn cap injects the wrap-up instruction and ends the conversation
- [x] World fact injected only when the player's message matches keywords
- [x] Summary-call failure falls back to a rule-based memory line
- [x] Narrator client is not called while a dialogue is active
