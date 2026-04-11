"""Gameplay file logger.

Appends a terse record of each turn to ``fantsu.log`` in the working directory.

Format per turn::

    14:23:01  IN   look at the door
    14:23:02  CALL open_portal {"location_id": "barn"}
    14:23:02  TOOL FAIL | The wooden door is closed.
    14:23:02  CALL move_to {"location_id": "barn"}
    14:23:02  TOOL FAIL | The wooden door is closed.
    14:23:02  OUT  (no tool output) Nothing happens.
    14:23:02 ----

The logger is a module-level singleton; importing this module is enough to
activate it.  Tests that import narrator will produce log output too — that is
intentional, as it aids debugging without affecting test assertions.

# TODO: truncate / rotate fantsu.log on game start so old runs don't pile up.
"""

from __future__ import annotations

import logging
from pathlib import Path

_LOG_PATH = Path("fantsu.log")
_TRUNC = 160  # max chars per logged value before truncating


def _clip(text: str) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= _TRUNC else text[:_TRUNC] + "…"


def _setup() -> logging.Logger:
    logger = logging.getLogger("fantsu.gameplay")
    if logger.handlers:
        return logger  # already configured; avoids double-handlers on reload
    logger.setLevel(logging.DEBUG)
    try:
        handler = logging.FileHandler(_LOG_PATH, mode="a", encoding="utf-8")
    except OSError:
        # Fall back to a no-op handler if the file can't be opened.
        handler = logging.NullHandler()  # type: ignore[assignment]
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


gameplay_log = _setup()


def log_player_input(text: str) -> None:
    gameplay_log.info(" IN   %s", _clip(text))


def log_tool_call(name: str, args: str) -> None:
    gameplay_log.info(" CALL %s %s", name, _clip(args))


def log_tool_result(ok: bool, message: str) -> None:
    tag = "OK  " if ok else "FAIL"
    gameplay_log.info(" TOOL %s | %s", tag, _clip(message))


def log_llm_text(text: str) -> None:
    gameplay_log.info(" OUT  (text) %s", _clip(text))


def log_narration(text: str) -> None:
    gameplay_log.info(" OUT  (tool) %s", _clip(text))


def log_turn_end() -> None:
    gameplay_log.info("----")
