"""Roaming non-faction armies - bandits, cultists, mercenaries, etc. (B8).

Spawns roaming armies in wilderness, manages stronghold escalation,
and fires random campaign events.
"""

import random
import math
from core.utils import distance
from campaign.faction import (
    TEAM_BANDITS, TEAM_CULTISTS, TEAM_CANNIBALS,
    TEAM_DESERTERS, TEAM_MERCENARY,
    TEAM_GOBLINS,
)

# --- Roaming group definitions ---

ROAMING_TYPES = {
    TEAM_BANDITS: {
        "name_pool": ["Bandit Gang", "Highwaymen", "Road Thieves", "Outlaws",
                       "Rogue Band", "Marauders"],
        "min_soldiers": 20, "max_soldiers": 60,
        "behavior": "ambush",  # lurk near roads/settlements
        "loot_gold": (20, 80),
        "spawn_weight": 55,
    },
    TEAM_CULTISTS: {
        "name_pool": ["Dark Cult", "Shadow Sect", "Dread Followers",
                       "Blood Acolytes", "Doom Heralds"],
        "min_soldiers": 30, "max_soldiers": 80,
        "behavior": "raid",  # raid villages
        "loot_gold": (30, 100),
        "spawn_weight": 22,
    },
    TEAM_CANNIBALS: {
        "name_pool": ["Flesh Eaters", "Mountain Maneaters", "The Hungry",
                       "Forest Lurkers"],
        "min_soldiers": 15, "max_soldiers": 40,
        "behavior": "ambush",
        "loot_gold": (10, 40),
        "spawn_weight": 15,
    },
    TEAM_DESERTERS: {
        "name_pool": ["Deserter Band", "Broken Company", "The Forsaken",
                       "Lost Soldiers"],
        "min_soldiers": 20, "max_soldiers": 50,
        "behavior": "wander",
        "loot_gold": (15, 50),
        "spawn_weight": 18,
    },
    TEAM_MERCENARY: {
        "name_pool": ["Sellsword Company", "Bronze Hawks", "Iron Wolves",
                       "Free Lances", "Golden Company"],
        "min_soldiers": 40, "max_soldiers": 100,
        "behavior": "wander",  # travel between settlements
        "loot_gold": (0, 0),  # can be hired, not looted
        "spawn_weight": 12,
    },
    TEAM_GOBLINS: {
        "name_pool": ["Goblin Raiders", "Sniveler Mob", "Moonclaw Pack",
                       "Crooked Knives", "Goblin Wolf Pack"],
        "min_soldiers": 25, "max_soldiers": 70,
        "behavior": "ambush",
        "loot_gold": (15, 60),
        "spawn_weight": 20,
    },
}


# --- Stronghold escalation stages ---

class StrongholdStage:
    WARBAND = "warband"       # Default spawned group
    ENCAMPMENT = "encampment"  # Claims a location, spawns patrols
    STRONGHOLD = "stronghold"  # Fortified, must be assaulted


