import dataclasses
import json

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


def test_portal_defaults():
    p = Portal(destination="barn", description="heavy oak door")
    assert p.state == "closed"
    assert p.locked_by is None


def test_exit_with_portal():
    portal = Portal(destination="yard", description="front door", state="open")
    ex = Exit(destination="yard", label="north", portal=portal)
    assert ex.portal is portal


def test_exit_without_portal():
    ex = Exit(destination="kitchen", label="open archway")
    assert ex.portal is None


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
    assert restored["items"]["bucket"]["state"]["filled"] is True
    assert restored["items"]["bucket"]["state_labels"]["filled"] == "filled with grain"
    assert restored["npcs"]["jakob"]["memory"] == ["Player arrived."]
    assert restored["tasks"][0]["completed"] is False
    assert restored["event_log"] == ["Game started."]
