"""Dynamic encounter generation for RAG-Quest."""

import random
from typing import List, Optional
from .combat import Enemy


# Location-based enemy tables
LOCATION_ENEMIES = {
    "forest": ["Wolf", "Bandit", "Giant Spider", "Goblin Scout"],
    "dungeon": ["Skeleton", "Goblin", "Orc", "Undead Knight"],
    "cave": ["Giant Bat", "Giant Rat", "Troll", "Cave Wyrm"],
    "marketplace": ["Thief", "Mugger", "Angry Guard"],
    "ruins": ["Ancient Guardian", "Ghost", "Stone Golem", "Cursed Mummy"],
    "forest clearing": ["Wolf", "Dire Bear", "Centaur", "Forest Druid"],
    "underground": ["Dwarf Warrior", "Drow Assassin", "Beholder", "Mind Flayer"],
}

# Enemy templates with base stats
ENEMY_TEMPLATES = {
    "Wolf": {
        "hp": 15,
        "attack": 3,
        "defense": 11,
        "dexterity": 13,
        "damage_dice": "1d6+1",
        "xp": 50,
        "loot": ["Wolf Pelt", "Sharp Fang"],
    },
    "Bandit": {
        "hp": 18,
        "attack": 4,
        "defense": 12,
        "dexterity": 14,
        "damage_dice": "1d8+1",
        "xp": 75,
        "loot": ["Gold Coins", "Stolen Ring", "Lockpick"],
    },
    "Giant Spider": {
        "hp": 20,
        "attack": 4,
        "defense": 13,
        "dexterity": 15,
        "damage_dice": "1d8+2",
        "xp": 100,
        "loot": ["Spider Silk", "Poison Fangs"],
    },
    "Goblin Scout": {
        "hp": 12,
        "attack": 2,
        "defense": 10,
        "dexterity": 12,
        "damage_dice": "1d6",
        "xp": 40,
        "loot": ["Goblin Ears", "Crude Dagger"],
    },
    "Skeleton": {
        "hp": 22,
        "attack": 4,
        "defense": 11,
        "dexterity": 11,
        "damage_dice": "1d8+1",
        "xp": 75,
        "loot": ["Bone Fragment", "Curse Mark"],
    },
    "Goblin": {
        "hp": 14,
        "attack": 3,
        "defense": 11,
        "dexterity": 12,
        "damage_dice": "1d6+1",
        "xp": 50,
        "loot": ["Goblin Gold", "Small Dagger"],
    },
    "Orc": {
        "hp": 26,
        "attack": 5,
        "defense": 12,
        "dexterity": 10,
        "damage_dice": "1d10+2",
        "xp": 125,
        "loot": ["Orcish Blade", "Orcish Shield", "Tribal Tattoo"],
    },
    "Undead Knight": {
        "hp": 35,
        "attack": 6,
        "defense": 14,
        "dexterity": 10,
        "damage_dice": "2d8+2",
        "xp": 200,
        "loot": ["Cursed Armor", "Ancient Sword", "Holy Relic"],
    },
    "Giant Bat": {
        "hp": 16,
        "attack": 3,
        "defense": 12,
        "dexterity": 14,
        "damage_dice": "1d6+1",
        "xp": 60,
        "loot": ["Bat Wing", "Echolocation Crystal"],
    },
    "Giant Rat": {
        "hp": 10,
        "attack": 2,
        "defense": 10,
        "dexterity": 13,
        "damage_dice": "1d4+1",
        "xp": 25,
        "loot": ["Rat Whiskers"],
    },
    "Troll": {
        "hp": 40,
        "attack": 6,
        "defense": 12,
        "dexterity": 9,
        "damage_dice": "2d8+3",
        "xp": 250,
        "loot": ["Troll Skin", "Regeneration Salve"],
    },
    "Cave Wyrm": {
        "hp": 50,
        "attack": 7,
        "defense": 15,
        "dexterity": 11,
        "damage_dice": "2d10+3",
        "xp": 400,
        "loot": ["Dragon Scale", "Wyrm Egg", "Ancient Hoard"],
    },
    "Thief": {
        "hp": 16,
        "attack": 4,
        "defense": 12,
        "dexterity": 15,
        "damage_dice": "1d8+1",
        "xp": 70,
        "loot": ["Stolen Goods", "Lockpick Set"],
    },
    "Mugger": {
        "hp": 14,
        "attack": 3,
        "defense": 11,
        "dexterity": 12,
        "damage_dice": "1d6+1",
        "xp": 50,
        "loot": ["Purse", "Dagger"],
    },
    "Angry Guard": {
        "hp": 24,
        "attack": 5,
        "defense": 13,
        "dexterity": 11,
        "damage_dice": "1d8+2",
        "xp": 100,
        "loot": ["Guard Armor", "Guard Badge"],
    },
    "Ancient Guardian": {
        "hp": 45,
        "attack": 6,
        "defense": 14,
        "dexterity": 10,
        "damage_dice": "2d8+2",
        "xp": 300,
        "loot": ["Ancient Relic", "Secret Map", "Lost Treasure"],
    },
    "Ghost": {
        "hp": 30,
        "attack": 5,
        "defense": 13,
        "dexterity": 12,
        "damage_dice": "1d8+2",
        "xp": 150,
        "loot": ["Spirit Fragment", "Ghostly Essence"],
    },
    "Stone Golem": {
        "hp": 50,
        "attack": 5,
        "defense": 16,
        "dexterity": 8,
        "damage_dice": "2d8+1",
        "xp": 250,
        "loot": ["Stone Shard", "Ancient Runestone"],
    },
    "Cursed Mummy": {
        "hp": 40,
        "attack": 4,
        "defense": 12,
        "dexterity": 9,
        "damage_dice": "1d8+2",
        "xp": 200,
        "loot": ["Ancient Curse", "Mummy Wraps", "Pharaoh's Gold"],
    },
}


