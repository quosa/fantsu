import pytest

from fantsu.renderer import describe_inventory, describe_location, format_time
from fantsu.state import NPC, Container, Door, Exit, Feature, GameState, Item, Location

# ------------------------------------------------------------------ #
# format_time                                                          #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, "just before dawn"),
        (1, "just before dawn"),
        (29, "just before dawn"),
        (30, "early morning"),
        (89, "early morning"),
        (90, "mid morning"),
        (180, "late morning"),
        (240, "around noon"),
        (360, "afternoon"),
        (480, "late afternoon"),
        (600, "evening"),
        (720, "night"),
        (999, "night"),
    ],
)
def test_format_time(minutes: int, expected: str) -> None:
    assert format_time(minutes) == expected


# ------------------------------------------------------------------ #
# describe_location helpers                                            #
# ------------------------------------------------------------------ #


def _minimal_state(loc: Location) -> GameState:
    """Build a GameState containing only the given location."""
    return GameState(
        player_location_id=loc.id,
        locations={loc.id: loc},
    )


# ------------------------------------------------------------------ #
# describe_location — heading and base description                     #
# ------------------------------------------------------------------ #


def test_describe_location_heading() -> None:
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="A dusty barn.",
    )
    text = describe_location(_minimal_state(loc))
    assert "[ Barn ]" in text
    assert "A dusty barn." in text


# ------------------------------------------------------------------ #
# describe_location — exits                                            #
# ------------------------------------------------------------------ #


def test_describe_location_exit_without_portal() -> None:
    loc = Location(
        id="kitchen",
        name="Kitchen",
        type="room",
        description_template="A warm kitchen.",
        exits=[Exit(destination="main_hall", label="open archway to main hall")],
    )
    text = describe_location(_minimal_state(loc))
    assert "open archway to main hall" in text
    assert "Exits:" in text


def test_describe_location_exit_with_door() -> None:
    loc = Location(
        id="farmhand_quarters",
        name="Farmhand's Quarters",
        type="room",
        description_template="A sparse room.",
        exits=[
            Exit(
                destination="main_hall",
                label="door to main hall",
                door_id="wooden_door",
            )
        ],
    )
    state = GameState(
        player_location_id="farmhand_quarters",
        locations={"farmhand_quarters": loc},
        doors={
            "wooden_door": Door(
                id="wooden_door", description="wooden door", state="closed"
            )
        },
    )
    text = describe_location(state)
    assert "wooden door" in text
    assert "closed" in text


def test_describe_location_no_exits_omits_exits_line() -> None:
    loc = Location(
        id="void",
        name="Void",
        type="room",
        description_template="Nothing.",
    )
    text = describe_location(_minimal_state(loc))
    assert "Exits" not in text


# ------------------------------------------------------------------ #
# describe_location — items                                            #
# ------------------------------------------------------------------ #


def test_describe_location_items_no_id_hint() -> None:
    """Player-facing output must not expose internal item ids."""
    loc = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template="A cool storehouse.",
        item_ids=["bucket"],
    )
    state = GameState(
        player_location_id="storehouse",
        locations={"storehouse": loc},
        items={
            "bucket": Item(id="bucket", name="wooden bucket", description="A bucket.")
        },
    )
    text = describe_location(state)
    assert "id=" not in text


def test_describe_location_shows_items() -> None:
    loc = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template="A cool storehouse.",
        item_ids=["bucket"],
    )
    state = GameState(
        player_location_id="storehouse",
        locations={"storehouse": loc},
        items={
            "bucket": Item(
                id="bucket",
                name="wooden bucket",
                description="A bucket.",
            )
        },
    )
    text = describe_location(state)
    assert "wooden bucket" in text
    assert "You see:" in text


def test_describe_location_no_items_omits_you_see() -> None:
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="A dusty barn.",
    )
    text = describe_location(_minimal_state(loc))
    assert "You see" not in text


# ------------------------------------------------------------------ #
# describe_location — NPCs                                             #
# ------------------------------------------------------------------ #


def test_describe_location_shows_npcs() -> None:
    loc = Location(
        id="main_hall",
        name="Main Hall",
        type="room",
        description_template="A broad hall.",
        npc_ids=["aldric"],
    )
    state = GameState(
        player_location_id="main_hall",
        locations={"main_hall": loc},
        npcs={
            "aldric": NPC(
                id="aldric",
                name="Master Aldric",
                occupation="farmer",
                location_id="main_hall",
            )
        },
    )
    text = describe_location(state)
    assert "Master Aldric" in text
    assert "Here:" in text


