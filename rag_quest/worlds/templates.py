"""Built-in world templates for quick start."""


STARTER_WORLDS = {
    "classic_dungeon": {
        "name": "Classic Dungeon",
        "setting": "Medieval Fantasy",
        "tone": "Dark",
        "description": "A classic fantasy dungeon crawl. Descend into the depths to face monsters and claim treasure.",
        "difficulty": "medium",
        "tags": ["dungeon", "classic", "fantasy"],
        "world_config": {
            "name": "The Deep Caverns",
            "setting": "Medieval Fantasy",
            "tone": "Dark",
            "day_number": 1,
        },
        "npc_seed": "dungeon_creatures",
        "quest_seed": "dungeon_quests",
    },
    "enchanted_forest": {
        "name": "Enchanted Forest",
        "setting": "Magical Realm",
        "tone": "Whimsical",
        "description": "Venture into a mystical forest filled with magic, fey creatures, and ancient secrets.",
        "difficulty": "medium",
        "tags": ["forest", "magic", "exploration"],
        "world_config": {
            "name": "The Endless Woods",
            "setting": "Magical Realm",
            "tone": "Whimsical",
            "day_number": 1,
        },
        "npc_seed": "forest_fey",
        "quest_seed": "forest_quests",
    },
    "port_city": {
        "name": "Port City",
        "setting": "Urban Fantasy",
        "tone": "Intrigue",
        "description": "A bustling port city filled with merchants, sailors, and intrigue. Navigate politics and trade.",
        "difficulty": "medium",
        "tags": ["city", "urban", "intrigue"],
        "world_config": {
            "name": "Saltmere Harbor",
            "setting": "Urban Fantasy",
            "tone": "Intrigue",
            "day_number": 1,
        },
        "npc_seed": "city_folk",
        "quest_seed": "city_quests",
    },
    "war_torn_kingdom": {
        "name": "War-Torn Kingdom",
        "setting": "Medieval Fantasy",
        "tone": "Dark",
        "description": "A kingdom torn by civil war. Choose your allegiances and survive the conflict.",
        "difficulty": "hard",
        "tags": ["war", "conflict", "political"],
        "world_config": {
            "name": "The Fractured Realm",
            "setting": "Medieval Fantasy",
            "tone": "Dark",
            "day_number": 1,
        },
        "npc_seed": "faction_leaders",
        "quest_seed": "faction_quests",
    },
}