class EncounterGenerator:
    """Generates dynamic encounters based on location and difficulty."""
    
    @staticmethod
    def generate_encounter(
        location: str,
        player_level: int,
        difficulty: str = "normal",
    ) -> List[Enemy]:
        """
        Generate enemies for an encounter.
        
        Args:
            location: Location name or category
            player_level: Player's current level
            difficulty: "easy", "normal", "hard", "deadly"
        
        Returns:
            List of Enemy objects
        """
        # Determine enemy count and difficulty scaling
        difficulty_scaling = {
            "easy": (0.7, 1),
            "normal": (1.0, 1),
            "hard": (1.3, 2),
            "deadly": (1.6, 3),
        }
        
        hp_scale, enemy_count = difficulty_scaling.get(difficulty, (1.0, 1))
        
        # Get possible enemies for this location
        location_lower = location.lower()
        possible_enemies = []
        
        # Try to match location
        for loc_key, enemies in LOCATION_ENEMIES.items():
            if loc_key in location_lower:
                possible_enemies = enemies
                break
        
        # Default to any enemies if no location match
        if not possible_enemies:
            possible_enemies = list(ENEMY_TEMPLATES.keys())
        
        # Select enemies randomly
        enemies = []
        for _ in range(enemy_count):
            enemy_name = random.choice(possible_enemies)
            template = ENEMY_TEMPLATES[enemy_name]
            
            # Scale HP by difficulty and player level
            scaled_hp = int(template["hp"] * hp_scale)
            scaled_attack = template["attack"] + (player_level - 1) // 2
            scaled_defense = template["defense"] + (player_level - 1) // 3
            
            enemy = Enemy(
                name=enemy_name,
                level=max(1, player_level - 1),
                hp=max(5, scaled_hp),
                attack=scaled_attack,
                defense=scaled_defense,
                dexterity=template.get("dexterity", 10),
                damage_dice=template["damage_dice"],
                xp_reward=int(template["xp"] * (1.0 + (player_level - 1) * 0.2)),
                loot=random.sample(template.get("loot", []), min(2, len(template.get("loot", [])))),
            )
            enemies.append(enemy)
        
        return enemies
    
    @staticmethod
    def generate_boss_encounter(location: str, player_level: int) -> List[Enemy]:
        """Generate a boss encounter."""
        boss_templates = {
            "Dark Lord": {
                "hp": 80,
                "attack": 8,
                "defense": 16,
                "dexterity": 12,
                "damage_dice": "3d10+4",
                "xp": 1000,
                "loot": ["Dark Amulet", "Lord's Crown", "Ancient Artifact"],
            },
            "Dragon King": {
                "hp": 100,
                "attack": 9,
                "defense": 17,
                "dexterity": 13,
                "damage_dice": "3d12+5",
                "xp": 1500,
                "loot": ["Dragon Crown", "Dragon Egg", "Infinite Treasure"],
            },
            "Lich": {
                "hp": 70,
                "attack": 7,
                "defense": 15,
                "dexterity": 11,
                "damage_dice": "2d10+4",
                "xp": 800,
                "loot": ["Phylactery", "Spell Tome", "Soul Crystal"],
            },
        }
        
        boss_name = random.choice(list(boss_templates.keys()))
        template = boss_templates[boss_name]
        
        boss = Enemy(
            name=boss_name,
            level=player_level + 2,
            hp=int(template["hp"] * (1.0 + (player_level - 1) * 0.15)),
            attack=template["attack"],
            defense=template["defense"],
            dexterity=template["dexterity"],
            damage_dice=template["damage_dice"],
            xp_reward=int(template["xp"] * (1.0 + (player_level - 1) * 0.2)),
            loot=template["loot"],
        )
        
        return [boss]
    
    @staticmethod
    def get_random_enemy(player_level: int) -> Enemy:
        """Get a single random enemy scaled to player level."""
        enemy_name = random.choice(list(ENEMY_TEMPLATES.keys()))
        template = ENEMY_TEMPLATES[enemy_name]
        
        scaled_hp = int(template["hp"] * (1.0 + (player_level - 1) * 0.1))
        scaled_attack = template["attack"] + (player_level - 1) // 2
        
        return Enemy(
            name=enemy_name,
            level=max(1, player_level - 1),
            hp=max(5, scaled_hp),
            attack=scaled_attack,
            defense=template["defense"],
            dexterity=template.get("dexterity", 10),
            damage_dice=template["damage_dice"],
            xp_reward=int(template["xp"] * (1.0 + (player_level - 1) * 0.2)),
            loot=random.sample(template.get("loot", []), min(1, len(template.get("loot", [])))),
        )
