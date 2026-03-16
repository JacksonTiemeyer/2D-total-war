"""Save/Load system - JSON-based campaign state persistence."""

import json
import os
from pathlib import Path

from data.unit_types import (
    ALL_RECRUITABLE, GENERAL_ROSTER,
    GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST,
    FACTION_SPECIALTY_UNITS,
    RACE_ROSTER, RACE_HEROES,
)

SAVE_DIR = os.path.join(str(Path.home()), ".2d-total-war")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")
SAVE_VERSION = 2  # Bumped for Phase 2 additions

# Build name -> UnitStats lookup (includes all racial and specialty units)
_UNIT_LOOKUP = {u.name: u for u in ALL_RECRUITABLE}
for units in FACTION_SPECIALTY_UNITS.values():
    for u in units:
        _UNIT_LOOKUP[u.name] = u
for units in RACE_ROSTER.values():
    for u in units:
        _UNIT_LOOKUP[u.name] = u
_GENERAL_LOOKUP = {u.name: u for u in GENERAL_ROSTER}
for heroes in RACE_HEROES.values():
    for u in heroes:
        _GENERAL_LOOKUP[u.name] = u


def _unit_from_name(name):
    """Resolve a unit name to its UnitStats object."""
    return _UNIT_LOOKUP.get(name) or _GENERAL_LOOKUP.get(name)


def save_exists():
    """Check if a save file exists."""
    return os.path.isfile(SAVE_FILE)


def save_campaign(campaign_scene):
    """Serialize the full campaign state to JSON."""
    # B5: Serialize AI controller state alongside armies
    enemy_armies_data = []
    for a in campaign_scene.armies:
        if not a.is_player:
            ad = _serialize_army(a)
            ai = campaign_scene.ai_controllers.get(id(a))
            if ai:
                ad["ai"] = ai.serialize()
            enemy_armies_data.append(ad)

    data = {
        "version": SAVE_VERSION,
        # B1: Real-time campaign state
        "day": campaign_scene.day,
        "day_ticks": campaign_scene.day_ticks,
        "campaign_speed": campaign_scene.campaign_speed,
        "paused": campaign_scene.paused,
        "turn": campaign_scene.turn,
        # B2: Player faction
        "player_faction": campaign_scene.player_faction,
        # Armies
        "player_army": _serialize_army(campaign_scene.player_army),
        "enemy_armies": enemy_armies_data,
        # Settlements
        "settlements": [
            _serialize_settlement(s) for s in campaign_scene.settlements
        ],
        # Diplomacy
        "diplomacy": campaign_scene.diplomacy.serialize(),
        # B8: Roaming manager state
        "roaming": campaign_scene.roaming_manager.serialize(),
        # B3: Quest system
        "quests": campaign_scene.quest_manager.serialize(),
        # B6/D6: General management (loyalty, betrayal, prisoners)
        "generals": campaign_scene.general_manager.serialize(),
        # Camera position
        "camera": {
            "x": campaign_scene.camera.x,
            "y": campaign_scene.camera.y,
            "zoom": campaign_scene.camera.zoom,
        },
    }

    # Phase 3: Player character
    if hasattr(campaign_scene, 'player_character') and campaign_scene.player_character:
        data["player_character"] = campaign_scene.player_character.serialize()

    # Phase 3: Companions
    if hasattr(campaign_scene, 'companion_manager'):
        data["companions"] = campaign_scene.companion_manager.serialize()

    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True


def load_campaign():
    """Deserialize campaign state from JSON. Returns a dict for CampaignScene to consume."""
    if not save_exists():
        return None
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    # Accept version 1 (legacy) and 2 (current)
    if data.get("version", 0) not in (1, 2):
        return None
    return data


def delete_save():
    """Remove the save file."""
    if save_exists():
        os.remove(SAVE_FILE)


