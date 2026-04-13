"""Unit tests for tools.py — no LLM calls."""

import pytest

from fantsu.state import GameState
from fantsu.tools import (
    close_portal,
    drop_item,
    get_time,
    look,
    move_to,
    open_container,
    open_portal,
    put_into,
    record_talk,
    take_from,
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
    assert state.doors["wooden_door"].state == "open"


def test_door_shared_state_bidirectional(state: GameState) -> None:
    """Opening a door from one side makes it open from the other side too."""
    state.player_location_id = "farmhand_quarters"
    open_portal("main_hall", state)
    # The door object is shared — the reverse exit must also see it as open
    reverse_exit = next(
        e for e in state.locations["main_hall"].exits
        if e.destination == "farmhand_quarters"
    )
    assert reverse_exit.door_id == "wooden_door"
    assert state.doors[reverse_exit.door_id].state == "open"


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
    # Lock the farm gate via the shared Door object
    state.doors["farm_gate"].state = "locked"

    result = open_portal("road_south", state)
    assert not result.ok
    assert "locked" in result.message


# ------------------------------------------------------------------ #
# close_portal                                                         #
# ------------------------------------------------------------------ #


def test_close_portal_open_becomes_closed(state: GameState) -> None:
    state.player_location_id = "main_hall"
    result = close_portal("yard", state)
    assert result.ok
    assert state.doors["front_door"].state == "closed"


def test_close_portal_already_closed(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    result = close_portal("main_hall", state)
    assert result.ok
    assert "already closed" in result.message


def test_close_portal_no_such_exit(state: GameState) -> None:
    state.player_location_id = "barn"
    result = close_portal("kitchen", state)
    assert not result.ok


def test_close_portal_no_portal_on_exit(state: GameState) -> None:
    state.player_location_id = "storehouse"
    result = close_portal("yard", state)
    assert not result.ok


def test_close_portal_locked(state: GameState) -> None:
    # A locked door is already secured — closing it returns "already closed"
    state.player_location_id = "yard"
    state.doors["farm_gate"].state = "locked"
    result = close_portal("road_south", state)
    assert result.ok
    assert "already closed" in result.message


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


def test_use_item_not_accessible(state: GameState) -> None:
    # Player in farmhand_quarters; bucket is in storehouse — not reachable
    state.player_location_id = "farmhand_quarters"
    assert "bucket" not in state.player_inventory
    assert "bucket" not in state.locations["farmhand_quarters"].item_ids
    result = use_item("bucket", "feed_sack", state)
    assert not result.ok
    assert "don't see" in result.message


def test_use_item_fill_bucket_from_floor(state: GameState) -> None:
    # Bucket on the floor (not in inventory) can be filled from the feed_sack
    state.player_location_id = "storehouse"
    assert "bucket" not in state.player_inventory
    assert "bucket" in state.locations["storehouse"].item_ids
    result = use_item("bucket", "feed_sack", state)
    assert result.ok
    assert state.items["bucket"].state["filled"] is True


def test_use_item_fill_bucket_not_accessible(state: GameState) -> None:
    # Bucket in a different room — cannot fill it
    state.player_location_id = "farmhand_quarters"
    assert "bucket" not in state.player_inventory
    result = use_item("bucket", "feed_sack", state)
    assert not result.ok
    assert "don't see" in result.message


def test_use_item_empty_bucket_in_inventory(state: GameState) -> None:
    state.player_inventory.append("bucket")
    state.items["bucket"].state["filled"] = True
    result = use_item("bucket", "floor", state)
    assert result.ok
    assert state.items["bucket"].state["filled"] is False


def test_use_item_empty_bucket_from_floor(state: GameState) -> None:
    state.player_location_id = "storehouse"
    state.items["bucket"].state["filled"] = True
    assert "bucket" not in state.player_inventory
    result = use_item("bucket", "floor", state)
    assert result.ok
    assert state.items["bucket"].state["filled"] is False


def test_use_item_empty_bucket_already_empty(state: GameState) -> None:
    state.player_inventory.append("bucket")
    result = use_item("bucket", "floor", state)
    assert not result.ok
    assert "already empty" in result.message


def test_use_item_empty_bucket_not_accessible(state: GameState) -> None:
    state.player_location_id = "farmhand_quarters"
    assert "bucket" not in state.player_inventory
    result = use_item("bucket", "floor", state)
    assert not result.ok
    assert "don't see" in result.message


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


# ------------------------------------------------------------------ #
# Container helpers — build a minimal state with a chest              #
# ------------------------------------------------------------------ #


def _state_with_chest() -> GameState:
    """Return a world-built state with a chest added to the storehouse."""
    from fantsu.state import Container

    s = build()
    chest = Container(
        id="old_chest",
        name="old chest",
        description="A dusty old chest.",
        item_ids=["pitchfork"],
    )
    s.containers["old_chest"] = chest
    s.locations["storehouse"].container_ids.append("old_chest")
    return s


# ------------------------------------------------------------------ #
# open_container                                                       #
# ------------------------------------------------------------------ #


def test_open_container_closed_becomes_open() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    result = open_container("old_chest", s)
    assert result.ok
    assert s.containers["old_chest"].state == "open"


def test_open_container_already_open() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "open"
    result = open_container("old_chest", s)
    assert result.ok
    assert "already open" in result.message


def test_open_container_locked() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "locked"
    result = open_container("old_chest", s)
    assert not result.ok
    assert "locked" in result.message


def test_open_container_not_in_scope() -> None:
    s = _state_with_chest()
    s.player_location_id = "barn"  # chest is in storehouse
    result = open_container("old_chest", s)
    assert not result.ok


# ------------------------------------------------------------------ #
# take_from                                                            #
# ------------------------------------------------------------------ #


def test_take_from_open_container() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "open"
    result = take_from("old_chest", "pitchfork", s)
    assert result.ok
    assert "pitchfork" in s.player_inventory
    assert "pitchfork" not in s.containers["old_chest"].item_ids


def test_take_from_closed_container_blocked() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    result = take_from("old_chest", "pitchfork", s)
    assert not result.ok
    assert "closed" in result.message


def test_take_from_item_not_in_container() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "open"
    result = take_from("old_chest", "bucket", s)
    assert not result.ok


# ------------------------------------------------------------------ #
# put_into                                                             #
# ------------------------------------------------------------------ #


def test_put_into_open_container() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "open"
    s.player_inventory.append("bucket")
    result = put_into("bucket", "old_chest", s)
    assert result.ok
    assert "bucket" not in s.player_inventory
    assert "bucket" in s.containers["old_chest"].item_ids


def test_put_into_closed_container_blocked() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.player_inventory.append("bucket")
    result = put_into("bucket", "old_chest", s)
    assert not result.ok
    assert "closed" in result.message


def test_put_into_not_in_inventory() -> None:
    s = _state_with_chest()
    s.player_location_id = "storehouse"
    s.containers["old_chest"].state = "open"
    result = put_into("bucket", "old_chest", s)
    assert not result.ok
