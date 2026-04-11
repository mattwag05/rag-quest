"""Combat system for RAG-Quest with D&D-style mechanics."""

import random
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


class DamageType(Enum):
    """Types of damage."""
    PHYSICAL = "physical"
    MAGICAL = "magical"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"
    HOLY = "holy"


@dataclass
class DiceRoll:
    """D&D-style dice rolling: d4, d6, d8, d10, d12, d20."""
    
    dice_type: int  # 4, 6, 8, 10, 12, 20
    count: int = 1
    modifier: int = 0
    
    def roll(self) -> int:
        """Roll the dice and return the total."""
        total = sum(random.randint(1, self.dice_type) for _ in range(self.count))
        return total + self.modifier
    
    @staticmethod
    def d4(count: int = 1, modifier: int = 0) -> int:
        """Roll d4."""
        return DiceRoll(4, count, modifier).roll()
    
    @staticmethod
    def d6(count: int = 1, modifier: int = 0) -> int:
        """Roll d6."""
        return DiceRoll(6, count, modifier).roll()
    
    @staticmethod
    def d8(count: int = 1, modifier: int = 0) -> int:
        """Roll d8."""
        return DiceRoll(8, count, modifier).roll()
    
    @staticmethod
    def d10(count: int = 1, modifier: int = 0) -> int:
        """Roll d10."""
        return DiceRoll(10, count, modifier).roll()
    
    @staticmethod
    def d12(count: int = 1, modifier: int = 0) -> int:
        """Roll d12."""
        return DiceRoll(12, count, modifier).roll()
    
    @staticmethod
    def d20(modifier: int = 0) -> int:
        """Roll d20 (for attacks/saves)."""
        return DiceRoll(20, 1, modifier).roll()


class Ability:
    """A special combat ability."""
    
    def __init__(
        self,
        name: str,
        description: str,
        damage_dice: str,
        range_type: str = "melee",
        uses_per_combat: int = 3,
        cooldown: int = 0,
    ):
        self.name = name
        self.description = description
        self.damage_dice = damage_dice  # e.g., "2d8+3"
        self.range_type = range_type  # "melee", "ranged", "aoe"
        self.uses_per_combat = uses_per_combat
        self.uses_remaining = uses_per_combat
        self.cooldown = cooldown
        self.turns_until_ready = 0
    
    def reset(self):
        """Reset ability for a new combat."""
        self.uses_remaining = self.uses_per_combat
        self.turns_until_ready = 0
    
    def use(self) -> bool:
        """Use the ability if available."""
        if self.uses_remaining > 0 and self.turns_until_ready == 0:
            self.uses_remaining -= 1
            self.turns_until_ready = self.cooldown
            return True
        return False
    
    def tick(self):
        """Reduce cooldown by 1 turn."""
        if self.turns_until_ready > 0:
            self.turns_until_ready -= 1


class Enemy:
    """An enemy in combat."""
    
    def __init__(
        self,
        name: str,
        level: int = 1,
        hp: int = 20,
        attack: int = 5,
        defense: int = 10,
        dexterity: int = 10,
        damage_dice: str = "1d6",
        xp_reward: int = 100,
        loot: Optional[List[str]] = None,
        abilities: Optional[List[Ability]] = None,
    ):
        self.name = name
        self.level = level
        self.max_hp = hp
        self.current_hp = hp
        self.attack_bonus = attack
        self.defense_ac = defense
        self.dexterity = dexterity
        self.damage_dice = damage_dice
        self.xp_reward = xp_reward
        self.loot = loot or []
        self.abilities = abilities or []
        self.is_alive = True
    
    def take_damage(self, damage: int) -> bool:
        """Apply damage to enemy. Returns True if killed."""
        self.current_hp -= damage
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive = False
            return True
        return False
    
    def heal(self, amount: int):
        """Heal the enemy."""
        self.current_hp = min(self.current_hp + amount, self.max_hp)
    
    def get_status(self) -> str:
        """Get a status string."""
        return f"{self.name} ({self.current_hp}/{self.max_hp} HP)"


