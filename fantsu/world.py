"""Factory that constructs the starting game world."""

from fantsu import config
from fantsu.state import (
    NPC,
    Exit,
    Feature,
    GameState,
    Item,
    Location,
    Portal,
    ScheduleEntry,
    Task,
)


def build() -> GameState:
    """Return a fully initialised GameState for the starting farmhouse world."""

    # ------------------------------------------------------------------ #
    # Locations                                                            #
    # ------------------------------------------------------------------ #

    farmhand_quarters = Location(
        id="farmhand_quarters",
        name="Farmhand's Quarters",
        type="room",
        description_template=(
            "A small, sparse room with a straw pallet and a hook on the wall. "
            "Morning light seeps under the door."
        ),
        exits=[
            Exit(
                destination="main_hall",
                label="door to main hall",
                portal=Portal(
                    destination="main_hall",
                    description="wooden door",
                    state="closed",
                ),
            )
        ],
        item_ids=["player_boots"],
        npc_ids=[],
    )

    main_hall = Location(
        id="main_hall",
        name="Main Hall",
        type="room",
        description_template=(
            "The broad main hall of the farmhouse. A long table dominates the centre; "
            "the smell of bread drifts from the kitchen."
        ),
        exits=[
            Exit(
                destination="farmhand_quarters",
                label="door to farmhand quarters",
                portal=Portal(
                    destination="farmhand_quarters",
                    description="wooden door",
                    state="closed",
                ),
            ),
            Exit(destination="kitchen", label="open archway to kitchen"),
            Exit(
                destination="yard",
                label="front door to yard",
                portal=Portal(
                    destination="yard",
                    description="front door",
                    state="open",
                ),
            ),
        ],
        item_ids=[],
        npc_ids=["aldric"],
    )

    kitchen = Location(
        id="kitchen",
        name="Kitchen",
        type="room",
        description_template=(
            "A warm kitchen with a hearth, clay pots, and bunches of dried herbs "
            "hanging from the rafters."
        ),
        exits=[
            Exit(destination="main_hall", label="open archway to main hall"),
        ],
        item_ids=[],
        npc_ids=["marta"],
    )

    yard = Location(
        id="yard",
        name="The Yard",
        type="zone",
        description_template=(
            "The packed-earth yard at the heart of the farm. "
            "Chickens scratch at the ground. "
            "The storehouse and barn stand to either side."
        ),
        exits=[
            Exit(
                destination="main_hall",
                label="front door to main hall",
                portal=Portal(
                    destination="main_hall",
                    description="front door",
                    state="open",
                ),
            ),
            Exit(destination="storehouse", label="storehouse"),
            Exit(
                destination="barn",
                label="barn door",
                portal=Portal(
                    destination="barn",
                    description="barn door",
                    state="closed",
                ),
            ),
            Exit(
                destination="road_south",
                label="farm gate to road",
                portal=Portal(
                    destination="road_south",
                    description="farm gate",
                    state="closed",
                ),
            ),
        ],
        item_ids=[],
        npc_ids=[],
    )

    storehouse = Location(
        id="storehouse",
        name="Storehouse",
        type="room",
        description_template=(
            "A cool, shadowed storehouse. Sacks of grain line the walls and tools hang "
            "from iron pegs."
        ),
        exits=[
            Exit(destination="yard", label="back to the yard"),
        ],
        item_ids=["bucket", "feed_sack"],
        npc_ids=[],
    )

    barn = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template=(
            "A high-beamed barn smelling of hay and animals. Goats and chickens "
            "jostle in their pens."
        ),
        exits=[
            Exit(
                destination="yard",
                label="barn door to yard",
                portal=Portal(
                    destination="yard",
                    description="barn door",
                    state="closed",
                ),
            ),
        ],
        item_ids=["pitchfork"],
        npc_ids=["jakob"],
    )

    road_south = Location(
        id="road_south",
        name="South Road",
        type="zone",
        description_template=(
            "A rutted dirt road stretches away from the farm. Fields open to the east; "
            "a dark wood crowds in from the west."
        ),
        exits=[
            Exit(
                destination="yard",
                label="farm gate back to yard",
                portal=Portal(
                    destination="yard",
                    description="farm gate",
                    state="closed",
                ),
            ),
        ],
        features=[
            Feature(
                id="dense_woods",
                name="dense woods",
                description="Dark, old trees press close to the road.",
            ),
            Feature(
                id="open_fields",
                name="open fields",
                description="Wide fallow fields stretch toward the horizon.",
            ),
        ],
    )

    # ------------------------------------------------------------------ #
    # Items                                                                #
    # ------------------------------------------------------------------ #

    items: dict[str, Item] = {
        "bucket": Item(
            id="bucket",
            name="wooden bucket",
            description="A sturdy wooden bucket with a rope handle.",
            portable=True,
            state={"filled": False},
        ),
        "feed_sack": Item(
            id="feed_sack",
            name="sack of grain",
            description="A heavy sack of mixed grain for the livestock.",
            portable=False,
            state={},
        ),
        "pitchfork": Item(
            id="pitchfork",
            name="pitchfork",
            description="A long-handled pitchfork, good for moving hay.",
            portable=True,
            state={},
        ),
        "player_boots": Item(
            id="player_boots",
            name="worn boots",
            description="Your well-worn leather boots.",
            portable=True,
            state={},
        ),
    }

    # ------------------------------------------------------------------ #
    # NPCs                                                                 #
    # ------------------------------------------------------------------ #

    aldric = NPC(
        id="aldric",
        name="Master Aldric",
        occupation="farmer and landowner",
        location_id="main_hall",
        schedule=[
            ScheduleEntry(start_time=0, location_id="main_hall"),
            ScheduleEntry(start_time=90, location_id="yard"),
            ScheduleEntry(start_time=240, location_id="kitchen"),
            ScheduleEntry(start_time=360, location_id="yard"),
        ],
        relationships={"marta": "wife", "player": "hired hand"},
        profile=(
            "Stern but fair. Worried about the harvest and the state of the barn. "
            "Treats farmhands decently but expects hard work. "
            "Speaks plainly and briefly."
        ),
        disposition="neutral",
    )

    marta = NPC(
        id="marta",
        name="Marta",
        occupation="farmer's wife",
        location_id="kitchen",
        schedule=[
            ScheduleEntry(start_time=0, location_id="kitchen"),
            ScheduleEntry(start_time=90, location_id="yard"),
            ScheduleEntry(start_time=240, location_id="kitchen"),
        ],
        relationships={"aldric": "husband"},
        profile=(
            "Warm and talkative. Knows everything that happens on the farm "
            "and in the village. "
            "Generous with gossip, less so with the good bread. "
            "Speaks in a friendly, "
            "slightly conspiratorial tone."
        ),
        disposition="friendly",
    )

    jakob = NPC(
        id="jakob",
        name="Jakob",
        occupation="senior farmhand",
        location_id="barn",
        schedule=[
            ScheduleEntry(start_time=0, location_id="farmhand_quarters"),
            ScheduleEntry(start_time=30, location_id="barn"),
            ScheduleEntry(start_time=240, location_id="yard"),
        ],
        relationships={"player": "colleague (wary)"},
        profile=(
            "Taciturn and experienced. Slightly resentful of new hires. "
            "Respects competence. "
            "Gives short answers; warms up only if the player proves useful."
        ),
        disposition="wary",
    )

    # ------------------------------------------------------------------ #
    # Tasks                                                                #
    # ------------------------------------------------------------------ #

    tasks = [
        Task(
            id="feed_animals",
            description="Feed the goats and chickens in the barn",
            giver_id="aldric",
            completion_check=(
                "bucket filled AND use_item(bucket, animals) called in barn"
            ),
        )
    ]

    # ------------------------------------------------------------------ #
    # Assemble state                                                       #
    # ------------------------------------------------------------------ #

    locations = {
        loc.id: loc
        for loc in [
            farmhand_quarters,
            main_hall,
            kitchen,
            yard,
            storehouse,
            barn,
            road_south,
        ]
    }

    npcs = {npc.id: npc for npc in [aldric, marta, jakob]}

    return GameState(
        time=0,
        player_location_id="farmhand_quarters",
        locations=locations,
        npcs=npcs,
        items=items,
        tasks=tasks,
    )


# ------------------------------------------------------------------ #
# NPC schedule tick                                                    #
# ------------------------------------------------------------------ #


def _current_schedule_location(npc: NPC, time: int) -> str | None:
    """Return the location_id the NPC should be in at `time`, or None."""
    target: str | None = None
    for entry in npc.schedule:
        if time >= entry.start_time:
            target = entry.location_id
    return target


def tick_npcs(state: GameState) -> None:
    """Move NPCs to their scheduled locations for the current game time."""
    for npc in state.npcs.values():
        target = _current_schedule_location(npc, state.time)
        if target and target != npc.location_id:
            old_loc = state.locations.get(npc.location_id)
            new_loc = state.locations.get(target)
            if old_loc and npc.id in old_loc.npc_ids:
                old_loc.npc_ids.remove(npc.id)
            if new_loc and npc.id not in new_loc.npc_ids:
                new_loc.npc_ids.append(npc.id)
            npc.location_id = target


def advance_time(state: GameState, location_type: str) -> None:
    """Advance game time based on location type."""
    if location_type == "zone":
        state.time += config.TIME_PER_ZONE_TRAVERSAL
    else:
        state.time += config.TIME_PER_ROOM_ACTION
    tick_npcs(state)
