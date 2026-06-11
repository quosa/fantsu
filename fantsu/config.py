import os

GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
Z_API_KEY: str = os.environ.get("Z_API_KEY", "")

# Per-backend model names. The active NARRATOR_MODEL / NPC_MODEL pair is
# picked below; integration tests address a specific backend's constants.
OPENROUTER_NARRATOR_MODEL = "google/gemini-2.5-flash-lite"  # cheap, solid tool use
OPENROUTER_NPC_MODEL = "google/gemini-2.5-flash-lite"
GROQ_NARRATOR_MODEL = "llama-3.3-70b-versatile"  # reliable tool-use support
GROQ_NPC_MODEL = "llama-3.1-8b-instant"  # fast chat model, no tool use needed
OLLAMA_MODEL = "qwen3:8b"

if OPENROUTER_API_KEY:
    NARRATOR_MODEL = OPENROUTER_NARRATOR_MODEL
    NPC_MODEL = OPENROUTER_NPC_MODEL
elif GROQ_API_KEY:
    NARRATOR_MODEL = GROQ_NARRATOR_MODEL
    NPC_MODEL = GROQ_NPC_MODEL
else:
    NARRATOR_MODEL = OLLAMA_MODEL
    NPC_MODEL = OLLAMA_MODEL

OLLAMA_URL = "http://localhost:11434"  # kept for ollama_client.py compatibility
TIME_PER_ROOM_ACTION = 2  # minutes advanced per room-level action
TIME_PER_ZONE_TRAVERSAL = 5  # minutes advanced per zone traversal
NPC_MEMORY_LENGTH = 10  # max entries kept in NPC memory

DIALOGUE_MAX_TURNS = 6  # exchanges before the NPC excuses itself to its chores
# Word-boundary matched against player input; any hit ends the conversation.
FAREWELL_PHRASES = (
    "goodbye",
    "farewell",
    "bye",
    "see you",
    "never mind",
    "i must go",
    "must be off",
    "stop talking",
    "leave you to it",
)
