"""Tool definitions in Ollama/OpenAI tool-call format."""

ALL_TOOLS: list[dict[str, object]] = [
    {
        "type": "function",
        "function": {
            "name": "move_to",
            "description": (
                "Move the player to an adjacent location. "
                "Only works if a direct exit exists and any portal is open."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {
                        "type": "string",
                        "description": "The id of the destination location.",
                    }
                },
                "required": ["location_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_portal",
            "description": "Open a door or gate on the exit leading to a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {
                        "type": "string",
                        "description": (
                            "The destination location id whose portal should be opened."
                        ),
                    }
                },
                "required": ["location_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_portal",
            "description": "Close a door or gate on the exit leading to a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {
                        "type": "string",
                        "description": (
                            "The destination location id whose portal should be closed."
                        ),
                    }
                },
                "required": ["location_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_item",
            "description": "Pick up a portable item from the current location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The id of the item to pick up.",
                    }
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drop_item",
            "description": "Drop an item from the player's inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The id of the item to drop.",
                    }
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_item",
            "description": (
                "Use an item (from inventory or current location) on a target. "
                "To fill the bucket: use_item(bucket, feed_sack). "
                "To empty the bucket: use_item(bucket, floor). "
                "To feed animals in the barn: use_item(bucket, animals) "
                "— also accepts 'chickens', 'goats', 'livestock', 'trough'. "
                "To wear boots: use_item(player_boots, self)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The id of the item to use.",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "The id of the target (item, NPC, or keyword).",
                    },
                },
                "required": ["item_id", "target_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "talk_to",
            "description": "Speak to an NPC in the same location as the player.",
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_id": {
                        "type": "string",
                        "description": "The id of the NPC to talk to.",
                    },
                    "message": {
                        "type": "string",
                        "description": "What the player says to the NPC.",
                    },
                },
                "required": ["npc_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_container",
            "description": (
                "Open a container (chest, cabinet, drawer, etc.) "
                "in the current location or a portable container in inventory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "The id of the container to open.",
                    }
                },
                "required": ["container_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_from",
            "description": "Take an item from an open container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "The id of the container to take from.",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "The id of the item to take.",
                    },
                },
                "required": ["container_id", "item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "put_into",
            "description": "Put an item from inventory into an open container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The id of the item to put into the container.",
                    },
                    "container_id": {
                        "type": "string",
                        "description": "The id of the container to put the item into.",
                    },
                },
                "required": ["item_id", "container_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "look",
            "description": "Describe the current location. Does not advance time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Return the current in-game time of day.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
