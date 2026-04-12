"""Game action implementations.

Each public function takes a GameState (mutated in place) and returns a
ToolResult.  No LLM calls happen here — tools are pure game logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fantsu import config
from fantsu.renderer import describe_location, format_time
from fantsu.state import GameState


@dataclass
class ToolResult:
    ok: bool
    message: str


# ------------------------------------------------------------------ #
# move_to                                                              #
# ------------------------------------------------------------------ #


def move_to(location_id: str, state: GameState) -> ToolResult:
    """Move the player to a connected location."""
    current = state.locations.get(state.player_location_id)
    if current is None:
        return ToolResult(ok=False, message="You are nowhere. Something is wrong.")

    # Find a matching exit
    target_exit = next(
        (ex for ex in current.exits if ex.destination == location_id), None
    )
    if target_exit is None:
        return ToolResult(
            ok=False,
            message=f"There is no way to reach '{location_id}' from here.",
        )

    # Check portal state
    if target_exit.portal is not None and target_exit.portal.state != "open":
        portal_desc = target_exit.portal.description
        portal_state = target_exit.portal.state
        return ToolResult(
            ok=False,
            message=f"The {portal_desc} is {portal_state}.",
        )

    # Move the player
    state.player_location_id = location_id

    # Advance time
    dest_loc = state.locations.get(location_id)
    loc_type = dest_loc.type if dest_loc else "room"
    if loc_type == "zone":
        state.time += config.TIME_PER_ZONE_TRAVERSAL
    else:
        state.time += config.TIME_PER_ROOM_ACTION

    state.event_log.append(f"Player moved to {location_id}.")
    return ToolResult(ok=True, message=describe_location(state))


# ------------------------------------------------------------------ #
# open_portal                                                          #
# ------------------------------------------------------------------ #


def open_portal(location_id: str, state: GameState) -> ToolResult:
    """Open the portal on the exit leading to location_id."""
    current = state.locations.get(state.player_location_id)
    if current is None:
        return ToolResult(ok=False, message="Current location not found.")

    target_exit = next(
        (ex for ex in current.exits if ex.destination == location_id), None
    )
    if target_exit is None:
        return ToolResult(
            ok=False,
            message=f"No exit leads to '{location_id}' from here.",
        )
    if target_exit.portal is None:
        return ToolResult(ok=False, message="There is nothing to open that way.")

    portal = target_exit.portal
    if portal.state == "locked":
        return ToolResult(
            ok=False, message=f"The {portal.description} is locked."
        )
    if portal.state == "open":
        return ToolResult(
            ok=True, message=f"The {portal.description} is already open."
        )

    portal.state = "open"
    state.event_log.append(f"Player opened {portal.description} to {location_id}.")
    return ToolResult(ok=True, message=f"You open the {portal.description}.")


# ------------------------------------------------------------------ #
# close_portal                                                         #
# ------------------------------------------------------------------ #


def close_portal(location_id: str, state: GameState) -> ToolResult:
    """Close the portal on the exit leading to location_id."""
    current = state.locations.get(state.player_location_id)
    if current is None:
        return ToolResult(ok=False, message="Current location not found.")

    target_exit = next(
        (ex for ex in current.exits if ex.destination == location_id), None
    )
    if target_exit is None:
        return ToolResult(
            ok=False,
            message=f"No exit leads to '{location_id}' from here.",
        )
    if target_exit.portal is None:
        return ToolResult(ok=False, message="There is nothing to close that way.")

    portal = target_exit.portal
    if portal.state != "open":
        return ToolResult(
            ok=True, message=f"The {portal.description} is already closed."
        )

    portal.state = "closed"
    state.event_log.append(f"Player closed {portal.description} to {location_id}.")
    return ToolResult(ok=True, message=f"You close the {portal.description}.")


# ------------------------------------------------------------------ #
# take_item                                                            #
# ------------------------------------------------------------------ #


def take_item(item_id: str, state: GameState) -> ToolResult:
    """Pick up a portable item from the current location."""
    current = state.locations.get(state.player_location_id)
    if current is None:
        return ToolResult(ok=False, message="Current location not found.")

    if item_id not in current.item_ids:
        return ToolResult(ok=False, message=f"There is no '{item_id}' here.")

    item = state.items.get(item_id)
    if item is None:
        return ToolResult(ok=False, message=f"Item '{item_id}' does not exist.")

    if not item.portable:
        return ToolResult(ok=False, message=f"You cannot pick up {item.name}.")

    current.item_ids.remove(item_id)
    state.player_inventory.append(item_id)
    state.event_log.append(f"Player took {item_id}.")
    return ToolResult(ok=True, message=f"You pick up the {item.name}.")


# ------------------------------------------------------------------ #
# drop_item                                                            #
# ------------------------------------------------------------------ #


def drop_item(item_id: str, state: GameState) -> ToolResult:
    """Drop an item from inventory into the current location."""
    if item_id not in state.player_inventory:
        return ToolResult(ok=False, message=f"You are not carrying '{item_id}'.")

    current = state.locations.get(state.player_location_id)
    if current is None:
        return ToolResult(ok=False, message="Current location not found.")

    state.player_inventory.remove(item_id)
    current.item_ids.append(item_id)

    item = state.items.get(item_id)
    name = item.name if item else item_id
    state.event_log.append(f"Player dropped {item_id}.")
    return ToolResult(ok=True, message=f"You set down the {name}.")


# ------------------------------------------------------------------ #
# use_item                                                             #
# ------------------------------------------------------------------ #


def _fill_bucket(state: GameState) -> ToolResult:
    """Fill the bucket from the feed_sack."""
    bucket = state.items.get("bucket")
    if bucket is None:
        return ToolResult(ok=False, message="Bucket not found.")
    if bucket.state.get("filled"):
        return ToolResult(ok=True, message="The bucket is already full.")
    bucket.state["filled"] = True
    state.event_log.append("Player filled the bucket.")
    return ToolResult(
        ok=True, message="You scoop grain into the bucket. It is now full."
    )


def _wear_boots(state: GameState) -> ToolResult:
    """Put on or acknowledge the worn boots."""
    boots = state.items.get("player_boots")
    if boots is None or "player_boots" not in state.player_inventory:
        return ToolResult(ok=False, message="You need to be holding the boots.")
    if boots.state.get("worn"):
        return ToolResult(ok=True, message="You are already wearing your boots.")
    boots.state["worn"] = True
    state.event_log.append("Player put on boots.")
    return ToolResult(
        ok=True,
        message="You pull on your worn leather boots. They fit like old friends.",
    )


def _feed_animals(state: GameState) -> ToolResult:
    """Feed the animals with a filled bucket (must be in barn)."""
    if state.player_location_id != "barn":
        return ToolResult(
            ok=False, message="There are no animals to feed here."
        )
    bucket = state.items.get("bucket")
    if bucket is None or "bucket" not in state.player_inventory:
        return ToolResult(ok=False, message="You need to be holding the bucket.")
    if not bucket.state.get("filled"):
        return ToolResult(
            ok=False,
            message="The bucket is empty. Fill it with grain first.",
        )

    # Complete the task
    bucket.state["filled"] = False
    for task in state.tasks:
        if task.id == "feed_animals" and not task.completed:
            task.completed = True

    state.event_log.append("Player fed the animals.")
    return ToolResult(
        ok=True,
        message=(
            "You pour the grain into the feeding trough. "
            "The goats and chickens jostle eagerly around it."
        ),
    )


def _empty_bucket(state: GameState) -> ToolResult:
    """Spill the bucket contents on the floor."""
    bucket = state.items.get("bucket")
    if bucket is None:
        return ToolResult(ok=False, message="Bucket not found.")
    if not bucket.state.get("filled"):
        return ToolResult(ok=False, message="The bucket is already empty.")
    bucket.state["filled"] = False
    state.event_log.append("Player emptied the bucket.")
    return ToolResult(
        ok=True, message="You tip the bucket. Grain spills across the floor."
    )


# Dispatch table: (item_id, target_id) → handler
_ITEM_HANDLERS: dict[tuple[str, str], Callable[[GameState], ToolResult]] = {
    ("bucket", "feed_sack"): _fill_bucket,
    # empty the bucket
    ("bucket", "floor"):  _empty_bucket,
    ("bucket", "ground"): _empty_bucket,
    ("bucket", "spill"):  _empty_bucket,
    # feed animals — accept any natural target the LLM might choose
    ("bucket", "animals"): _feed_animals,
    ("bucket", "chickens"): _feed_animals,
    ("bucket", "goats"): _feed_animals,
    ("bucket", "livestock"): _feed_animals,
    ("bucket", "trough"): _feed_animals,
    # boots — accept any natural target the LLM might choose
    ("player_boots", "self"): _wear_boots,
    ("player_boots", "player"): _wear_boots,
    ("player_boots", "feet"): _wear_boots,
    ("player_boots", "player_boots"): _wear_boots,
}


def use_item(item_id: str, target_id: str, state: GameState) -> ToolResult:
    """Use an item on a target."""
    current = state.locations.get(state.player_location_id)
    in_inventory = item_id in state.player_inventory
    in_location = current is not None and item_id in current.item_ids
    if not in_inventory and not in_location:
        return ToolResult(ok=False, message=f"You don't see '{item_id}' here.")

    handler = _ITEM_HANDLERS.get((item_id, target_id))
    if handler is None:
        item = state.items.get(item_id)
        name = item.name if item else item_id
        return ToolResult(
            ok=False,
            message=f"You cannot use the {name} on '{target_id}'.",
        )

    return handler(state)


# ------------------------------------------------------------------ #
# talk_to                                                              #
# ------------------------------------------------------------------ #


def validate_talk_to(npc_id: str, state: GameState) -> ToolResult | None:
    """Return an error ToolResult if the NPC cannot be talked to, else None."""
    npc = state.npcs.get(npc_id)
    if npc is None:
        return ToolResult(ok=False, message=f"There is no one called '{npc_id}'.")
    if npc.location_id != state.player_location_id:
        return ToolResult(
            ok=False,
            message=f"{npc.name} is not here.",
        )
    return None


def record_talk(npc_id: str, dialogue: str, state: GameState) -> None:
    """Append a dialogue summary to NPC memory and the event log."""
    npc = state.npcs[npc_id]
    summary = f'Player spoke to {npc.name}: "{dialogue[:80]}"'
    npc.memory.append(summary)
    if len(npc.memory) > config.NPC_MEMORY_LENGTH:
        npc.memory = npc.memory[-config.NPC_MEMORY_LENGTH :]
    state.event_log.append(summary)


# ------------------------------------------------------------------ #
# look                                                                 #
# ------------------------------------------------------------------ #


def look(state: GameState) -> ToolResult:
    """Describe the current location. Does not advance time."""
    return ToolResult(ok=True, message=describe_location(state))


# ------------------------------------------------------------------ #
# get_time                                                             #
# ------------------------------------------------------------------ #


def get_time(state: GameState) -> ToolResult:
    """Return the current in-game time as a human-readable string."""
    return ToolResult(ok=True, message=f"It is {format_time(state.time)}.")
