# Web hosting plan — play Fantsu online

## Problem

Fantsu is a terminal program (`python -m fantsu.main`) that reads `input()` and
prints to stdout. The goal: let the author (and friends) play it from a browser,
ideally on a free/simple host, without everyone installing Python or running a
local model.

## The decisive constraint

Every turn calls a live LLM backend: Groq's cloud API (needs a secret
`GROQ_API_KEY`), Z.ai, or a local Ollama daemon. That means the app needs a
**server-side runtime that can hold a secret** — which rules out the obvious
"simple" option:

- **GitHub Pages — rejected.** Static hosting only. It can't run Python and
  can't safely store an API key. The only way to run Python there is Pyodide
  (Python→WASM in the browser), but then the key would be public, browser→Groq
  calls would hit CORS, and `localhost` Ollama is unreachable. Not worth a
  bring-your-own-key WASM rewrite.

## Approach chosen

A small **Gradio chat UI** wrapping `narrator.process_input`, deployed to
**Hugging Face Spaces** with `GROQ_API_KEY` stored as a Space secret.

Why this combination:

- `process_input(player_input, state) -> (narration, state)` is already cleanly
  separated from I/O, so the wrapper is thin.
- Gradio gives a chat interface (nicer than a raw terminal) with almost no UI
  code, and per-browser-session state out of the box (`gr.State`), so multiple
  people get independent games.
- Hugging Face Spaces is a free container host with first-class secret storage —
  no Dockerfile, no infra, public URL.

### What was rejected and why

- **Browser terminal (ttyd / gotty / pyxterm.js / terminado).** Zero game-code
  changes — serve the existing CLI as a real terminal in the browser. Great for
  a 10-minute demo, but a raw terminal is a worse experience than chat and gives
  no path to save/load. Kept in pocket as the fastest fallback.
- **FastAPI + WebSocket custom UI.** Most flexible, but more code to write and
  maintain than Gradio for no benefit at this stage.
- **GitHub Pages / Pyodide.** Rejected for the key + CORS reasons above.
- **Local Ollama backend for the hosted app.** No key needed, but requires a GPU
  box; small models on free hosts (or a Pi) are too slow. Groq cloud is simpler
  and free.

## Implementation

New/changed files:

- `fantsu/scenes.py` — extracted `OPENING_SCENE` / `ENDING_TEXT` constants
  (logic-free) so both the CLI and the web UI can import them without pulling in
  the LLM client modules. `main.py` now imports from here.
- `fantsu/web.py` — the wrapper. Split in two:
  - Pure, framework-free session logic (`Session`, `new_session`, `intro_text`,
    `play_turn`) that mirrors `main.main`'s loop body — run the narrator,
    announce completed tasks, show the ending, tick NPCs. Unit-tested with mock
    LLM clients, no gradio needed.
  - Gradio glue (`build_app`, `main`) that imports `gradio` lazily, so
    `make check` and the test suite never need it. Each browser session gets its
    own `Session` via `gr.State`.
- `app.py` — Hugging Face Spaces entry point (`demo = build_app()`).
- `requirements.txt` — runtime deps for the Space (`ollama`, `openai`, `gradio`).
- `pyproject.toml` — optional `web` extra (`gradio>=5.0`); `fantsu/web.py`
  excluded from mypy (consistent with `main.py`); `gradio` added to mypy's
  ignore-missing-imports overrides.
- `tests/test_web.py` — covers the pure session helpers with mock clients.

### Run locally

```bash
pip install -e ".[web]"
GROQ_API_KEY=gsk_... python -m fantsu.web      # http://localhost:7860
```

### Deploy to Hugging Face Spaces

1. Create a new Space: **SDK = Gradio**, hardware = free CPU basic.
2. Push this repo's contents to the Space's git remote (or connect the GitHub
   repo). The Space needs `app.py` + `requirements.txt` at the root — both are
   provided.
3. The Space's own `README.md` must carry the Spaces YAML header. Use:

   ```yaml
   ---
   title: Fantsu
   emoji: 🌾
   colorFrom: green
   colorTo: yellow
   sdk: gradio
   sdk_version: "5.49.1"   # or current; must match a version that defaults to
                           # the messages chat format
   app_file: app.py
   pinned: false
   ---
   ```

4. In **Settings → Variables and secrets**, add a secret `GROQ_API_KEY`.
5. Open the Space URL and play. Each visitor gets an independent game.

### Alternative hosts (same artifact)

- **Fly.io / Render / Railway** — wrap with a Dockerfile running
  `python -m fantsu.web` (exposes port 7860); set `GROQ_API_KEY` as a secret.
- **Home Raspberry Pi** — `pip install -e ".[web]"` + `python -m fantsu.web`,
  exposed via a Cloudflare Tunnel or Tailscale (no port-forwarding needed).

## Verification checklist

- [x] `make check` clean (ruff + mypy + tests; mypy verified with the project
      interpreter via `mypy --python-executable`).
- [x] `tests/test_web.py` passes with mock LLM clients — no network calls.
- [x] `build_app()` constructs a Gradio `Blocks` app (smoke-tested on gradio 6).
- [x] `python -m fantsu.main` (CLI) still works after the `scenes.py` extraction.
- [ ] Deployed Space loads, shows the opening scene, and a full turn round-trips
      against Groq (requires a live key — do once after first deploy).
```
