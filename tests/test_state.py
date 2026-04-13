import dataclasses
import json

from fantsu.state import (
    NPC,
    Container,
    Door,
    Exit,
    Feature,
    GameState,
    Item,
    Location,
    ScheduleEntry,
    Task,
)


def test_door_defaults():
    d = Door(id="wooden_door", description="heavy oak door")
    assert d.state == "closed"
    assert d.locked_by is None


def test_door_open():
    d = Door(id="front_door", description="front door", state="open")
    assert d.state == "open"


def test_container_defaults():
    c = Container(id="old_chest", name="old chest", description="A dusty chest.")
    assert c.state == "closed"
    assert c.locked_by is None
    assert c.item_ids == []
    assert c.portable is False


def test_container_with_items():
    c = Container(
        id="tool_box",
        name="tool box",
        description="A wooden box.",
        item_ids=["hammer", "nails"],
    )
    assert "hammer" in c.item_ids
    assert "nails" in c.item_ids


def test_exit_with_door_id():
    ex = Exit(destination="yard", label="front door to yard", door_id="front_door")
    assert ex.door_id == "front_door"


def test_exit_without_door():
    ex = Exit(destination="kitchen", label="open archway")
    assert ex.door_id is None


def test_feature_defaults():
    f = Feature(id="lake", name="the lake", description="A still lake.")
    assert f.enterable is False
    assert f.destination is None


def test_location_defaults():
    loc = Location(
        id="barn",
        name="Barn",
        type="room",
        description_template="A dusty barn.",
    )
    assert loc.exits == []
    assert loc.item_ids == []
    assert loc.npc_ids == []
    assert loc.features == []
    assert loc.container_ids == []


def test_item_state_dict():
    item = Item(
        id="bucket",
        name="wooden bucket",
        description="A bucket.",
        state={"filled": False},
    )
    assert item.state["filled"] is False
    assert item.portable is True


def test_schedule_entry():
    entry = ScheduleEntry(start_time=0, location_id="main_hall")
    assert entry.start_time == 0


def test_npc_defaults():
    npc = NPC(id="aldric", name="Aldric", occupation="farmer", location_id="main_hall")
    assert npc.memory == []
    assert npc.relationships == {}
    assert npc.disposition == "neutral"
    assert npc.profile == ""


def test_task_defaults():
    task = Task(id="feed_animals", description="Feed the animals.", giver_id="aldric")
    assert task.completed is False
    assert task.completion_check == ""


def test_game_state_defaults():
    state = GameState()
    assert state.time == 0
    assert state.player_location_id == ""
    assert state.player_inventory == []
    assert state.locations == {}
    assert state.doors == {}
    assert state.containers == {}
    assert state.npcs == {}
    assert state.items == {}
    assert state.tasks == []
    assert state.event_log == []


def test_game_state_json_round_trip():
    state = GameState(
        time=30,
        player_location_id="barn",
        player_inventory=["bucket"],
        locations={
            "barn": Location(
                id="barn",
                name="Barn",
                type="room",
                description_template="A dusty barn.",
                item_ids=["pitchfork"],
                npc_ids=["jakob"],
            )
        },
        doors={
            "barn_door": Door(
                id="barn_door",
                description="barn door",
                state="open",
            )
        },
        containers={},
        items={
            "bucket": Item(
                id="bucket",
                name="wooden bucket",
                description="A bucket.",
                state={"filled": True},
                state_labels={"filled": "filled with grain"},
            )
        },
        npcs={
            "jakob": NPC(
                id="jakob",
                name="Jakob",
                occupation="farmhand",
                location_id="barn",
                memory=["Player arrived."],
            )
        },
        tasks=[
            Task(id="feed_animals", description="Feed the animals.", giver_id="aldric")
        ],
        event_log=["Game started."],
    )

    raw = dataclasses.asdict(state)
    serialised = json.dumps(raw)
    restored = json.loads(serialised)

    assert restored["time"] == 30
    assert restored["player_location_id"] == "barn"
    assert restored["player_inventory"] == ["bucket"]
    assert restored["locations"]["barn"]["name"] == "Barn"
    assert restored["doors"]["barn_door"]["state"] == "open"
    assert restored["containers"] == {}
    assert restored["items"]["bucket"]["state"]["filled"] is True
    assert restored["items"]["bucket"]["state_labels"]["filled"] == "filled with grain"
    assert restored["npcs"]["jakob"]["memory"] == ["Player arrived."]
    assert restored["tasks"][0]["completed"] is False
    assert restored["event_log"] == ["Game started."]
