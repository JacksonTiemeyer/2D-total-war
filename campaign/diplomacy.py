"""Diplomacy manager - tracks faction relationships and diplomatic actions.

B12: Dual-layer reputation system:
  - Faction reputation: how the faction views the player (-100 to 100)
  - Individual general opinion: how each named general views the player (-100 to 100)
"""

import random
from campaign.faction import FactionPersonality


class DiplomacyState:
    WAR = "war"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"


class DiplomacyManager:
    """Manages relationships between all factions and individual generals.

    Relations are stored as a dict of (team_a, team_b) -> int (-100 to 100).
    Negative = hostile, Positive = friendly.

    B12: Also tracks individual general opinions of the player.
    """

    WAR_THRESHOLD = -50
    ALLIANCE_THRESHOLD = 50

    def __init__(self, factions):
        self.factions = {f.team: f for f in factions}
        self.relations = {}
        # B12: Individual general opinions of the player (general_name -> int)
        self.general_opinions = {}
        self._init_relations(factions)

    def _init_relations(self, factions):
        """Set up initial relations based on faction personalities."""
        for i, f1 in enumerate(factions):
            for f2 in factions[i + 1:]:
                key = self._key(f1.team, f2.team)
                # Default: slightly hostile
                base = -20
                if f1.personality == FactionPersonality.DIPLOMATIC:
                    base += 20
                if f2.personality == FactionPersonality.DIPLOMATIC:
                    base += 20
                if (f1.personality == FactionPersonality.AGGRESSIVE and
                        f2.personality == FactionPersonality.AGGRESSIVE):
                    base -= 30
                self.relations[key] = max(-100, min(100, base))

    def _key(self, team_a, team_b):
        return (min(team_a, team_b), max(team_a, team_b))

    def get_relation(self, team_a, team_b):
        if team_a == team_b:
            return 100
        return self.relations.get(self._key(team_a, team_b), 0)

    def set_relation(self, team_a, team_b, value):
        self.relations[self._key(team_a, team_b)] = max(-100, min(100, value))

    def modify_relation(self, team_a, team_b, delta):
        current = self.get_relation(team_a, team_b)
        self.set_relation(team_a, team_b, current + delta)

    def get_state(self, team_a, team_b):
        """Return diplomatic state between two factions."""
        if team_a == team_b:
            return DiplomacyState.ALLIED
        rel = self.get_relation(team_a, team_b)
        if rel <= self.WAR_THRESHOLD:
            return DiplomacyState.WAR
        elif rel < -20:
            return DiplomacyState.HOSTILE
        elif rel < 20:
            return DiplomacyState.NEUTRAL
        elif rel < self.ALLIANCE_THRESHOLD:
            return DiplomacyState.FRIENDLY
        else:
            return DiplomacyState.ALLIED

    def are_at_war(self, team_a, team_b):
        return self.get_state(team_a, team_b) == DiplomacyState.WAR

    def are_allied(self, team_a, team_b):
        return self.get_state(team_a, team_b) == DiplomacyState.ALLIED

    def declare_war(self, team_a, team_b):
        """Force war between two factions."""
        self.set_relation(team_a, team_b, -80)

    def propose_alliance(self, team_a, team_b):
        """Attempt alliance. Returns True if accepted."""
        rel = self.get_relation(team_a, team_b)
        # Must already be friendly
        if rel < 20:
            return False
        # Aggressive factions are harder to ally with
        target_faction = self.factions.get(team_b)
        if target_faction and target_faction.personality == FactionPersonality.AGGRESSIVE:
            threshold = 40
        else:
            threshold = 25
        if rel >= threshold:
            self.set_relation(team_a, team_b, 60)
            return True
        return False

    def propose_peace(self, team_a, team_b):
        """Attempt peace. Returns True if accepted."""
        rel = self.get_relation(team_a, team_b)
        if rel > self.WAR_THRESHOLD:
            return False  # not at war
        # Chance based on relation: closer to threshold = higher chance
        chance = 0.3 + (rel - (-100)) / 100 * 0.5
        if random.random() < chance:
            self.set_relation(team_a, team_b, -20)  # move to hostile but not war
            return True
        return False

    def ai_diplomacy_tick(self, faction, all_factions):
        """AI faction makes diplomatic decisions each turn."""
        for other in all_factions:
            if other.team == faction.team:
                continue
            rel = self.get_relation(faction.team, other.team)
            state = self.get_state(faction.team, other.team)

            # Aggressive factions: declare war on neutral/hostile neighbors
            if (faction.personality == FactionPersonality.AGGRESSIVE and
                    state in (DiplomacyState.HOSTILE, DiplomacyState.NEUTRAL)):
                if random.random() < 0.1:
                    self.declare_war(faction.team, other.team)

            # Defensive factions: try to make peace and alliances
            elif faction.personality == FactionPersonality.DEFENSIVE:
                if state == DiplomacyState.WAR and random.random() < 0.15:
                    self.propose_peace(faction.team, other.team)
                elif state == DiplomacyState.FRIENDLY and random.random() < 0.1:
                    self.propose_alliance(faction.team, other.team)

            # Diplomatic factions: improve relations gradually
            elif faction.personality == FactionPersonality.DIPLOMATIC:
                if state != DiplomacyState.WAR:
                    self.modify_relation(faction.team, other.team, 2)
                elif random.random() < 0.2:
                    self.propose_peace(faction.team, other.team)

            # Natural drift: relations slowly move toward 0 if not at war
            if state != DiplomacyState.WAR and state != DiplomacyState.ALLIED:
                if rel > 5:
                    self.modify_relation(faction.team, other.team, -1)
                elif rel < -5:
                    self.modify_relation(faction.team, other.team, 1)

    # --- B12: Individual general opinion methods ---

    def get_general_opinion(self, general_name):
        """Get a general's personal opinion of the player (-100 to 100)."""
        return self.general_opinions.get(general_name, 0)

    def set_general_opinion(self, general_name, value):
        """Set a general's opinion, clamped to [-100, 100]."""
        self.general_opinions[general_name] = max(-100, min(100, value))

    def modify_general_opinion(self, general_name, delta):
        """Adjust a general's opinion by delta."""
        current = self.get_general_opinion(general_name)
        self.set_general_opinion(general_name, current + delta)

    def get_general_state(self, general_name):
        """Return diplomatic-style state for a general's opinion."""
        opinion = self.get_general_opinion(general_name)
        if opinion <= -50:
            return DiplomacyState.HOSTILE
        elif opinion < -20:
            return DiplomacyState.HOSTILE
        elif opinion < 20:
            return DiplomacyState.NEUTRAL
        elif opinion < 50:
            return DiplomacyState.FRIENDLY
        else:
            return DiplomacyState.ALLIED

    def bribe_general(self, general_name, gold_amount):
        """B12: Attempt to bribe a general. Returns opinion gained."""
        gain = gold_amount // 10  # 10 gold = 1 opinion point
        self.modify_general_opinion(general_name, gain)
        return gain

    def battle_opinion_update(self, general_name, player_won, shared_battle=False):
        """B12: Update general opinion after battle interaction."""
        if shared_battle:
            # Fought alongside player
            self.modify_general_opinion(general_name, 10)
        elif player_won:
            # Player defeated this general's army
            self.modify_general_opinion(general_name, -15)
        else:
            # General beat the player
            self.modify_general_opinion(general_name, 5)

    def serialize(self):
        """Convert to JSON-serializable dict."""
        return {
            "relations": {f"{a},{b}": v for (a, b), v in self.relations.items()},
            "general_opinions": self.general_opinions,
        }

    def deserialize(self, data):
        """Restore from serialized data."""
        self.relations = {}
        # Handle both old format (flat dict) and new format (nested)
        if "relations" in data:
            rel_data = data["relations"]
            self.general_opinions = data.get("general_opinions", {})
        else:
            # Legacy format: data is the relations dict directly
            rel_data = data
            self.general_opinions = {}
        for key, val in rel_data.items():
            a, b = key.split(",")
            self.relations[(int(a), int(b))] = val
