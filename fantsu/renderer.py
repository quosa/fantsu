"""Pure string formatting — no I/O, no side effects."""

from fantsu.state import Container, GameState, Item


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


def _item_label(item: Item) -> str:
    """Return the item name with any active state annotations."""
    notes = [label for key, label in item.state_labels.items() if item.state.get(key)]
    return f"{item.name} ({', '.join(notes)})" if notes else item.name


def _container_label(container: Container) -> str:
    """Return container name with state and contents when open."""
    if container.state == "open" and container.item_ids:
        # List contents by name (best-effort; ids without matching items are skipped)
        return f"{container.name} ({container.state})"
    return f"{container.name} ({container.state})"


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
        if ex.door_id is not None:
            door = state.doors.get(ex.door_id)
            if door is not None:
                exit_parts.append(
                    f"{ex.label}: {door.description} ({door.state})"
                )
            else:
                exit_parts.append(ex.label)
        else:
            exit_parts.append(ex.label)
    if exit_parts:
        lines.append("Exits: " + ", ".join(exit_parts))

    # Items and containers merged into one "You see:" line
    visible: list[str] = []
    for i in loc.item_ids:
        item = state.items.get(i)
        if item is not None:
            visible.append(_item_label(item))
    for cid in loc.container_ids:
        container = state.containers.get(cid)
        if container is not None:
            visible.append(_container_label(container))
    if visible:
        lines.append("You see: " + ", ".join(visible))

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
    labels: list[str] = []
    for i in state.player_inventory:
        item = state.items.get(i)
        if item is not None:
            labels.append(_item_label(item))
    return "You are carrying: " + ", ".join(labels)
