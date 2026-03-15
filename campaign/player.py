"""Player character system — race, class, leveling, stats.

The PlayerCharacter tracks the player's identity, progression, and abilities
throughout the campaign. It replaces the simple general_name/general_stats
fields on the player Army.

Full implementation in Batch 9.
"""

from data.races import ALL_PLAYABLE_RACES

# ── Player Classes ───────────────────────────────────────────────────────

CLASS_WARLORD = "warlord"
CLASS_BATTLEMAGE = "battlemage"
CLASS_CHAMPION = "champion"
CLASS_ROGUE = "rogue"
CLASS_ENGINEER = "engineer"
CLASS_NECROMANCER = "necromancer"

ALL_CLASSES = (
    CLASS_WARLORD, CLASS_BATTLEMAGE, CLASS_CHAMPION,
    CLASS_ROGUE, CLASS_ENGINEER, CLASS_NECROMANCER,
)

CLASS_DESCRIPTIONS = {
    CLASS_WARLORD: "The army builder. Biggest armies, best morale, squad size bonuses.",
    CLASS_BATTLEMAGE: "Spellcaster general. Fewer troops but devastating magic.",
    CLASS_CHAMPION: "Personal combat monster. Duel bonuses, intimidation, kill power.",
    CLASS_ROGUE: "The schemer. Economic bonuses, spies, sabotage, ambush mechanics.",
    CLASS_ENGINEER: "The builder. Constructs golems, siege expert, settlement bonuses.",
    CLASS_NECROMANCER: "Master of death. Raise fallen enemies, undead army grows from combat.",
}

# ── Starting Traits (non-race) ───────────────────────────────────────────

PLAYER_TRAITS = {
    "born_leader": {"name": "Born Leader", "effect": "+10% squad morale"},
    "veteran_campaigner": {"name": "Veteran Campaigner", "effect": "Start at level 3"},
    "silver_tongue": {"name": "Silver Tongue", "effect": "+20% reputation gain"},
    "iron_constitution": {"name": "Iron Constitution", "effect": "+50% hero health"},
    "merchant_prince": {"name": "Merchant Prince", "effect": "2x starting gold, +15% income"},
    "tactical_genius": {"name": "Tactical Genius", "effect": "Unlock 2nd formation from start"},
    "blessed_by_gods": {"name": "Blessed by the Gods", "effect": "+10% magic resistance"},
    "scrapper": {"name": "Scrapper", "effect": "+25% loot from battles"},
}

# ── Leveling Tables ──────────────────────────────────────────────────────

# XP required to reach each level (cumulative)
def xp_for_level(level):
    """XP required to reach a given level. Quadratic scaling."""
    if level <= 1:
        return 0
    return int(10 * (level - 1) ** 1.8)


# Level tier thresholds and unlocks
LEVEL_TIERS = {
    # (min_level, max_level): (tier_name, max_squads, squad_size_mult)
    (1, 5): ("Wanderer", 3, 0.5),
    (6, 10): ("Mercenary", 5, 0.65),
    (11, 15): ("Captain", 7, 0.8),
    (16, 20): ("Minor Lord", 9, 1.0),
    (21, 30): ("Major Lord", 12, 1.15),
    (31, 40): ("War Chief", 15, 1.3),
    (41, 50): ("Overlord", 20, 1.5),
}


def get_tier_for_level(level):
    """Return (tier_name, max_squads, squad_size_mult) for a given level."""
    for (lo, hi), data in LEVEL_TIERS.items():
        if lo <= level <= hi:
            return data
    return ("Overlord", 20, 1.5)  # fallback for levels > 50


# Max companions at each level
def max_companions_for_level(level):
    """Number of companion slots available at a given level."""
    if level < 5:
        return 0
    if level < 15:
        return 1
    if level < 25:
        return 2
    if level < 35:
        return 3
    if level < 45:
        return 4
    return 5


# ── Player Character Class ──────────────────────────────────────────────

