import pytest

from fantsu.state import GameState
from fantsu.world import _current_schedule_location, build, tick_npcs


@pytest.fixture()
def state() -> GameState:
    return build()


# ------------------------------------------------------------------ #
# Location structure                                                   #
# ------------------------------------------------------------------ #


def test_all_locations_present(state: GameState) -> None:
    expected = {
        "farmhand_quarters",
        "main_hall",
        "kitchen",
        "yard",
        "storehouse",
        "barn",
        "road_south",
        "woods_edge",
        "field_path",
        "field_end",
    }
    assert set(state.locations.keys()) == expected


def test_player_starts_in_farmhand_quarters(state: GameState) -> None:
    assert state.player_location_id == "farmhand_quarters"


def test_location_types(state: GameState) -> None:
    assert state.locations["yard"].type == "zone"
    assert state.locations["road_south"].type == "zone"
    assert state.locations["field_path"].type == "zone"
    assert state.locations["barn"].type == "room"
    assert state.locations["woods_edge"].type == "room"
    assert state.locations["field_end"].type == "room"


def test_road_south_has_features(state: GameState) -> None:
    features = state.locations["road_south"].features
    ids = {f.id for f in features}
    assert "dense_woods" in ids
    assert "open_fields" in ids


# ------------------------------------------------------------------ #
# Exit / portal connectivity                                           #
# ------------------------------------------------------------------ #


def test_farmhand_quarters_has_door_to_main_hall(state: GameState) -> None:
    exits = state.locations["farmhand_quarters"].exits
    assert any(e.destination == "main_hall" and e.door_id is not None for e in exits)


def test_main_hall_open_archway_to_kitchen_has_no_door(state: GameState) -> None:
    exits = state.locations["main_hall"].exits
    kitchen_exit = next(e for e in exits if e.destination == "kitchen")
    assert kitchen_exit.door_id is None


def test_barn_door_starts_closed(state: GameState) -> None:
    assert state.doors["barn_door"].state == "closed"


def test_bidirectional_doors_share_state(state: GameState) -> None:
    """Both directions of each door reference the same door_id."""
    fq_exit = next(
        e for e in state.locations["farmhand_quarters"].exits
        if e.destination == "main_hall"
    )
    mh_exit = next(
        e for e in state.locations["main_hall"].exits
        if e.destination == "farmhand_quarters"
    )
    assert fq_exit.door_id == mh_exit.door_id == "wooden_door"


def test_road_south_connects_to_outdoor_zones(state: GameState) -> None:
    road_destinations = {e.destination for e in state.locations["road_south"].exits}
    assert "woods_edge" in road_destinations
    assert "field_path" in road_destinations


def test_road_south_features_are_enterable(state: GameState) -> None:
    features = state.locations["road_south"].features
    woods = next(f for f in features if f.id == "dense_woods")
    fields = next(f for f in features if f.id == "open_fields")
    assert woods.enterable is True
    assert woods.destination == "woods_edge"
    assert fields.enterable is True
    assert fields.destination == "field_path"


def test_woods_edge_has_gnarled_stick(state: GameState) -> None:
    assert "gnarled_stick" in state.locations["woods_edge"].item_ids
    assert "gnarled_stick" in state.items


# ------------------------------------------------------------------ #
# Items                                                                #
# ------------------------------------------------------------------ #


def test_all_items_present(state: GameState) -> None:
    assert set(state.items.keys()) == {
        "bucket",
        "feed_sack",
        "pitchfork",
        "player_boots",
        "gnarled_stick",
    }


def test_bucket_starts_unfilled(state: GameState) -> None:
    assert state.items["bucket"].state["filled"] is False


def test_feed_sack_not_portable(state: GameState) -> None:
    assert state.items["feed_sack"].portable is False


def test_items_in_correct_locations(state: GameState) -> None:
    assert "bucket" in state.locations["storehouse"].item_ids
    assert "feed_sack" in state.locations["storehouse"].item_ids
    assert "pitchfork" in state.locations["barn"].item_ids
    assert "player_boots" in state.locations["farmhand_quarters"].item_ids