class Stronghold:
    """A roaming group's base that has escalated beyond a simple warband."""

    def __init__(self, x, y, team, stage=StrongholdStage.WARBAND):
        self.x = x
        self.y = y
        self.team = team
        self.stage = stage
        self.wins = 0  # battles won
        self.garrison_strength = 30 if stage == StrongholdStage.ENCAMPMENT else 80
        self.patrol_timer = 0
        self.name = self._generate_name()

    def _generate_name(self):
        prefixes = {
            TEAM_BANDITS: "Bandit",
            TEAM_CULTISTS: "Cult",
            TEAM_CANNIBALS: "Cannibal",
            TEAM_DESERTERS: "Deserter",
            TEAM_GOBLINS: "Goblin",
        }
        prefix = prefixes.get(self.team, "Outlaw")
        if self.stage == StrongholdStage.ENCAMPMENT:
            return f"{prefix} Camp"
        elif self.stage == StrongholdStage.STRONGHOLD:
            return f"{prefix} Stronghold"
        return f"{prefix} Warband"

    def can_escalate(self):
        if self.stage == StrongholdStage.WARBAND and self.wins >= 2:
            return StrongholdStage.ENCAMPMENT
        if self.stage == StrongholdStage.ENCAMPMENT and self.wins >= 5:
            return StrongholdStage.STRONGHOLD
        return None

    def escalate(self):
        new_stage = self.can_escalate()
        if new_stage:
            self.stage = new_stage
            self.name = self._generate_name()
            if new_stage == StrongholdStage.ENCAMPMENT:
                self.garrison_strength = 50
            elif new_stage == StrongholdStage.STRONGHOLD:
                self.garrison_strength = 120
            return True
        return False

    def serialize(self):
        return {
            "x": self.x, "y": self.y, "team": self.team,
            "stage": self.stage, "wins": self.wins,
            "garrison_strength": self.garrison_strength,
            "name": self.name,
        }

    @staticmethod
    def deserialize(data):
        s = Stronghold(data["x"], data["y"], data["team"], data["stage"])
        s.wins = data.get("wins", 0)
        s.garrison_strength = data.get("garrison_strength", 30)
        s.name = data.get("name", s.name)
        return s


# --- Random Events ---

class CampaignEvent:
    """A random campaign event that triggers effects."""

    def __init__(self, name, description, effect_fn):
        self.name = name
        self.description = description
        self.effect_fn = effect_fn  # callable(campaign_scene) -> str notification


def _event_bandit_uprising(scene):
    """Spawn a large bandit army."""
    from campaign.army import create_enemy_army
    x = random.randint(200, 3800)
    y = random.randint(200, 2800)
    army = create_enemy_army("Bandit Horde", TEAM_BANDITS, x, y, difficulty=3)
    scene.armies.append(army)
    scene._get_ai(army)  # ensure AI controller exists
    return "A massive bandit horde has risen in the wilderness!"


def _event_plague(scene):
    """Reduce garrison in a random settlement."""
    if not scene.settlements:
        return None
    s = random.choice(scene.settlements)
    s.garrison_strength = max(10, int(s.garrison_strength * 0.5))
    return f"Plague strikes {s.name}! Garrison halved."


def _event_harvest_festival(scene):
    """Boost gold for player."""
    scene.player_army.gold += 100
    return "Harvest Festival! +100 gold from celebrations."


def _event_merchant_caravan(scene):
    """Free gold from a passing caravan."""
    gold = random.randint(30, 80)
    scene.player_army.gold += gold
    return f"A merchant caravan passes by. You trade goods for +{gold} gold."


def _event_refugee_crisis(scene):
    """Add free soldiers to player army."""
    from campaign.army import CampaignSquad
    from data.unit_types import MILITIA
    if scene.player_army.can_recruit:
        scene.player_army.add_squad(MILITIA)
        return "Refugees join your army as militia!"
    return "Refugees flee through your territory."


def _event_desertion_wave(scene):
    """Random AI army loses soldiers."""
    ai_armies = [a for a in scene.armies if not a.is_player and a.squads]
    if not ai_armies:
        return None
    army = random.choice(ai_armies)
    for sq in army.squads:
        loss = max(1, int(sq.current_count * random.uniform(0.1, 0.2)))
        sq.current_count = max(1, sq.current_count - loss)
    from campaign.faction import FACTION_BY_TEAM
    f = FACTION_BY_TEAM.get(army.team)
    name = f.name if f else "An"
    return f"Desertion wave! {name} army '{army.name}' loses soldiers."


RANDOM_EVENTS = [
    CampaignEvent("Bandit Uprising", "Bandits grow bold", _event_bandit_uprising),
    CampaignEvent("Plague", "Disease spreads", _event_plague),
    CampaignEvent("Harvest Festival", "Celebrations!", _event_harvest_festival),
    CampaignEvent("Merchant Caravan", "Traders pass by", _event_merchant_caravan),
    CampaignEvent("Refugee Crisis", "Displaced people", _event_refugee_crisis),
    CampaignEvent("Desertion Wave", "Soldiers flee", _event_desertion_wave),
]