class PlayerCharacter:
    """The player's persistent character throughout the campaign."""

    def __init__(self, name, race, player_class, trait=""):
        self.name = name
        self.race = race
        self.player_class = player_class
        self.trait = trait
        self.level = 3 if trait == "veteran_campaigner" else 1
        self.xp = xp_for_level(self.level)

        # Core stats (grow with level, weighted by class)
        self.leadership = 10       # Army size, morale aura
        self.combat = 10           # Personal melee power
        self.magic_power = 10      # Spell damage, mana contribution
        self.cunning = 10          # Economic bonuses, ambush chance
        self.engineering = 10      # Construct quality, siege bonuses

        # Apply class-based starting stat weights
        self._apply_class_stats()

        # Abilities (unlocked by class + level)
        self.abilities = []

        # Reputation per race {race_id: int}
        self.reputation = {r: 0 for r in ALL_PLAYABLE_RACES}
        # Same-race starts with bonus reputation
        if race in self.reputation:
            self.reputation[race] = 20

    def _apply_class_stats(self):
        """Set starting stat distribution based on class."""
        if self.player_class == CLASS_WARLORD:
            self.leadership = 18
            self.combat = 12
        elif self.player_class == CLASS_BATTLEMAGE:
            self.magic_power = 18
            self.leadership = 8
        elif self.player_class == CLASS_CHAMPION:
            self.combat = 20
            self.leadership = 8
        elif self.player_class == CLASS_ROGUE:
            self.cunning = 18
            self.combat = 12
        elif self.player_class == CLASS_ENGINEER:
            self.engineering = 18
            self.cunning = 12
        elif self.player_class == CLASS_NECROMANCER:
            self.magic_power = 16
            self.combat = 8
            self.cunning = 14

    @property
    def tier_name(self):
        return get_tier_for_level(self.level)[0]

    @property
    def max_squads(self):
        return get_tier_for_level(self.level)[1]

    @property
    def squad_size_mult(self):
        return get_tier_for_level(self.level)[2]

    @property
    def max_companions(self):
        return max_companions_for_level(self.level)

    def add_xp(self, amount):
        """Add XP and check for level-ups. Returns number of levels gained."""
        self.xp += amount
        levels_gained = 0
        while self.level < 50 and self.xp >= xp_for_level(self.level + 1):
            self.level += 1
            levels_gained += 1
            self._on_level_up()
        return levels_gained

    def _on_level_up(self):
        """Apply stat growth on level up (class-weighted)."""
        # Each class gets different stat point distribution
        if self.player_class == CLASS_WARLORD:
            self.leadership += 3
            self.combat += 1
        elif self.player_class == CLASS_BATTLEMAGE:
            self.magic_power += 3
            self.leadership += 1
        elif self.player_class == CLASS_CHAMPION:
            self.combat += 3
            self.leadership += 1
        elif self.player_class == CLASS_ROGUE:
            self.cunning += 3
            self.combat += 1
        elif self.player_class == CLASS_ENGINEER:
            self.engineering += 3
            self.cunning += 1
        elif self.player_class == CLASS_NECROMANCER:
            self.magic_power += 2
            self.cunning += 2

    def modify_reputation(self, race_id, amount):
        """Modify reputation with a race. Clamped to -100..100."""
        if race_id in self.reputation:
            self.reputation[race_id] = max(-100, min(100,
                                           self.reputation[race_id] + amount))

    def serialize(self):
        """Serialize for save system."""
        return {
            "name": self.name,
            "race": self.race,
            "player_class": self.player_class,
            "trait": self.trait,
            "level": self.level,
            "xp": self.xp,
            "leadership": self.leadership,
            "combat": self.combat,
            "magic_power": self.magic_power,
            "cunning": self.cunning,
            "engineering": self.engineering,
            "abilities": self.abilities[:],
            "reputation": dict(self.reputation),
        }

    @classmethod
    def deserialize(cls, data):
        """Rebuild from save data."""
        pc = cls(data["name"], data["race"], data["player_class"],
                 data.get("trait", ""))
        pc.level = data.get("level", 1)
        pc.xp = data.get("xp", 0)
        pc.leadership = data.get("leadership", 10)
        pc.combat = data.get("combat", 10)
        pc.magic_power = data.get("magic_power", 10)
        pc.cunning = data.get("cunning", 10)
        pc.engineering = data.get("engineering", 10)
        pc.abilities = data.get("abilities", [])
        pc.reputation = data.get("reputation", {r: 0 for r in ALL_PLAYABLE_RACES})
        return pc
