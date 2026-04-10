"""Unit tests for tools.py — no LLM calls."""

import pytest

from fantsu.state import GameState
from fantsu.tools import (
    drop_item,
    get_time,
    look,
    move_to,
    open_portal,
    record_talk,
    take_item,
    use_item,
    validate_talk_to,
)
from fantsu.world import build


@pytest.fixture()
def state() -> GameState:
    return build()


# ------------------------------------------------------------------ #
# move_to                                                              #
# ------------------------------------------------------------------ #


def test_move_to_valid_no_portal(state: GameState) -> None:
    state.player_location_id = "main_hall"
    result = move_to("kitchen", state)
    assert result.ok
    assert state.player_location_id == "kitchen"


def test_move_to_advances_time(state: GameState) -> None:
    state.player_location_id = "main_hall"
    t_before = state.time
    move_to("kitchen", state)
    assert state.time > t_before


def test_move_to_blocked_by_closed_portal(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    result = move_to("main_hall", state)
    assert not result.ok
    assert "closed" in result.message


def test_move_to_succeeds_after_portal_opened(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    open_portal("main_hall", state)
    result = move_to("main_hall", state)
    assert result.ok
    assert state.player_location_id == "main_hall"


def test_move_to_missing_exit(state: GameState) -> None:
    state.player_location_id = "barn"
    result = move_to("kitchen", state)
    assert not result.ok


def test_move_to_appends_event_log(state: GameState) -> None:
    state.player_location_id = "main_hall"
    move_to("kitchen", state)
    assert any("kitchen" in e for e in state.event_log)


# ------------------------------------------------------------------ #
# open_portal                                                          #
# ------------------------------------------------------------------ #


def test_open_portal_closed_becomes_open(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    result = open_portal("main_hall", state)
    assert result.ok
    exits = state.locations["farmhand_quarters"].exits
    portal = next(e.portal for e in exits if e.destination == "main_hall")
    assert portal is not None
    assert portal.state == "open"


def test_open_portal_already_open(state: GameState) -> None:
    state.player_location_id = "main_hall"
    result = open_portal("yard", state)
    assert result.ok
    assert "already open" in result.message


def test_open_portal_no_such_exit(state: GameState) -> None:
    state.player_location_id = "barn"
    result = open_portal("kitchen", state)
    assert not result.ok


def test_open_portal_no_portal_on_exit(state: GameState) -> None:
    state.player_location_id = "main_hall"
    result = open_portal("kitchen", state)
    assert not result.ok


def test_open_portal_locked(state: GameState) -> None:
    state.player_location_id = "yard"
    # Lock the farm gate
    exits = state.locations["yard"].exits
    gate_exit = next(e for e in exits if e.destination == "road_south")
    assert gate_exit.portal is not None
    gate_exit.portal.state = "locked"

    result = open_portal("road_south", state)
    assert not result.ok
    assert "locked" in result.message


# ------------------------------------------------------------------ #
# take_item                                                            #
# ------------------------------------------------------------------ #


def test_take_item_portable(state: GameState) -> None:
    state.player_location_id = "storehouse"
    result = take_item("bucket", state)
    assert result.ok
    assert "bucket" in state.player_inventory
    assert "bucket" not in state.locations["storehouse"].item_ids


def test_take_item_not_portable(state: GameState) -> None:
    state.player_location_id = "storehouse"
    result = take_item("feed_sack", state)
    assert not result.ok
    assert "feed_sack" not in state.player_inventory


def test_take_item_not_in_location(state: GameState) -> None:
    state.player_location_id = "barn"
    result = take_item("bucket", state)
    assert not result.ok


def test_take_item_appends_event_log(state: GameState) -> None:
    state.player_location_id = "storehouse"
    take_item("bucket", state)
    assert any("bucket" in e for e in state.event_log)


# ------------------------------------------------------------------ #
# drop_item                                                            #
# ------------------------------------------------------------------ #


def test_drop_item_in_inventory(state: GameState) -> None:
    state.player_location_id = "barn"
    state.player_inventory.append("bucket")
    result = drop_item("bucket", state)
    assert result.ok
    assert "bucket" not in state.player_inventory
    assert "bucket" in state.locations["barn"].item_ids


def test_drop_item_not_in_inventory(state: GameState) -> None:
    result = drop_item("bucket", state)
    assert not result.ok


# ------------------------------------------------------------------ #
# use_item                                                             #
# ------------------------------------------------------------------ #


def test_use_item_fill_bucket(state: GameState) -> None:
    state.player_location_id = "storehouse"
    state.player_inventory.append("bucket")
    result = use_item("bucket", "feed_sack", state)
    assert result.ok
    assert state.items["bucket"].state["filled"] is True


def test_use_item_fill_bucket_already_full(state: GameState) -> None:
    state.player_inventory.append("bucket")
    state.items["bucket"].state["filled"] = True
    result = use_item("bucket", "feed_sack", state)
    assert result.ok
    assert "already" in result.message


def test_use_item_feed_animals_completes_task(state: GameState) -> None:
    state.player_location_id = "barn"
    state.player_inventory.append("bucket")
    state.items["bucket"].state["filled"] = True
    result = use_item("bucket", "animals", state)
    assert result.ok
    task = next(t for t in state.tasks if t.id == "feed_animals")
    assert task.completed is True


def test_use_item_feed_animals_alias_targets(state: GameState) -> None:
    for target in ("chickens", "goats", "livestock", "trough"):
        s = build()
        s.player_location_id = "barn"
        s.player_inventory.append("bucket")
        s.items["bucket"].state["filled"] = True
        result = use_item("bucket", target, s)
        assert result.ok, f"target '{target}' should work"
        task = next(t for t in s.tasks if t.id == "feed_animals")
        assert task.completed is True


def test_use_item_feed_animals_empty_bucket(state: GameState) -> None:
    state.player_location_id = "barn"
    state.player_inventory.append("bucket")
    result = use_item("bucket", "animals", state)
    assert not result.ok
    assert "empty" in result.message


def test_use_item_feed_animals_wrong_location(state: GameState) -> None:
    state.player_location_id = "yard"
    state.player_inventory.append("bucket")
    state.items["bucket"].state["filled"] = True
    result = use_item("bucket", "animals", state)
    assert not result.ok


def test_use_item_not_in_inventory(state: GameState) -> None:
    result = use_item("bucket", "feed_sack", state)
    assert not result.ok


def test_use_item_unknown_combination(state: GameState) -> None:
    state.player_inventory.append("pitchfork")
    result = use_item("pitchfork", "animals", state)
    assert not result.ok


def test_use_item_wear_boots(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    state.player_inventory.append("player_boots")
    result = use_item("player_boots", "self", state)
    assert result.ok
    assert state.items["player_boots"].state.get("worn") is True


def test_use_item_wear_boots_already_worn(state: GameState) -> None:
    state.player_inventory.append("player_boots")
    state.items["player_boots"].state["worn"] = True
    result = use_item("player_boots", "self", state)
    assert result.ok
    assert "already" in result.message


def test_use_item_wear_boots_via_feet_target(state: GameState) -> None:
    state.player_inventory.append("player_boots")
    result = use_item("player_boots", "feet", state)
    assert result.ok


# ------------------------------------------------------------------ #
# validate_talk_to                                                     #
# ------------------------------------------------------------------ #


def test_validate_talk_to_npc_present(state: GameState) -> None:
    state.player_location_id = "main_hall"
    error = validate_talk_to("aldric", state)
    assert error is None


def test_validate_talk_to_npc_absent(state: GameState) -> None:
    state.player_location_id = "barn"
    error = validate_talk_to("aldric", state)
    assert error is not None
    assert not error.ok


def test_validate_talk_to_unknown_npc(state: GameState) -> None:
    error = validate_talk_to("ghost", state)
    assert error is not None
    assert not error.ok


# ------------------------------------------------------------------ #
# record_talk                                                          #
# ------------------------------------------------------------------ #


def test_record_talk_appends_memory(state: GameState) -> None:
    record_talk("aldric", "Good morning, sir.", state)
    assert any("Good morning" in m for m in state.npcs["aldric"].memory)


def test_record_talk_trims_memory_to_limit(state: GameState) -> None:
    for i in range(15):
        record_talk("aldric", f"Message {i}", state)
    assert len(state.npcs["aldric"].memory) <= 10


# ------------------------------------------------------------------ #
# look                                                                 #
# ------------------------------------------------------------------ #


def test_look_returns_location_text(state: GameState) -> None:
    result = look(state)
    assert result.ok
    assert "Farmhand" in result.message


def test_look_does_not_advance_time(state: GameState) -> None:
    t_before = state.time
    look(state)
    assert state.time == t_before


# ------------------------------------------------------------------ #
# get_time                                                             #
# ------------------------------------------------------------------ #


def test_get_time_returns_string(state: GameState) -> None:
    result = get_time(state)
    assert result.ok
    assert isinstance(result.message, str)
    assert len(result.message) > 0
