#!/usr/bin/env python3
"""RAG-Quest v0.5.0 End-to-End Playtest"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag_quest.engine.character import Character, CharacterClass, Race
from rag_quest.engine.world import World
from rag_quest.engine.inventory import Inventory, Item
from rag_quest.engine.quests import Quest, QuestLog, QuestObjective, QuestReward, QuestStatus, ObjectiveType
from rag_quest.engine.party import Party, PartyMember, CombatStyle, DialogueStyle
from rag_quest.engine.relationships import RelationshipManager
from rag_quest.engine.events import WorldEvent, EventManager, EventType
from rag_quest.engine.combat import Enemy, CombatEncounter
from rag_quest.engine.achievements import AchievementManager
from rag_quest.engine.dungeon import DungeonGenerator, DifficultyLevel
from rag_quest.saves.manager import SaveManager
from rag_quest.worlds.exporter import WorldExporter
from rag_quest.worlds.importer import WorldImporter
from rag_quest.multiplayer.session import MultiplayerSession
from rag_quest.multiplayer.trading import TradeManager, Trade, TradeStatus

test_log = []
passed = 0
failed = 0
bugs = []

def test(section, name, ok, details=""):
    global passed, failed
    status = "PASS" if ok else "FAIL"
    msg = f"[{section:15}] {name:40} {status}"
    if details:
        msg += f" ({details})"
    test_log.append(msg)
    if ok:
        passed += 1
    else:
        failed += 1
    print(msg)

def bug(section, desc, severity="P2"):
    bugs.append(f"[{severity}] {section}: {desc}")
    print(f"  BUG: {desc}")

print("\n" + "="*80)
print("RAG-QUEST v0.5.0 END-TO-END PLAYTEST")
print("="*80 + "\n")

# SECTION 1: CHARACTER CREATION
print("SECTION 1: CHARACTER & WORLD SETUP")
print("-" * 80)

try:
    player = Character(name="Kael", race=Race.HUMAN, character_class=CharacterClass.FIGHTER)
    test("Setup", "Create character", player is not None)
    test("Setup", "Character serialization", bool(player.to_dict()))
except Exception as e:
    test("Setup", "Create character", False, str(e))
    player = None

# Test all races
for race in [Race.ELF, Race.DWARF, Race.HALFLING, Race.ORC]:
    try:
        c = Character(name=f"Test", race=race, character_class=CharacterClass.FIGHTER)
        test("Setup", f"Create {race.value}", c is not None)
    except Exception as e:
        test("Setup", f"Create {race.value}", False, str(e))

# Test all classes
for cls in [CharacterClass.ROGUE, CharacterClass.MAGE, CharacterClass.CLERIC, CharacterClass.RANGER]:
    try:
        c = Character(name=f"Test", race=Race.HUMAN, character_class=cls)
        test("Setup", f"Create {cls.value}", c is not None)
    except Exception as e:
        test("Setup", f"Create {cls.value}", False, str(e))

try:
    world = World(name="Test World", setting="Fantasy", tone="Dark")
    test("Setup", "Create world", world is not None)
    test("Setup", "World serialization", bool(world.to_dict()))
except Exception as e:
    test("Setup", "Create world", False, str(e))
    world = None

# SECTION 2: ENGINE SYSTEMS
print("\nSECTION 2: ENGINE SYSTEMS INITIALIZATION")
print("-" * 80)

try:
    inv = Inventory(max_weight=100)
    test("Engines", "Inventory init", inv is not None)
    test("Engines", "Inventory serialization", bool(inv.to_dict()))
except Exception as e:
    test("Engines", "Inventory init", False, str(e))
    inv = None

try:
    ql = QuestLog()
    test("Engines", "QuestLog init", ql is not None)
    test("Engines", "QuestLog serialization", bool(ql.to_dict()))
except Exception as e:
    test("Engines", "QuestLog init", False, str(e))
    ql = None

try:
    party = Party(max_size=4)
    test("Engines", "Party init", party is not None)
    test("Engines", "Party serialization", bool(party.to_dict()))
except Exception as e:
    test("Engines", "Party init", False, str(e))
    party = None

try:
    rel = RelationshipManager()
    test("Engines", "RelationshipManager init", rel is not None)
    test("Engines", "RelationshipManager serialization", bool(rel.to_dict()))
except Exception as e:
    test("Engines", "RelationshipManager init", False, str(e))
    rel = None

try:
    em = EventManager()
    test("Engines", "EventManager init", em is not None)
    test("Engines", "EventManager serialization", bool(em.to_dict()))
except Exception as e:
    test("Engines", "EventManager init", False, str(e))
    em = None

try:
    am = AchievementManager()
    test("Engines", "AchievementManager init", am is not None)
    test("Engines", "AchievementManager serialization", bool(am.to_dict()))
except Exception as e:
    test("Engines", "AchievementManager init", False, str(e))
    am = None

# SECTION 3: WORLD STATE
print("\nSECTION 3: WORLD EXPLORATION & STATE")
print("-" * 80)

if world:
    try:
        world.add_visited_location("Tavern")
        world.add_visited_location("Forest")
        test("World", "Add locations", len(world.visited_locations) == 2)
    except Exception as e:
        test("World", "Add locations", False, str(e))

    try:
        world.advance_time()
        test("World", "Advance time", world.day_number >= 0)
    except Exception as e:
        test("World", "Advance time", False, str(e))

    try:
        world.add_met_npc("Gandalf")
        world.add_met_npc("Legolas")
        test("World", "Track NPCs", len(world.npcs_met) == 2)
    except Exception as e:
        test("World", "Track NPCs", False, str(e))

    try:
        ctx = world.get_context()
        test("World", "Get context", ctx and len(ctx) > 0)
    except Exception as e:
        test("World", "Get context", False, str(e))

# SECTION 4: COMBAT
print("\nSECTION 4: COMBAT SYSTEM")
print("-" * 80)

if player:
    try:
        enemy = Enemy(name="Goblin", level=1, hp=20, attack=5, defense=10)
        test("Combat", "Create enemy", enemy is not None)
        # Note: Enemy doesn't have to_dict, that's OK
        test("Combat", "Enemy basic attributes", enemy.hp == 20 and enemy.level == 1)
    except Exception as e:
        test("Combat", "Create enemy", False, str(e))
        enemy = None

    if enemy:
        try:
            enemies = [enemy]
            enc = CombatEncounter(player_character=player, enemies=enemies)
            test("Combat", "Create encounter", enc is not None)
        except Exception as e:
            test("Combat", "Create encounter", False, str(e))
            enc = None

        if enc:
            try:
                initiative = enc.roll_initiative()
                test("Combat", "Roll initiative", isinstance(initiative, tuple) and len(initiative) == 2)
            except Exception as e:
                test("Combat", "Roll initiative", False, str(e))

            try:
                attack = enc.player_attack()
                test("Combat", "Attack roll", 1 <= attack <= 20)
            except Exception as e:
                test("Combat", "Attack roll", False, str(e))

            try:
                damage = enc.calculate_damage("player")
                test("Combat", "Calculate damage", damage >= 0)
            except Exception as e:
                test("Combat", "Calculate damage", False, str(e))

            try:
                result = enc.resolve()
                test("Combat", "Resolve encounter", result in ["player_victory", "enemy_victory", "ongoing"])
            except Exception as e:
                test("Combat", "Resolve encounter", False, str(e))

# SECTION 5: CHARACTER PROGRESSION
print("\nSECTION 5: CHARACTER PROGRESSION")
print("-" * 80)

if player:
    try:
        initial_level = player.level
        # Experience system - check what attributes exist
        player.experience = 1000
        test("Progression", "Set experience", player.experience == 1000)
        # Note: Level up may require specific thresholds
    except Exception as e:
        test("Progression", "Set experience", False, str(e))

    try:
        abilities = player.unlocked_abilities
        test("Progression", "Get abilities", isinstance(abilities, list))
    except Exception as e:
        test("Progression", "Get abilities", False, str(e))

    try:
        # Test attributes
        test("Progression", "Character attributes", player.strength >= 0 and player.level >= 1)
    except Exception as e:
        test("Progression", "Character attributes", False, str(e))

# SECTION 6: PARTY SYSTEM
print("\nSECTION 6: PARTY & RELATIONSHIPS")
print("-" * 80)

if party:
    try:
        m1 = PartyMember(name="Legolas", race="Elf", character_class="Ranger", loyalty=80)
        m2 = PartyMember(name="Gimli", race="Dwarf", character_class="Fighter", loyalty=70)
        party.add_member(m1)
        party.add_member(m2)
        test("Party", "Add members", len(party.members) == 2)
    except Exception as e:
        test("Party", "Add members", False, str(e))
        bug("Party", f"PartyMember API mismatch: {e}")

    try:
        test("Party", "Members loyalty", party.members[0].loyalty == 80 if party.members else False)
    except Exception as e:
        test("Party", "Members loyalty", False, str(e))

if rel:
    try:
        rel.add_npc("Gandalf", "Wizard")
        rel.add_npc("Legolas", "Ranger")
        test("Relationships", "Add NPCs", len(rel.npcs) >= 2)
    except Exception as e:
        test("Relationships", "Add NPCs", False, str(e))

    try:
        # Check what methods exist
        methods = [m for m in dir(rel) if not m.startswith('_')]
        has_change = 'change_disposition' in methods
        has_faction = 'create_faction' in methods
        if not has_change or not has_faction:
            bug("Relationships", f"Missing methods. Has: {methods}")
        test("Relationships", "Disposition method exists", has_change)
        test("Relationships", "Faction method exists", has_faction)
    except Exception as e:
        test("Relationships", "Methods check", False, str(e))

# SECTION 7: QUESTS
print("\nSECTION 7: QUEST SYSTEM")
print("-" * 80)

if ql:
    try:
        reward = QuestReward(gold=100, experience=50)
        quest = Quest(
            title="Rescue Princess",
            description="Save the princess",
            reward=reward
        )
        ql.add_quest(quest)
        test("Quests", "Create and add quest", len(ql.quests) > 0)
    except Exception as e:
        test("Quests", "Create and add quest", False, str(e))
        bug("Quests", f"Quest API: {e}")

    try:
        active = ql.get_active_quests()
        test("Quests", "Get active quests", isinstance(active, list))
    except Exception as e:
        test("Quests", "Get active quests", False, str(e))

# SECTION 8: EVENTS
print("\nSECTION 8: WORLD EVENTS")
print("-" * 80)

if em:
    # Use actual EventType values
    event_types = [EventType.WEATHER, EventType.COMBAT, EventType.CONFLICT]
    for et in event_types:
        try:
            evt = WorldEvent(
                title=f"Event {et.value}",
                description="Test event",
                event_type=et
            )
            em.add_event(evt)
            test("Events", f"Create {et.value} event", evt is not None)
        except Exception as e:
            test("Events", f"Create {et.value} event", False, str(e))

    try:
        active = em.get_active_events()
        test("Events", "Get active events", isinstance(active, list))
    except Exception as e:
        test("Events", "Get active events", False, str(e))

# SECTION 9: ACHIEVEMENTS
print("\nSECTION 9: ACHIEVEMENTS")
print("-" * 80)

if am:
    try:
        achievements = am.get_all_achievements()
        test("Achievements", "Load achievements", len(achievements) > 0, f"{len(achievements)} loaded")
    except Exception as e:
        test("Achievements", "Load achievements", False, str(e))

    try:
        if player:
            am.check_achievements(player=player)
        unlocked = am.get_unlocked_achievements()
        test("Achievements", "Check & get unlocked", isinstance(unlocked, list))
    except Exception as e:
        test("Achievements", "Check & get unlocked", False, str(e))

# SECTION 10: DUNGEONS
print("\nSECTION 10: PROCEDURAL DUNGEONS")
print("-" * 80)

try:
    dg = DungeonGenerator()
    for difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM]:
        try:
            dungeon = dg.generate_level(difficulty=difficulty)
            has_rooms = "rooms" in dungeon and len(dungeon["rooms"]) > 0
            has_map = "map" in dungeon
            test("Dungeons", f"Generate {difficulty.value}", has_rooms, f"{len(dungeon.get('rooms', []))} rooms")
            test("Dungeons", f"Generate map {difficulty.value}", has_map)
        except Exception as e:
            test("Dungeons", f"Generate {difficulty.value}", False, str(e))
except Exception as e:
    test("Dungeons", "DungeonGenerator init", False, str(e))

# SECTION 11: SAVES
print("\nSECTION 11: SAVE/LOAD SYSTEM")
print("-" * 80)

try:
    sm = SaveManager()
    test("Saves", "SaveManager init", sm is not None)
except Exception as e:
    test("Saves", "SaveManager init", False, str(e))
    sm = None

if sm and player and world:
    try:
        state = {
            "character": player.to_dict(),
            "world": world.to_dict(),
            "inventory": inv.to_dict() if inv else {},
        }
        sm.save_game("Test World", 0, state, "Kael")
        test("Saves", "Save game", True)
    except Exception as e:
        test("Saves", "Save game", False, str(e))

    try:
        saves = sm.list_saves("Test World")
        test("Saves", "List saves", len(saves) > 0, f"{len(saves)} saves")
    except Exception as e:
        test("Saves", "List saves", False, str(e))

    try:
        loaded = sm.load_game("Test World", 0)
        test("Saves", "Load game", loaded and "character" in loaded)
    except Exception as e:
        test("Saves", "Load game", False, str(e))

# SECTION 12: WORLD EXPORT/IMPORT
print("\nSECTION 12: WORLD EXPORT/IMPORT")
print("-" * 80)

if world:
    try:
        exp = WorldExporter()
        path = Path("/tmp/test_world.rqworld")
        exp.export_world(world=world, character_name="Kael", output_path=str(path))
        test("Worlds", "Export world", path.exists(), f"{path.stat().st_size if path.exists() else 0} bytes")
    except Exception as e:
        test("Worlds", "Export world", False, str(e))

    if path.exists():
        try:
            imp = WorldImporter()
            imported = imp.import_world(str(path))
            test("Worlds", "Import world", imported and imported.name == world.name)
        except Exception as e:
            test("Worlds", "Import world", False, str(e))

# SECTION 13: MULTIPLAYER
print("\nSECTION 13: MULTIPLAYER")
print("-" * 80)

try:
    mp = MultiplayerSession(world_name="Test World", max_players=4)
    test("Multiplayer", "Create session", mp is not None)
except Exception as e:
    test("Multiplayer", "Create session", False, str(e))
    mp = None

if mp:
    try:
        p1 = Character(name="Hero1", race=Race.HUMAN, character_class=CharacterClass.FIGHTER)
        p2 = Character(name="Hero2", race=Race.ELF, character_class=CharacterClass.MAGE)
        mp.add_player(p1)
        mp.add_player(p2)
        test("Multiplayer", "Add players", len(mp.players) == 2)
    except Exception as e:
        test("Multiplayer", "Add players", False, str(e))

    try:
        mp.sync_state()
        test("Multiplayer", "Sync state", True)
    except Exception as e:
        test("Multiplayer", "Sync state", False, str(e))

# SECTION 14: FULL INTEGRATION
print("\nSECTION 14: FULL INTEGRATION")
print("-" * 80)

if player and world:
    try:
        full = {
            "character": player.to_dict(),
            "world": world.to_dict(),
            "inventory": inv.to_dict() if inv else {},
            "quests": ql.to_dict() if ql else {},
            "party": party.to_dict() if party else {},
            "relationships": rel.to_dict() if rel else {},
            "events": em.to_dict() if em else {},
            "achievements": am.to_dict() if am else {},
        }
        json_str = json.dumps(full)
        test("Integration", "Serialize full state", len(json_str) > 0, f"{len(json_str)} bytes")
    except Exception as e:
        test("Integration", "Serialize full state", False, str(e))

    try:
        full2 = json.loads(json_str)
        test("Integration", "Deserialize full state", "character" in full2)
    except Exception as e:
        test("Integration", "Deserialize full state", False, str(e))

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

total = passed + failed
success_rate = (100 * passed // total) if total > 0 else 0

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {success_rate}%")

print(f"\nBugs Found: {len(bugs)}")
if bugs:
    print("\nBug List:")
    for b in bugs:
        print(f"  {b}")

# Write log
log_file = Path(__file__).parent / "v050_test_log.txt"
with open(log_file, "w") as f:
    f.write("RAG-Quest v0.5.0 End-to-End Playtest Log\n")
    f.write("="*80 + "\n\n")
    for line in test_log:
        f.write(line + "\n")
    f.write("\n" + "="*80 + "\n")
    f.write("SUMMARY\n")
    f.write("="*80 + "\n")
    f.write(f"Total: {total}\nPassed: {passed}\nFailed: {failed}\nRate: {success_rate}%\n")
    if bugs:
        f.write(f"\nBugs ({len(bugs)}):\n")
        for b in bugs:
            f.write(f"  {b}\n")

print(f"\nLog: {log_file}")
sys.exit(0 if failed == 0 else 1)
