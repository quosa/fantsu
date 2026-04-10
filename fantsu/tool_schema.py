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
                "Use an item from inventory on a target. "
                "Known targets: 'feed_sack' (fill bucket), "
                "'animals' (feed animals in barn)."
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
