# Farmstead — POC Game Plan

A text-adventure with LLM-backed NPCs and a natural language command interface.
Player types freely; a narrator LLM interprets intent and calls game tools;
a second LLM call handles NPC dialogue with per-NPC context.

---

## Tech Stack

- **Python 3.11+**
- **Ollama** (local) via `ollama` Python library
- **Model**: `mistral` or `llama3` — configurable constant at top of config file
- **No game framework** — pure Python, terminal only for POC
- **No database** — game state is a single in-memory dataclass, JSON-serialisable for save/load later

---

## Project Structure

```
farmstead/
  main.py            # game loop — input → LLM → tools → narrate → print
  config.py          # model name, ollama URL, game constants
  state.py           # all dataclasses: GameState, Location, Zone, NPC, Item, Portal, Feature, Task
  world.py           # factory: builds the starting farmhouse world
  tools.py           # all tool implementations (move, take, talk, etc.)
  tool_schema.py     # tool definitions in Ollama/OpenAI tool-call format
  npc.py             # NPC LLM call: builds per-NPC prompt, calls ollama, returns dialogue
  narrator.py        # narrator LLM call: builds context prompt, calls ollama with tools
  renderer.py        # formats GameState into readable text for the player
  prompts.py         # all system prompt strings, kept separate for easy tuning
```

---

## Data Model (`state.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class Portal:
    destination: str                        # location id
    description: str                        # "heavy oak door", "wooden gate"
    state: Literal["open", "closed", "locked"] = "closed"
    locked_by: str | None = None            # item id of key, if any

@dataclass
class Exit:
    destination: str                        # location id
    label: str                              # "north", "to the barn"
    portal: Portal | None = None            # None = walk straight through

@dataclass
class Feature:
    id: str
    name: str                               # "the lake", "dense woods"
    description: str
    enterable: bool = False
    destination: str | None = None          # location id if enterable

@dataclass
class Location:
    id: str
    name: str
    type: Literal["room", "zone"]
    description_template: str              # plain text, rendered by renderer
    exits: list[Exit] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)
    npc_ids: list[str] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)   # zones mainly

@dataclass
class Item:
    id: str
    name: str
    description: str
    portable: bool = True
    state: dict = field(default_factory=dict)   # {"filled": False} etc.

@dataclass
class ScheduleEntry:
    start_time: int         # minutes since dawn (0 = dawn, 120 = 2hrs after dawn)
    location_id: str

@dataclass
class NPC:
    id: str
    name: str
    occupation: str
    location_id: str
    schedule: list[ScheduleEntry] = field(default_factory=list)
    relationships: dict[str, str] = field(default_factory=dict)  # npc_id -> role
    memory: list[str] = field(default_factory=list)              # last N events
    profile: str = ""                                            # LLM system prompt fragment
    disposition: str = "neutral"                                 # toward player

@dataclass
class Task:
    id: str
    description: str
    giver_id: str                           # npc id
    completed: bool = False
    completion_check: str = ""             # plain english, LLM or code checks this

@dataclass
class GameState:
    time: int = 0                           # minutes since dawn
    player_location_id: str = ""
    player_inventory: list[str] = field(default_factory=list)
    locations: dict[str, Location] = field(default_factory=dict)
    npcs: dict[str, NPC] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
