# Fantsu

A terminal text adventure with LLM-backed NPCs. You type freely; a narrator
LLM interprets your intent and calls game tools; a second LLM call handles
NPC dialogue with per-character memory and personality.

The first scene: wake up on a medieval farmstead, get your morning task from
the landowner, and figure out how to complete it.

---

## Requirements

- Python 3.11+
- **Either** a free [Groq](https://console.groq.com) API key **or** [Ollama](https://ollama.com/download) running locally

The backend is selected automatically at startup:

| `GROQ_API_KEY` set? | Backend used |
|---|---|
| Yes | Groq cloud API (no local model needed) |
| No / empty | Local Ollama (`http://localhost:11434`, model: `mistral`) |

---

## Quick start

### Option A — Groq (no local GPU needed)

```bash
# 1. Get a free API key at console.groq.com, then:
export GROQ_API_KEY=gsk_...

# 2. Clone and install
git clone https://github.com/quosa/fantsu.git
cd fantsu
pip install -e .

# 3. Play
make run
```

### Option B — Local Ollama

```bash
# 1. Install Ollama and pull a model
ollama pull mistral

# 2. Clone and install
git clone https://github.com/quosa/fantsu.git
cd fantsu
pip install -e .

# 3. Play
make run
```

### Option C — Play in a browser (GitHub Codespaces)

No local installation at all. See **[docs/codespaces_plan.md](docs/codespaces_plan.md)** for the full guide. In short:

1. Add `GROQ_API_KEY` to your [Codespaces secrets](https://github.com/settings/codespaces)
2. Open this repo → **Code → Codespaces → New codespace**
3. Run `make run` in the browser terminal

---

## How to play

Type naturally. The narrator interprets your intent.

| What you want to do | Example input |
|---------------------|---------------|
| Look around | `look`, `what do I see?` |
| Move somewhere | `go to the main hall`, `head to the barn` |
| Open a door | `open the door`, `open the wooden door` |
| Pick something up | `take the bucket`, `grab the boots` |
| Wear something | `put on my boots`, `wear the boots` |
| Talk to someone | `talk to Aldric`, `ask Marta about the farm` |
| Use an item | `fill the bucket with grain`, `feed the animals` |
| Check the time | `what time is it?` |
| Quit | `quit`, `exit`, `q` |

**The starting task**: Aldric asks you to feed the goats and chickens in the
barn. You'll need to find the bucket, fill it with grain from the storehouse,
and get to the barn.

**Doors**: closed doors must be opened explicitly before you can walk through
them. Try *"open the wooden door"* then *"go to the main hall"*.

---

## Locations

```
Farmhand's Quarters → (wooden door) → Main Hall
Main Hall → (open archway) → Kitchen
Main Hall → (front door) → The Yard
The Yard → Storehouse
The Yard → (barn door) → Barn
The Yard → (farm gate) → South Road
```

---

## Known limitations (v0.1 POC)

- No save/load yet (game state is in memory only)
- Tool-call quality depends heavily on the model; larger models play better
- NPC schedules tick but NPCs don't react to being moved
- The narrator makes a single LLM call per turn and never feeds tool
  results back to the model, so the LLM's description of the world can
  drift from actual game state over time (see CLAUDE.md for details)
