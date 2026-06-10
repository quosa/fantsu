"""Hardcoded narrative text — no logic, no LLM, no I/O.

Kept separate from main.py so both the CLI and the web UI can reuse these
without importing the LLM client modules.
"""

OPENING_SCENE = """\
You wake to a sharp knock at your door.

"Up with you!" Aldric's voice, gruff but not unkind. "The animals haven't
been fed. Take the bucket from the storehouse, fill it with grain, and see
to the goats and chickens in the barn. There's bread in the kitchen when
you're done."

His footsteps retreat toward the main hall.
"""

ENDING_TEXT = (
    "Aldric finds you as you leave the barn. He looks at the "
    "contented animals and gives a rare nod.\n"
    '"Good work. There\'s bread and butter waiting in the kitchen."\n'
    "\nYou have completed all tasks. Well done."
)