```

---

## The Starting World (`world.py`)

Build exactly this scene — no more for the POC.

### Locations

| id | name | type |
|----|------|------|
| `farmhand_quarters` | Farmhand's Quarters | room |
| `main_hall` | Main Hall | room |
| `kitchen` | Kitchen | room |
| `yard` | The Yard | zone |
| `storehouse` | Storehouse | room |
| `barn` | Barn | room |

### Exits / Portals

```
farmhand_quarters → main_hall      portal: "wooden door" (closed)
main_hall → kitchen                exit: "open archway" (no portal)
main_hall → yard                   portal: "front door" (open)
yard → storehouse                  exit: direct, no portal
yard → barn                        portal: "barn door" (closed)
yard → road_south                  portal: "farm gate" (latched/closed)
```

`road_south` is a minimal Zone with features: woods (west), open fields (east). Not needed for the task but shows the pattern.

### NPCs

**Master Aldric** (`aldric`)
- occupation: farmer / landowner
- starts in: `main_hall`
- schedule: dawn→main_hall, mid-morning→yard, noon→kitchen, afternoon→yard
- profile: stern but fair, worried about the harvest, treats farmhands decently
- relationships: `marta`=wife, `player`=hired hand
- memory: [] (starts empty)
- opening line (hardcoded, not LLM): knocks on player door, gives the task

**Marta** (`marta`)
- occupation: farmer's wife
- starts in: `kitchen`
- schedule: dawn→kitchen, morning→yard, midday→kitchen
- profile: warm, gossipy, knows everything that happens on the farm
- relationships: `aldric`=husband

**Jakob** (`jakob`)
- occupation: farmhand (senior)
- starts in: `farmhand_quarters`
- schedule: dawn→farmhand_quarters, early-morning→barn, midday→yard
- profile: taciturn, experienced, slightly resentful of new hires
- relationships: `player`=colleague (wary)

### Items

| id | name | portable | initial location | state |
|----|------|----------|-----------------|-------|
| `bucket` | wooden bucket | yes | storehouse | `{"filled": false}` |
| `feed_sack` | sack of grain | no | storehouse | {} |
| `pitchfork` | pitchfork | yes | barn | {} |
| `player_boots` | worn boots | yes | farmhand_quarters | {} |

### Task

```
id: feed_animals
description: "Feed the goats and chickens in the barn"
giver_id: aldric
completion_check: bucket filled AND use_item(bucket, animals) called in barn
```

---

## Tools (`tools.py` + `tool_schema.py`)

### Tool list

```python
move_to(location_id: str)
open_portal(location_id: str, direction: str)
take_item(item_id: str)
drop_item(item_id: str)
use_item(item_id: str, target_id: str)
talk_to(npc_id: str, message: str)
look()
get_time()
```

### Tool implementations (key ones)

**`move_to`**
- Check exit exists from current location
- If portal on exit: check portal state is "open", else return error "the door is closed"
- Update `state.player_location_id`
- Advance time by `traversal_time` (default 2 min rooms, 5 min zones)
- Append to event_log
- Return new location description

**`open_portal`**
- Find portal on given exit
- If locked: return "it's locked"
- Set portal.state = "open"
- Append to event_log
- Return "you open the [description]"

**`take_item`**
- Check item is in current location and portable=True
- Move item_id from location.item_ids to player_inventory
- Append to event_log
- Return confirmation

**`use_item`**
- Flexible: match item_id + target_id to a handler
- Key cases for POC:
  - `bucket` + `feed_sack` → set bucket.state["filled"]=True, return "you fill the bucket"
  - `bucket` + `animals` (special target, valid only in barn) → mark task complete if bucket filled
- Append to event_log
- Return result string

**`talk_to`**
- Validate npc is in same location as player
- Call `npc.get_response(npc_id, message, state)` → returns dialogue string
- Append dialogue summary to npc.memory and event_log
- Return dialogue string

**`look`**
- Return `renderer.describe_location(state)`
- No time advance

**`get_time`**
- Return formatted time string: "Early morning, about two hours after dawn"

---

## NPC Dialogue (`npc.py`)

```python
def get_response(npc_id: str, player_message: str, state: GameState) -> str:
    npc = state.npcs[npc_id]
    
    system = f"""
You are {npc.name}, a {npc.occupation} on a medieval farm.
{npc.profile}

Current time: {format_time(state.time)}
Your location: {state.locations[npc.location_id].name}
People nearby: {nearby_npc_names(npc, state)}
Your recent memories: {chr(10).join(npc.memory[-5:])}

Stay in character. Speak naturally, not in modern idiom.
Keep responses to 2-4 sentences unless the player asks something complex.
You may hint at tasks, rumours, or needs — but do not break character.
"""
    
    response = ollama.chat(
        model=config.NPC_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": player_message}
        ]
    )
    return response["message"]["content"]
```

---

## Narrator LLM (`narrator.py`)

Called once per player input. Receives full context, calls tools, returns narration.

```python
def process_input(player_input: str, state: GameState) -> tuple[str, GameState]:
    context = build_context(state)
    
    messages = [
        {"role": "system", "content": prompts.NARRATOR_SYSTEM},
        {"role": "user", "content": f"{context}\n\nPlayer: {player_input}"}
    ]
    
    response = ollama.chat(
        model=config.NARRATOR_MODEL,
        messages=messages,
        tools=tool_schema.ALL_TOOLS
    )
    
    # process tool calls, mutate state, collect results
    narration = execute_tool_calls(response, state)
    return narration, state