# ------------------------------------------------------------------ #
# NPCs                                                                 #
# ------------------------------------------------------------------ #


def test_all_npcs_present(state: GameState) -> None:
    assert set(state.npcs.keys()) == {"aldric", "marta", "jakob"}


def test_aldric_starts_in_main_hall(state: GameState) -> None:
    assert state.npcs["aldric"].location_id == "main_hall"
    assert "aldric" in state.locations["main_hall"].npc_ids


def test_marta_starts_in_kitchen(state: GameState) -> None:
    assert state.npcs["marta"].location_id == "kitchen"
    assert "marta" in state.locations["kitchen"].npc_ids


def test_jakob_starts_in_barn(state: GameState) -> None:
    # Jakob's dawn schedule puts him in farmhand_quarters (time=0),
    # but build() sets location_id directly from the NPC definition which
    # starts him in barn. tick_npcs will correct this when time advances.
    assert state.npcs["jakob"].location_id == "barn"


# ------------------------------------------------------------------ #
# NPC schedule                                                         #
# ------------------------------------------------------------------ #


def test_schedule_location_at_dawn(state: GameState) -> None:
    jakob = state.npcs["jakob"]
    assert _current_schedule_location(jakob, 0) == "farmhand_quarters"


def test_schedule_location_early_morning(state: GameState) -> None:
    jakob = state.npcs["jakob"]
    assert _current_schedule_location(jakob, 30) == "barn"


def test_schedule_location_midday(state: GameState) -> None:
    jakob = state.npcs["jakob"]
    assert _current_schedule_location(jakob, 240) == "yard"


def test_aldric_schedule_mid_morning(state: GameState) -> None:
    aldric = state.npcs["aldric"]
    assert _current_schedule_location(aldric, 90) == "yard"
    assert _current_schedule_location(aldric, 240) == "kitchen"
    assert _current_schedule_location(aldric, 360) == "yard"


# ------------------------------------------------------------------ #
# tick_npcs                                                            #
# ------------------------------------------------------------------ #


def test_tick_moves_jakob_to_farmhand_quarters_at_dawn(state: GameState) -> None:
    # Jakob starts in barn per build(); schedule says farmhand_quarters at t=0
    assert state.npcs["jakob"].location_id == "barn"
    state.time = 0

    tick_npcs(state)

    assert state.npcs["jakob"].location_id == "farmhand_quarters"
    assert "jakob" in state.locations["farmhand_quarters"].npc_ids
    assert "jakob" not in state.locations["barn"].npc_ids


def test_tick_moves_jakob_to_barn_at_30(state: GameState) -> None:
    # Start Jakob in farmhand_quarters at dawn, then advance to t=30
    state.npcs["jakob"].location_id = "farmhand_quarters"
    state.locations["farmhand_quarters"].npc_ids.append("jakob")
    state.time = 30

    tick_npcs(state)

    assert state.npcs["jakob"].location_id == "barn"
    assert "jakob" in state.locations["barn"].npc_ids
    assert "jakob" not in state.locations["farmhand_quarters"].npc_ids


def test_tick_noop_when_already_at_target(state: GameState) -> None:
    state.npcs["marta"].location_id = "kitchen"
    if "marta" not in state.locations["kitchen"].npc_ids:
        state.locations["kitchen"].npc_ids.append("marta")
    state.time = 0

    tick_npcs(state)

    assert state.npcs["marta"].location_id == "kitchen"


# ------------------------------------------------------------------ #
# Tasks                                                                #
# ------------------------------------------------------------------ #


def test_feed_animals_task_present(state: GameState) -> None:
    task_ids = [t.id for t in state.tasks]
    assert "feed_animals" in task_ids


def test_feed_animals_task_not_completed(state: GameState) -> None:
    task = next(t for t in state.tasks if t.id == "feed_animals")
    assert task.completed is False
    assert task.giver_id == "aldric"
