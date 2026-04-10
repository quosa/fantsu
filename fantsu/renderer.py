"""Pure string formatting — no I/O, no side effects."""

from fantsu.state import GameState


def format_time(minutes: int) -> str:
    """Convert minutes-since-dawn into a human-readable time label."""
    labels = [
        (0, "just before dawn"),
        (30, "early morning"),
        (90, "mid morning"),
        (180, "late morning"),
        (240, "around noon"),
        (360, "afternoon"),
        (480, "late afternoon"),
        (600, "evening"),
        (720, "night"),
    ]
    result = "night"
    for threshold, label in labels:
        if minutes >= threshold:
            result = label
    return result


def describe_location(state: GameState) -> str:
    """Render the player's current location as readable text."""
    loc = state.locations[state.player_location_id]

    lines: list[str] = []

    # Heading
    lines.append(f"[ {loc.name} ]")
    lines.append(loc.description_template)

    # Exits
    exit_parts: list[str] = []
    for ex in loc.exits:
        if ex.portal:
            exit_parts.append(
                f"{ex.label}: {ex.portal.description} ({ex.portal.state})"
            )
        else:
            exit_parts.append(ex.label)
    if exit_parts:
        lines.append("Exits: " + ", ".join(exit_parts))

    # Items on the ground
    item_names = [state.items[i].name for i in loc.item_ids if i in state.items]
    if item_names:
        lines.append("You see: " + ", ".join(item_names))

    # NPCs present
    npc_names = [state.npcs[n].name for n in loc.npc_ids if n in state.npcs]
    if npc_names:
        lines.append("Here: " + ", ".join(npc_names))

    # Zone features
    if loc.type == "zone" and loc.features:
        feat_names = [f.name for f in loc.features]
        lines.append("Nearby: " + ", ".join(feat_names))

    return "\n".join(lines)


def describe_inventory(state: GameState) -> str:
    """Render the player's inventory."""
    if not state.player_inventory:
        return "You are carrying nothing."
    names = [
        state.items[i].name for i in state.player_inventory if i in state.items
    ]
    return "You are carrying: " + ", ".join(names)
