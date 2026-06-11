# OpenRouter inference backend

## Problem

The game supported two backends: Groq cloud (when `GROQ_API_KEY` is set)
and a local Ollama daemon. Groq's free tier rate-limits aggressively and
its model selection is narrow; Ollama needs local hardware. OpenRouter
gives access to many providers (including Google's cheap Gemini Flash
models) behind one OpenAI-compatible API and one key, which is a better
fit for the hosted HF Space.

## Approach

Add a third backend with the highest selection priority:

1. **`fantsu/clients/openrouter_client.py`** — `OpenRouterClient`,
   mirroring `GroqClient`: an `openai.OpenAI` client pointed at
   `https://openrouter.ai/api/v1`, reading `OPENROUTER_API_KEY`, and
   normalising responses to the Ollama-style
   `{"message": {"content", "tool_calls"}}` dict the rest of the game
   expects. The inline-tool-call fallback (`_inline_tools`) is kept for
   models that emit function-call markup as plain content. The
   Groq-specific `BadRequestError` / `failed_generation` recovery is
   **not** copied — that 400-with-payload behaviour is unique to Groq.
   The module is mypy-excluded like the other clients.
2. **`fantsu/config.py`** — backend auto-selection becomes a chain:
   `OPENROUTER_API_KEY` set → OpenRouter with
   `google/gemini-2.5-flash-lite` for both narrator and NPCs; else
   `GROQ_API_KEY` set → Groq (unchanged models); else Ollama.
3. **`fantsu/main.py` / `fantsu/web.py`** — the client-construction
   branches gain an OpenRouter case ahead of Groq, mirroring the config
   chain. `web.py` keeps its lazy imports.
4. **Groq integration tests fixed for multi-key environments** — the
   live tests in `tests/test_groq_integration.py` used
   `config.NARRATOR_MODEL` / `config.NPC_MODEL`, which now resolve to
   the OpenRouter model whenever `OPENROUTER_API_KEY` is also set —
   sending `google/gemini-2.5-flash-lite` to Groq (404). Config now
   exposes per-backend constants (`GROQ_NARRATOR_MODEL`,
   `OPENROUTER_NPC_MODEL`, …) and a `groq_models` fixture pins the
   active models to Groq's for those tests. They also now **skip**
   instead of fail on Groq 429 rate-limit errors, since exhausted
   shared quota proves nothing about the code.

## Rejected alternatives

- **Routing OpenRouter through `GroqClient` with an overridable base
  URL** — would tangle Groq's error-recovery quirks into a generic
  client and make per-backend tuning awkward. A small dedicated class
  matches the existing one-file-per-backend pattern.
- **Separate narrator/NPC models on OpenRouter** — Gemini 2.5 Flash
  Lite is cheap and handles both tool use and chat well; one model
  keeps config simple. Easy to split later in `config.py`.

## Verification

- [x] `make check` passes (lint, mypy strict, full test suite — no LLM
      calls, as required)
- [x] New client is listed in the mypy `exclude` block in
      `pyproject.toml`
- [x] `config.py` precedence: OpenRouter → Groq → Ollama
- [x] `main.py` and `web.py` both construct `OpenRouterClient` when
      `OPENROUTER_API_KEY` is set
- [x] README / CLAUDE.md backend docs updated
- [x] Deployed to the HF Space `jussikuosa/fantsu` via
      `./deploy_to_hf.sh` (set `OPENROUTER_API_KEY` as a Space secret
      in the Space UI to activate the backend)
- [ ] Live smoke test against openrouter.ai — blocked in the dev
      container (host not in the network allowlist); verify on the
      Space once the secret is set
