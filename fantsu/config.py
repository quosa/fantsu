import os

GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

if GROQ_API_KEY:
    NARRATOR_MODEL = "llama-3.3-70b-versatile"  # reliable tool-use support
    NPC_MODEL = "llama-3.1-8b-instant"  # fast chat model, no tool use needed
else:
    NARRATOR_MODEL = "mistral"
    NPC_MODEL = "mistral"

OLLAMA_URL = "http://localhost:11434"  # kept for ollama_client.py compatibility
TIME_PER_ROOM_ACTION = 2  # minutes advanced per room-level action
TIME_PER_ZONE_TRAVERSAL = 5  # minutes advanced per zone traversal
NPC_MEMORY_LENGTH = 10  # max entries kept in NPC memory
