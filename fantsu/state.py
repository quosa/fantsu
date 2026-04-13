from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Door:
    id: str
    description: str
    state: Literal["open", "closed", "locked"] = "closed"
    locked_by: str | None = None  # item id of key, if any


@dataclass
class Container:
    id: str
    name: str
    description: str
    state: Literal["open", "closed", "locked"] = "closed"
    locked_by: str | None = None  # item id of key, if any
    item_ids: list[str] = field(default_factory=list)
    # True → also tracked in Location.item_ids / player_inventory
    portable: bool = False


@dataclass
class Exit:
    destination: str
    label: str
    door_id: str | None = None  # None = walk straight through


@dataclass
class Feature:
    id: str
    name: str
    description: str
    enterable: bool = False
    destination: str | None = None  # location id if enterable


@dataclass
class Location:
    id: str
    name: str
    type: Literal["room", "zone"]
    description_template: str
    exits: list[Exit] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)
    npc_ids: list[str] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    container_ids: list[str] = field(default_factory=list)


@dataclass
class Item:
    id: str
    name: str
    description: str
    portable: bool = True
    state: dict[str, object] = field(default_factory=dict)
    state_labels: dict[str, str] = field(default_factory=dict)


@dataclass
class ScheduleEntry:
    start_time: int  # minutes since dawn (0 = dawn)
    location_id: str


@dataclass
class NPC:
    id: str
    name: str
    occupation: str
    location_id: str
    schedule: list[ScheduleEntry] = field(default_factory=list)
    relationships: dict[str, str] = field(default_factory=dict)
    memory: list[str] = field(default_factory=list)
    profile: str = ""
    disposition: str = "neutral"


@dataclass
class Task:
    id: str
    description: str
    giver_id: str
    completed: bool = False
    completion_check: str = ""


@dataclass
class GameState:
    time: int = 0
    player_location_id: str = ""
    player_inventory: list[str] = field(default_factory=list)
    locations: dict[str, Location] = field(default_factory=dict)
    doors: dict[str, Door] = field(default_factory=dict)
    containers: dict[str, Container] = field(default_factory=dict)
    npcs: dict[str, NPC] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