def _serialize_army(army):
    """Convert an Army to a serializable dict."""
    return {
        "name": army.name,
        "team": army.team,
        "x": army.x,
        "y": army.y,
        "is_player": army.is_player,
        "gold": army.gold,
        "general_name": army.general_name,
        "general_stats": army.general_stats.name,
        "general_xp": army.general_xp,
        "general_level": army.general_level,
        "squads": [
            {
                "unit_name": sq.unit_stats.name,
                "current_count": sq.current_count,
                "battles_survived": sq.battles_survived,
                "total_kills": sq.total_kills,
            }
            for sq in army.squads
        ],
    }


def _serialize_settlement(settlement):
    """Convert a Settlement to a serializable dict."""
    return {
        "name": settlement.name,
        "x": settlement.x,
        "y": settlement.y,
        "owner": settlement.owner,
        "settlement_type": settlement.settlement_type,
        "garrison_strength": settlement.garrison_strength,
        "available_recruits": [u.name for u in settlement.available_recruits],
    }


def restore_campaign_scene(data):
    """Rebuild a CampaignScene from saved data. Returns a CampaignScene."""
    from campaign.campaign_scene import CampaignScene
    from campaign.army import Army, CampaignSquad
    from campaign.settlement import Settlement
    from campaign.faction import FACTION_ROSTER
    from campaign.diplomacy import DiplomacyManager

    # Create a fresh scene, then override with saved data
    scene = CampaignScene.__new__(CampaignScene)

    # Re-init camera
    from core.camera import Camera
    from core.settings import (
        CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT,
        CAMPAIGN_SPEED_1X, CAMPAIGN_TICKS_PER_DAY,
    )
    scene.camera = Camera(CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT)
    cam_data = data.get("camera", {})
    scene.camera.x = cam_data.get("x", CAMPAIGN_MAP_WIDTH / 2)
    scene.camera.y = cam_data.get("y", CAMPAIGN_MAP_HEIGHT / 2)
    scene.camera.zoom = cam_data.get("zoom", 1.0)

    # B1: Real-time campaign state
    scene.day = data.get("day", data.get("turn", 1))
    scene.day_ticks = data.get("day_ticks", 0)
    scene.campaign_speed = data.get("campaign_speed", CAMPAIGN_SPEED_1X)
    scene.paused = data.get("paused", False)
    scene.turn = data.get("turn", scene.day)

    # B2: Player faction
    scene.player_faction = data.get("player_faction", None)

    # UI state
    scene.selected_settlement = None
    scene.show_diplomacy = False
    scene.pending_battle = None
    scene.settlement_interaction = None

    # Notifications
    scene.notifications = []
    scene.NOTIFICATION_DURATION = 300

    # Fog/territory cache flags
    scene._fog_surface = None
    scene._fog_needs_update = True
    scene._territory_surface = None
    scene._territory_needs_update = True

    # AI timers
    scene._ai_tick_timer = 0
    scene._ai_diplomacy_timer = 0
    scene._income_timer = 0

    # Factions & diplomacy
    scene.factions = FACTION_ROSTER[:]
    scene.diplomacy = DiplomacyManager(scene.factions)
    if "diplomacy" in data:
        scene.diplomacy.deserialize(data["diplomacy"])

    # Restore settlements
    scene.settlements = []
    for sd in data["settlements"]:
        s = Settlement(sd["name"], sd["x"], sd["y"], sd["owner"], sd["settlement_type"])
        s.garrison_strength = sd["garrison_strength"]
        s.available_recruits = [
            _unit_from_name(n) for n in sd.get("available_recruits", [])
            if _unit_from_name(n) is not None
        ]
        scene.settlements.append(s)

    # Restore armies
    scene.armies = []
    # Player army
    pa = data["player_army"]
    scene.player_army = _restore_army(pa)
    scene.armies.append(scene.player_army)

    # Enemy armies + B5: AI controllers
    scene.ai_controllers = {}
    for ea in data.get("enemy_armies", []):
        army = _restore_army(ea)
        scene.armies.append(army)
        # Restore AI controller
        from campaign.ai_controller import ArmyAI, pick_personality
        ai = ArmyAI(army, pick_personality())
        if "ai" in ea:
            ai.deserialize(ea["ai"])
        scene.ai_controllers[id(army)] = ai

    # B8: Roaming manager
    from campaign.roaming import RoamingManager
    scene.roaming_manager = RoamingManager()
    if "roaming" in data:
        scene.roaming_manager.deserialize(data["roaming"])

    # B3: Quest system
    from campaign.quest import QuestManager
    scene.quest_manager = QuestManager()
    scene.show_quest_log = False
    if "quests" in data:
        scene.quest_manager.deserialize(data["quests"])

    # B6/D6: General management system
    from campaign.generals import GeneralManager
    scene.general_manager = GeneralManager()
    scene.show_persuasion = False
    scene.persuasion_target = None
    scene.show_prisoners = False
    scene.prisoner_action_msg = None
    scene.prisoner_action_timer = 0
    if "generals" in data:
        scene.general_manager.deserialize(data["generals"])
    else:
        # Register existing generals if loading from older save
        for army in scene.armies:
            if not army.is_player:
                ai = scene.ai_controllers.get(id(army))
                personality = ai.personality if ai else "cautious"
                scene.general_manager.register_general(
                    army.general_name, army.team, personality, army.general_level)

    # D1: Terrain zones (must match CampaignScene.__init__)
    scene._terrain_forests = [
        (200, 400, 120), (1000, 200, 80), (700, 800, 100),
        (1500, 900, 90), (1900, 300, 70), (1100, 700, 110),
        (900, 900, 85), (600, 1400, 95), (2800, 1500, 80),
        (3300, 400, 75), (1700, 2200, 90),
    ]
    scene._terrain_mountains = [
        (1100, 150, 60), (1800, 600, 50), (300, 900, 45),
        (1600, 100, 55), (3000, 400, 50), (2500, 1400, 45),
        (500, 1800, 40),
    ]
    scene._terrain_deserts = [
        (2800, 1900, 200), (3200, 1700, 150), (3000, 2100, 120),
    ]
    scene._terrain_water = [
        (1200, 2700, 250), (800, 2500, 150), (1600, 2700, 180),
    ]

    # D5: Tournament state
    scene.tournament_towns = {}
    scene.active_tournament = None
    scene.show_tournament = False

    # Phase 3: Restore player character
    if "player_character" in data:
        from campaign.player import PlayerCharacter
        scene.player_character = PlayerCharacter.deserialize(data["player_character"])
        # Also update army name
        scene.player_army.general_name = scene.player_character.name

    # Phase 3: Restore companions
    if "companions" in data:
        from campaign.companion import CompanionManager
        if not hasattr(scene, 'companion_manager'):
            scene.companion_manager = CompanionManager()
        scene.companion_manager.deserialize(data["companions"])

    # UI state missing from original restore
    scene.show_army_panel = False

    scene._add_notification = lambda text: scene.notifications.append((text, scene.NOTIFICATION_DURATION))
    scene._add_notification("Campaign loaded!")

    return scene


def _restore_army(ad):
    """Rebuild an Army from saved data."""
    from campaign.army import Army, CampaignSquad

    army = Army(ad["name"], ad["team"], ad["x"], ad["y"], ad.get("is_player", False))
    army.gold = ad.get("gold", 0)
    army.general_name = ad.get("general_name", ad["name"])
    gen_stats = _GENERAL_LOOKUP.get(ad.get("general_stats", "Commander"))
    army.general_stats = gen_stats or GENERAL_COMMANDER
    army.general_xp = ad.get("general_xp", 0)
    army.general_level = ad.get("general_level", 1)

    army.squads = []
    for sq_data in ad.get("squads", []):
        unit = _unit_from_name(sq_data["unit_name"])
        if unit is None:
            continue
        csq = CampaignSquad(unit, sq_data.get("current_count"))
        csq.battles_survived = sq_data.get("battles_survived", 0)
        csq.total_kills = sq_data.get("total_kills", 0)
        army.squads.append(csq)

    return army