class CombatTurn:
    """Represents one turn in combat."""
    
    def __init__(self, actor_name: str, is_player: bool):
        self.actor_name = actor_name
        self.is_player = is_player
        self.action = None
        self.target = None
        self.damage_dealt = 0
        self.hits = False
        self.critical_hit = False
        self.description = ""


class CombatEncounter:
    """Manages a single combat encounter."""
    
    def __init__(
        self,
        player_character,
        enemies: List[Enemy],
    ):
        self.player = player_character
        self.enemies = enemies
        self.turn_count = 0
        self.log: List[str] = []
        self.is_active = True
        self.player_initiative = 0
        self.enemy_initiatives = {}
        self.turn_order: List[Tuple[str, bool]] = []  # (actor_name, is_player)
        self.current_turn_index = 0
    
    def start(self):
        """Initialize combat and calculate initiative."""
        self._calculate_initiative()
        self._sort_turn_order()
        self.log.append(f"Combat started! {len(self.enemies)} enemy/enemies appeared!")
        for enemy in self.enemies:
            self.log.append(f"  - {enemy.get_status()}")
    
    def _calculate_initiative(self):
        """Calculate initiative for all combatants."""
        # Player initiative: d20 + dexterity modifier
        dex_mod = (self.player.dexterity - 10) // 2
        self.player_initiative = DiceRoll.d20(dex_mod)
        self.log.append(f"Player initiative: {self.player_initiative}")
        
        # Enemy initiatives
        for enemy in self.enemies:
            dex_mod = (enemy.dexterity - 10) // 2
            initiative = DiceRoll.d20(dex_mod)
            self.enemy_initiatives[enemy.name] = initiative
            self.log.append(f"{enemy.name} initiative: {initiative}")
    
    def _sort_turn_order(self):
        """Sort turn order by initiative (highest first)."""
        order = [("player", True, self.player_initiative)]
        for enemy in self.enemies:
            init = self.enemy_initiatives[enemy.name]
            order.append((enemy.name, False, init))
        
        order.sort(key=lambda x: x[2], reverse=True)
        self.turn_order = [(name, is_player) for name, is_player, _ in order]
    
    def get_turn_order(self) -> List[str]:
        """Get the turn order as a list of names."""
        return [name for name, _ in self.turn_order]
    
    def player_attack(self, enemy_index: int = 0) -> dict:
        """Process a player attack."""
        if enemy_index >= len(self.enemies) or not self.enemies[enemy_index].is_alive:
            enemy_index = 0  # Attack first alive enemy
        
        target = self.enemies[enemy_index]
        dex_mod = (self.player.dexterity - 10) // 2
        attack_roll = DiceRoll.d20(self.player.attack_bonus + dex_mod)
        
        result = {
            "hit": False,
            "damage": 0,
            "critical": False,
            "description": "",
        }
        
        # Check if hit
        if attack_roll >= target.defense_ac:
            result["hit"] = True
            
            # Critical hit on natural 20
            if attack_roll == 20:
                result["critical"] = True
                damage = self._parse_damage_dice(self.player.damage_dice)
                damage *= 2  # Double damage on crit
            else:
                damage = self._parse_damage_dice(self.player.damage_dice)
            
            result["damage"] = damage
            target.take_damage(damage)
            
            if result["critical"]:
                result["description"] = f"CRITICAL HIT! You deal {damage} damage to {target.name}!"
            else:
                result["description"] = f"You hit {target.name} for {damage} damage!"
            
            if not target.is_alive:
                result["description"] += f" {target.name} is defeated!"
        else:
            result["description"] = f"Your attack misses {target.name}!"
        
        self.log.append(result["description"])
        return result
    
    def enemy_attack(self, enemy: Enemy) -> dict:
        """Process an enemy attack on the player."""
        dex_mod = (enemy.dexterity - 10) // 2
        attack_roll = DiceRoll.d20(enemy.attack_bonus + dex_mod)
        
        player_ac = self.player.defense_ac
        result = {
            "hit": False,
            "damage": 0,
            "critical": False,
            "description": "",
        }
        
        # Check if hit
        if attack_roll >= player_ac:
            result["hit"] = True
            
            # Critical hit on natural 20
            if attack_roll == 20:
                result["critical"] = True
                damage = self._parse_damage_dice(enemy.damage_dice)
                damage *= 2
            else:
                damage = self._parse_damage_dice(enemy.damage_dice)
            
            result["damage"] = damage
            self.player.take_damage(damage)
            
            if result["critical"]:
                result["description"] = f"CRITICAL HIT! {enemy.name} deals {damage} damage to you!"
            else:
                result["description"] = f"{enemy.name} hits you for {damage} damage!"
            
            if self.player.current_hp <= 0:
                result["description"] += " You are defeated!"
        else:
            result["description"] = f"{enemy.name}'s attack misses!"
        
        self.log.append(result["description"])
        return result
    
    def resolve_combat(self) -> dict:
        """Resolve the combat encounter."""
        result = {
            "victory": False,
            "defeat": False,
            "xp_earned": 0,
            "loot": [],
            "description": "",
        }
        
        # Check if player or all enemies are dead
        if self.player.current_hp <= 0:
            result["defeat"] = True
            result["description"] = "You have been defeated!"
        elif all(not enemy.is_alive for enemy in self.enemies):
            result["victory"] = True
            result["description"] = "Victory! You have defeated all enemies!"
            
            # Calculate XP and loot
            for enemy in self.enemies:
                result["xp_earned"] += enemy.xp_reward
                result["loot"].extend(enemy.loot)
        
        self.log.append(result["description"])
        return result
    
    @staticmethod
    def _parse_damage_dice(dice_str: str) -> int:
        """Parse a damage dice string like '1d6+2' and roll it."""
        if not dice_str:
            return 1
        
        # Simple parser for "XdY+Z" or "XdY-Z"
        parts = dice_str.lower().split('d')
        if len(parts) != 2:
            return 1
        
        try:
            count = int(parts[0]) or 1
            rest = parts[1]
            
            modifier = 0
            if '+' in rest:
                die_val, mod_val = rest.split('+')
                die_val = int(die_val)
                modifier = int(mod_val)
            elif '-' in rest:
                die_val, mod_val = rest.split('-')
                die_val = int(die_val)
                modifier = -int(mod_val)
            else:
                die_val = int(rest)
            
            return DiceRoll(die_val, count, modifier).roll()
        except:
            return 1
    
    def get_log(self) -> List[str]:
        """Get the combat log."""
        return self.log.copy()
    
    def get_status(self) -> str:
        """Get current combat status."""
        status = f"Player HP: {self.player.current_hp}/{self.player.max_hp}\n"
        for i, enemy in enumerate(self.enemies):
            status += f"{i}. {enemy.get_status()}\n"
        return status


class CombatManager:
    """High-level combat management."""
    
    def __init__(self, narrator=None):
        self.narrator = narrator
        self.current_encounter: Optional[CombatEncounter] = None
    
    def start_combat(
        self,
        player_character,
        enemies: List[Enemy],
    ) -> CombatEncounter:
        """Start a new combat encounter."""
        self.current_encounter = CombatEncounter(player_character, enemies)
        self.current_encounter.start()
        return self.current_encounter
    
    def end_combat(self) -> Optional[dict]:
        """End the current combat and get results."""
        if self.current_encounter:
            result = self.current_encounter.resolve_combat()
            encounter = self.current_encounter
            self.current_encounter = None
            return result, encounter
        return None
    
    def is_in_combat(self) -> bool:
        """Check if currently in combat."""
        return self.current_encounter is not None
