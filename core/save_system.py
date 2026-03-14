"""Save/Load system - JSON-based campaign state persistence."""

import json
import os
from pathlib import Path

from data.unit_types import (
    ALL_RECRUITABLE, GENERAL_ROSTER,
    GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST,
    FACTION_SPECIALTY_UNITS,
)

SAVE_DIR = os.path.join(str(Path.home()), ".2d-total-war")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")
SAVE_VERSION = 2  # Bumped for Phase 2 additions

# Build name -> UnitStats lookup (includes specialty units)
_UNIT_LOOKUP = {u.name: u for u in ALL_RECRUITABLE}
for units in FACTION_SPECIALTY_UNITS.values():
    for u in units:
        _UNIT_LOOKUP[u.name] = u
_GENERAL_LOOKUP = {u.name: u for u in GENERAL_ROSTER}


def _unit_from_name(name):
    """Resolve a unit name to its UnitStats object."""
    return _UNIT_LOOKUP.get(name) or _GENERAL_LOOKUP.get(name)


def save_exists():
    """Check if a save file exists."""
    return os.path.isfile(SAVE_FILE)


def save_campaign(campaign_scene):
    """Serialize the full campaign state to JSON."""
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
        "enemy_armies": [
            _serialize_army(a) for a in campaign_scene.armies
            if not a.is_player
        ],
        # Settlements
        "settlements": [
            _serialize_settlement(s) for s in campaign_scene.settlements
        ],
        # Diplomacy
        "diplomacy": campaign_scene.diplomacy.serialize(),
        # Camera position
        "camera": {
            "x": campaign_scene.camera.x,
            "y": campaign_scene.camera.y,
            "zoom": campaign_scene.camera.zoom,
        },
    }

    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True


def load_campaign():
    """Deserialize campaign state from JSON. Returns a dict for CampaignScene to consume."""
    if not save_exists():
        return None
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
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
    scene.show_recruitment = False
    scene.show_diplomacy = False
    scene.recruitment_settlement = None
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

    # Enemy armies
    for ea in data.get("enemy_armies", []):
        army = _restore_army(ea)
        scene.armies.append(army)

    scene._add_notification = lambda text: scene.notifications.append((text, 300))
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
