# Fantsu

A terminal text adventure with LLM-backed NPCs. You type freely; a narrator
LLM interprets your intent and calls game tools; a second LLM call handles
NPC dialogue with per-character memory and personality.

The first scene: wake up on a medieval farmstead, get your morning task from
the landowner, and figure out how to complete it.

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download) running locally (default: `http://localhost:11434`)
- A pulled model — `mistral` is the default, `qwen3:8b` also works well

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/quosa/fantsu.git
cd fantsu
pip install -e .

# 2. Pull a model (if you haven't already)
ollama pull mistral

# 3. Play
fantsu
# or: python -m fantsu.main
```

### Changing the model

Edit `fantsu/config.py`:

```python
NARRATOR_MODEL = "mistral"   # change to e.g. "qwen3:8b", "llama3"
NPC_MODEL      = "mistral"
```

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