class RoamingManager:
    """Manages spawning, despawning, and escalation of roaming armies."""

    # Max roaming armies on the map at once
    MAX_ROAMING = 22
    # Days between spawn checks
    SPAWN_INTERVAL = 3
    # Event check interval (days)
    EVENT_INTERVAL = 10
    # Chance of random event per check
    EVENT_CHANCE = 0.3

    def __init__(self):
        self.strongholds = []
        self.last_spawn_day = 0
        self.last_event_day = 0

    def update(self, day, armies, settlements, diplomacy, scene):
        """Called each day from campaign scene."""
        # Spawn new roaming armies
        if day - self.last_spawn_day >= self.SPAWN_INTERVAL:
            self.last_spawn_day = day
            self._try_spawn(armies, settlements, scene)

        # Check for random events
        if day - self.last_event_day >= self.EVENT_INTERVAL:
            self.last_event_day = day
            self._try_random_event(scene)

        # Update stronghold escalation
        self._update_strongholds(scene)

    def _try_spawn(self, armies, settlements, scene):
        """Spawn roaming armies in wilderness areas."""
        from campaign.army import create_enemy_army

        roaming_count = sum(1 for a in armies if a.team in ROAMING_TYPES)
        if roaming_count >= self.MAX_ROAMING:
            return

        # Pick a random roaming type with extra pressure on hostile wilderness groups.
        roaming_teams = list(ROAMING_TYPES.keys())
        weights = [ROAMING_TYPES[team].get("spawn_weight", 10) for team in roaming_teams]
        team = random.choices(roaming_teams, weights=weights, k=1)[0]
        info = ROAMING_TYPES[team]

        # Find a spawn location away from settlements (6000x4500 map)
        from core.settings import CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT
        for _ in range(10):
            x = random.randint(100, CAMPAIGN_MAP_WIDTH - 100)
            y = random.randint(100, CAMPAIGN_MAP_HEIGHT - 100)
            too_close = any(distance(x, y, s.x, s.y) < 150 for s in settlements)
            if not too_close:
                break

        name = random.choice(info["name_pool"])
        difficulty = 1
        if team == TEAM_MERCENARY:
            difficulty = 2
        army = create_enemy_army(name, team, x, y, difficulty)

        # Scale soldiers to type range
        target = random.randint(info["min_soldiers"], info["max_soldiers"])
        while army.total_soldiers < target and len(army.squads) < 6:
            from data.unit_types import MILITIA, SWORDSMEN
            army.add_squad(random.choice([MILITIA, SWORDSMEN]))

        scene.armies.append(army)
        scene._get_ai(army)  # register AI controller

    def _try_random_event(self, scene):
        """Fire a random campaign event."""
        if random.random() > self.EVENT_CHANCE:
            return
        event = random.choice(RANDOM_EVENTS)
        result = event.effect_fn(scene)
        if result:
            scene._add_notification(result)

    def _update_strongholds(self, scene):
        """Check if any roaming army should establish a stronghold."""
        # Track battle wins for roaming armies via a simple attribute
        for army in scene.armies:
            if army.team not in ROAMING_TYPES or army.team == TEAM_MERCENARY:
                continue
            wins = getattr(army, '_roaming_wins', 0)
            # Check if this army should escalate
            existing = next((s for s in self.strongholds
                             if distance(s.x, s.y, army.x, army.y) < 100
                             and s.team == army.team), None)
            if existing:
                existing.wins = max(existing.wins, wins)
                if existing.escalate():
                    scene._add_notification(
                        f"{existing.name} has grown stronger!")
            elif wins >= 2:
                sh = Stronghold(army.x, army.y, army.team,
                                StrongholdStage.ENCAMPMENT)
                sh.wins = wins
                self.strongholds.append(sh)
                scene._add_notification(
                    f"A {sh.name} has been established!")

    def ensure_bandits_near(self, x, y, armies, settlements, scene, count=1):
        """Ensure at least `count` bandit armies exist near (x, y). Spawn if needed."""
        from campaign.army import create_enemy_army
        radius = 400
        nearby_bandits = sum(
            1 for a in armies
            if a.team == TEAM_BANDITS and distance(a.x, a.y, x, y) < radius
        )
        for _ in range(max(0, count - nearby_bandits)):
            # Spawn a bandit near the quest location
            for _ in range(10):
                sx = x + random.randint(-300, 300)
                sy = y + random.randint(-300, 300)
                from core.settings import CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT
                sx = max(50, min(CAMPAIGN_MAP_WIDTH - 50, sx))
                sy = max(50, min(CAMPAIGN_MAP_HEIGHT - 50, sy))
                too_close = any(distance(sx, sy, s.x, s.y) < 80 for s in settlements)
                if not too_close:
                    break
            info = ROAMING_TYPES[TEAM_BANDITS]
            name = random.choice(info["name_pool"])
            army = create_enemy_army(name, TEAM_BANDITS, sx, sy, 1)
            target = random.randint(info["min_soldiers"], info["max_soldiers"])
            while army.total_soldiers < target and len(army.squads) < 4:
                from data.unit_types import MILITIA, SWORDSMEN
                army.add_squad(random.choice([MILITIA, SWORDSMEN]))
            scene.armies.append(army)
            scene._get_ai(army)

    def ensure_hideout_near(self, x, y, team, armies, settlements, scene, guard_count=1):
        """Ensure a hideout stronghold and its guards exist near a quest target."""
        from campaign.army import create_enemy_army
        radius = 450
        hideout = next(
            (s for s in self.strongholds
             if s.team == team and distance(s.x, s.y, x, y) < radius),
            None
        )
        if hideout is None:
            sx, sy = x, y
            for _ in range(12):
                sx = x + random.randint(-260, 260)
                sy = y + random.randint(-260, 260)
                from core.settings import CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT
                sx = max(50, min(CAMPAIGN_MAP_WIDTH - 50, sx))
                sy = max(50, min(CAMPAIGN_MAP_HEIGHT - 50, sy))
                too_close = any(distance(sx, sy, s.x, s.y) < 100 for s in settlements)
                if not too_close:
                    break
            hideout = Stronghold(sx, sy, team, StrongholdStage.ENCAMPMENT)
            self.strongholds.append(hideout)

        nearby_guards = sum(
            1 for a in armies
            if a.team == team and distance(a.x, a.y, hideout.x, hideout.y) < 220
        )
        for _ in range(max(0, guard_count - nearby_guards)):
            gx = hideout.x + random.randint(-120, 120)
            gy = hideout.y + random.randint(-120, 120)
            info = ROAMING_TYPES[team]
            army = create_enemy_army(random.choice(info["name_pool"]), team, gx, gy, 1)
            target = random.randint(info["min_soldiers"], info["max_soldiers"])
            while army.total_soldiers < target and len(army.squads) < 5:
                from data.unit_types import MILITIA, SWORDSMEN
                army.add_squad(random.choice([MILITIA, SWORDSMEN]))
            scene.armies.append(army)
            scene._get_ai(army)

        return hideout

    def record_roaming_win(self, army):
        """Record a battle win for a roaming army (for escalation)."""
        if army.team in ROAMING_TYPES:
            army._roaming_wins = getattr(army, '_roaming_wins', 0) + 1

    def serialize(self):
        return {
            "strongholds": [s.serialize() for s in self.strongholds],
            "last_spawn_day": self.last_spawn_day,
            "last_event_day": self.last_event_day,
        }

    def deserialize(self, data):
        self.strongholds = [Stronghold.deserialize(sd)
                            for sd in data.get("strongholds", [])]
        self.last_spawn_day = data.get("last_spawn_day", 0)
        self.last_event_day = data.get("last_event_day", 0)