```

### Narrator system prompt (in `prompts.py`)

```
You are the narrator of a medieval text adventure. 
Interpret the player's intent and call the appropriate game tools.
Describe results in second person, past tense, 2-3 sentences.
Be atmospheric but brief. Do not invent facts not in the game state.
If the player tries something impossible, call no tools and explain why briefly.
```

---

## Renderer (`renderer.py`)

```python
def describe_location(state: GameState) -> str:
    loc = state.locations[state.player_location_id]
    
    # base description
    text = loc.description_template + "\n"
    
    # exits
    exit_lines = []
    for exit in loc.exits:
        if exit.portal:
            exit_lines.append(f"{exit.label}: {exit.portal.description} ({exit.portal.state})")
        else:
            exit_lines.append(exit.label)
    if exit_lines:
        text += "Exits: " + ", ".join(exit_lines) + "\n"
    
    # items
    items = [state.items[i].name for i in loc.item_ids]
    if items:
        text += "You see: " + ", ".join(items) + "\n"
    
    # npcs
    npcs = [state.npcs[n].name for n in loc.npc_ids]
    if npcs:
        text += "Here: " + ", ".join(npcs) + "\n"
    
    # zone features
    if loc.type == "zone" and loc.features:
        feat_lines = [f.name for f in loc.features]
        text += "Nearby: " + ", ".join(feat_lines) + "\n"
    
    return text.strip()

def format_time(minutes: int) -> str:
    labels = [
        (0,   "just before dawn"),
        (30,  "early morning"),
        (90,  "mid morning"),
        (180, "late morning"),
        (240, "around noon"),
        (360, "afternoon"),
        (480, "late afternoon"),
        (600, "evening"),
        (720, "night"),
    ]
    for threshold, label in reversed(labels):
        if minutes >= threshold:
            return label
    return "night"
```

---

## Main Game Loop (`main.py`)

```python
def main():
    state = world.build()
    
    # opening scene — hardcoded, no LLM needed
    print(opening_scene())         # Aldric knocks, gives task
    print(renderer.describe_location(state))
    
    while True:
        try:
            player_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFarewell.")
            break
        
        if not player_input:
            continue
        if player_input.lower() in ("quit", "exit"):
            break
        
        narration, state = narrator.process_input(player_input, state)
        print("\n" + narration)
        
        # check task completion
        for task in state.tasks:
            if not task.completed and check_task(task, state):
                task.completed = True
                print(f"\n[Task complete: {task.description}]")
        
        # NPC schedule tick
        world.tick_npcs(state)
```

---

## NPC Schedule Tick

After each player action, advance NPCs to their correct location for current time:

```python
def tick_npcs(state: GameState):
    for npc in state.npcs.values():
        target = current_schedule_location(npc, state.time)
        if target and target != npc.location_id:
            # remove from old location npc list, add to new
            state.locations[npc.location_id].npc_ids.remove(npc.id)
            npc.location_id = target
            state.locations[target].npc_ids.append(npc.id)
```

---

## Config (`config.py`)

```python
NARRATOR_MODEL = "mistral"
NPC_MODEL = "mistral"
OLLAMA_URL = "http://localhost:11434"
TIME_PER_ROOM_ACTION = 2      # minutes
TIME_PER_ZONE_TRAVERSAL = 5   # minutes
NPC_MEMORY_LENGTH = 10        # entries kept
```

---

## Build Order

Work in this order, confirm each step runs before moving on:

1. **`state.py`** — all dataclasses, no logic
2. **`world.py`** — hardcoded farmhouse, `build()` returns a valid `GameState`
3. **`renderer.py`** — `describe_location()` prints something readable
4. **`main.py` skeleton** — loop with hardcoded echo, no LLM yet
5. **`tools.py`** — implement all tools against real state, test with direct calls
6. **`tool_schema.py`** — tool definitions in Ollama format
7. **`npc.py`** — single NPC call with profile context, test with Aldric
8. **`narrator.py`** — full narrator loop with tool calls
9. **Wire `main.py`** — replace echo with narrator, play through the feeding task end to end
10. **`world.tick_npcs`** — NPC movement, verify Jakob moves to barn at correct time

---

## POC Done When

- Player can wake up, talk to Aldric (LLM responds in character)
- Player can navigate all 6 locations
- Player can pick up bucket, fill it, carry it to barn, feed animals
- Task completes and is acknowledged
- At least one other NPC (Marta or Jakob) responds meaningfully via LLM when talked to
- NPCs are in correct locations based on time of day
