# Playing Fantsu via GitHub Codespaces

## Overview

Fantsu runs entirely in a browser terminal using GitHub Codespaces + Groq's free cloud LLM API. No local installation, no Ollama, no GPU required.

---

## One-time setup

### 1. Get a free Groq API key

1. Go to `console.groq.com` and sign up (no credit card needed)
2. Create an API key under **API Keys**
3. Copy the key (starts with `gsk_...`)

### 2. Add the key as a Codespaces secret

1. Go to **GitHub → Settings → Codespaces → Secrets**
2. Click **New secret**
   - Name: `GROQ_API_KEY`
   - Value: your `gsk_...` key
3. Under **Repository access**, add `quosa/fantsu`

You only do this once — the key is injected automatically into every Codespace.

---

## Playing the game

1. Go to `github.com/quosa/fantsu`
2. Click the green **Code** button → **Codespaces** tab → **Create codespace on main** (or your branch)
3. Wait ~30 seconds for the devcontainer to build and run `pip install -e '.[dev]'`
4. In the terminal at the bottom:
   ```
   make run
   ```
5. Type your actions at the `> ` prompt — e.g.:
   ```
   > look around
   > go to the storehouse
   > talk to Aldric
   ```
6. Press `Ctrl+C` or type `quit` to exit

---

## How it works

| Component | What it does |
|---|---|
| `.devcontainer/devcontainer.json` | Tells Codespaces to use Python 3.11 and install dependencies on startup |
| `fantsu/groq_client.py` | Calls Groq's API (OpenAI-compatible) and normalises the response for the game |
| `fantsu/config.py` | Sets `NARRATOR_MODEL` to a tool-use-optimised model, reads `GROQ_API_KEY` from env |
| `GROQ_API_KEY` secret | Injected as an env var by Codespaces — no hardcoded keys |

**LLM calls per player action**: 2 — one for the narrator (interprets your input, calls game tools), one for NPC dialogue when you talk to a character.

---

## Free tier limits

- **Groq**: 500k tokens/day, 14,400 requests/day on `llama-3.1-8b-instant` — plenty for casual play
- **Codespaces**: 60 core-hours/month on the free plan (a 2-core machine = ~30 h of active use)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AuthenticationError` from Groq | Check `echo $GROQ_API_KEY` in the terminal — if empty, the secret isn't set or not granted to this repo |
| Slow first response | Normal — cold start. Subsequent turns are fast |
| `ModuleNotFoundError: openai` | Run `pip install -e '.[dev]'` manually |