def test_describe_location_no_npcs_omits_here() -> None:
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="Empty barn.",
    )
    text = describe_location(_minimal_state(loc))
    assert "Here" not in text


# ------------------------------------------------------------------ #
# describe_location — zone features                                    #
# ------------------------------------------------------------------ #


def test_describe_location_zone_shows_features() -> None:
    loc = Location(
        id="road_south",
        name="South Road",
        type="zone",
        description_template="A rutted road.",
        features=[
            Feature(id="woods", name="dense woods", description="Dark trees."),
            Feature(id="fields", name="open fields", description="Wide fields."),
        ],
    )
    text = describe_location(_minimal_state(loc))
    assert "dense woods" in text
    assert "open fields" in text
    assert "Nearby:" in text


def test_describe_location_room_omits_nearby_even_with_features() -> None:
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="A barn.",
        features=[Feature(id="hay", name="hay pile", description="Hay.")],
    )
    text = describe_location(_minimal_state(loc))
    assert "Nearby" not in text


# ------------------------------------------------------------------ #
# describe_inventory                                                   #
# ------------------------------------------------------------------ #


def test_describe_inventory_empty() -> None:
    state = GameState()
    assert describe_inventory(state) == "You are carrying nothing."


def test_describe_inventory_with_items() -> None:
    state = GameState(
        player_inventory=["bucket", "pitchfork"],
        items={
            "bucket": Item(id="bucket", name="wooden bucket", description="A bucket."),
            "pitchfork": Item(
                id="pitchfork", name="pitchfork", description="A fork."
            ),
        },
    )
    text = describe_inventory(state)
    assert "wooden bucket" in text
    assert "pitchfork" in text
    assert "You are carrying:" in text


# ------------------------------------------------------------------ #
# item state labels                                                    #
# ------------------------------------------------------------------ #


def test_item_state_label_shown_when_active() -> None:
    loc = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template="A cool storehouse.",
        item_ids=["bucket"],
    )
    state = GameState(
        player_location_id="storehouse",
        locations={"storehouse": loc},
        items={
            "bucket": Item(
                id="bucket",
                name="wooden bucket",
                description="A bucket.",
                state={"filled": True},
                state_labels={"filled": "filled with grain"},
            )
        },
    )
    text = describe_location(state)
    assert "filled with grain" in text


def test_item_state_label_hidden_when_inactive() -> None:
    loc = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template="A cool storehouse.",
        item_ids=["bucket"],
    )
    state = GameState(
        player_location_id="storehouse",
        locations={"storehouse": loc},
        items={
            "bucket": Item(
                id="bucket",
                name="wooden bucket",
                description="A bucket.",
                state={"filled": False},
                state_labels={"filled": "filled with grain"},
            )
        },
    )
    text = describe_location(state)
    assert "wooden bucket" in text
    assert "filled with grain" not in text


def test_inventory_shows_item_state_label() -> None:
    state = GameState(
        player_inventory=["bucket"],
        items={
            "bucket": Item(
                id="bucket",
                name="wooden bucket",
                description="A bucket.",
                state={"filled": True},
                state_labels={"filled": "filled with grain"},
            )
        },
    )
    text = describe_inventory(state)
    assert "filled with grain" in text


# ------------------------------------------------------------------ #
# containers in location                                               #
# ------------------------------------------------------------------ #


def test_container_shown_in_you_see() -> None:
    loc = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template="A cool storehouse.",
        container_ids=["old_chest"],
    )
    state = GameState(
        player_location_id="storehouse",
        locations={"storehouse": loc},
        containers={
            "old_chest": Container(
                id="old_chest",
                name="old chest",
                description="A dusty chest.",
            )
        },
    )
    text = describe_location(state)
    assert "old chest" in text
    assert "closed" in text
    assert "You see:" in text


def test_open_container_shown_as_open() -> None:
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="A barn.",
        container_ids=["tool_box"],
    )
    state = GameState(
        player_location_id="barn",
        locations={"barn": loc},
        containers={
            "tool_box": Container(
                id="tool_box",
                name="tool box",
                description="A wooden box.",
                state="open",
            )
        },
    )
    text = describe_location(state)
    assert "tool box" in text
    assert "open" in text
