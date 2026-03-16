"""Companion system — named NPC heroes that join the player.

Companions serve as additional hero units in battle and can lead
detached armies at high levels. They have their own race, class,
level, abilities, and loyalty.

Full implementation in Batch 10.
"""

import random
from campaign.player import ALL_CLASSES, xp_for_level


class Companion:
    """A named NPC companion that fights alongside the player."""

    def __init__(self, name, race, companion_class, level=1, personality="loyal"):
        self.name = name
        self.race = race
        self.companion_class = companion_class
        self.level = level
        self.xp = xp_for_level(level)
        self.personality = personality   # loyal, ambitious, greedy, etc.
        self.loyalty = 80               # 0-100, leaves if too low
        self.abilities = []
        self.alive = True               # False = captured, will return
        self.capture_timer = 0          # Days until return if captured

    def add_xp(self, amount):
        """Add XP and level up. Returns levels gained."""
        self.xp += amount
        levels_gained = 0
        while self.level < 50 and self.xp >= xp_for_level(self.level + 1):
            self.level += 1
            levels_gained += 1
        return levels_gained

    def modify_loyalty(self, amount):
        """Modify loyalty. Companion leaves if it drops to 0."""
        self.loyalty = max(0, min(100, self.loyalty + amount))
        return self.loyalty > 0  # False = companion leaves

    def can_lead_army(self):
        """Check if companion can lead a detached army."""
        return self.level >= 35 and self.companion_class == "warlord"

    def serialize(self):
        return {
            "name": self.name,
            "race": self.race,
            "companion_class": self.companion_class,
            "level": self.level,
            "xp": self.xp,
            "personality": self.personality,
            "loyalty": self.loyalty,
            "abilities": self.abilities[:],
            "alive": self.alive,
            "capture_timer": self.capture_timer,
        }

    @classmethod
    def deserialize(cls, data):
        c = cls(data["name"], data["race"], data["companion_class"],
                data.get("level", 1), data.get("personality", "loyal"))
        c.xp = data.get("xp", 0)
        c.loyalty = data.get("loyalty", 80)
        c.abilities = data.get("abilities", [])
        c.alive = data.get("alive", True)
        c.capture_timer = data.get("capture_timer", 0)
        return c


# ── Companion Manager ─────────────────────────────────────────────────

class CompanionManager:
    """Manages the player's active companions."""

    def __init__(self):
        self.companions = []  # list of Companion

    def add(self, companion):
        self.companions.append(companion)

    def remove(self, name):
        self.companions = [c for c in self.companions if c.name != name]

    def get(self, name):
        for c in self.companions:
            if c.name == name:
                return c
        return None

    def tick_day(self):
        """Daily update: loyalty decay for ambitious companions, capture timers."""
        for c in self.companions:
            if not c.alive:
                c.capture_timer -= 1
                if c.capture_timer <= 0:
                    c.alive = True
            if c.personality == "ambitious":
                c.modify_loyalty(-1)
            elif c.personality == "greedy":
                c.modify_loyalty(-1)

    def check_departures(self):
        """Remove companions with 0 loyalty. Returns list of departed names."""
        departed = [c.name for c in self.companions if c.loyalty <= 0 and c.alive]
        self.companions = [c for c in self.companions if c.loyalty > 0 or not c.alive]
        return departed

    def serialize(self):
        return [c.serialize() for c in self.companions]

    def deserialize(self, data_list):
        self.companions = [Companion.deserialize(d) for d in data_list]


# ── Tavern Companion Generation ───────────────────────────────────────

_COMPANION_NAMES = [
    "Alaric", "Brenna", "Caelum", "Duskara", "Eldrin",
    "Freya", "Gideon", "Halia", "Ivor", "Jessa",
    "Kael", "Lyria", "Magnus", "Nessa", "Orin",
    "Petra", "Quinn", "Rowan", "Sable", "Theron",
]

_PERSONALITIES = ["loyal", "ambitious", "greedy", "stoic"]

_RACES = ["human", "elf", "dwarf", "orc", "undead"]


def generate_tavern_companions(settlement_name, day, player_level, count=3):
    """Generate random companions available at a tavern.

    Uses day + settlement_name as seed for deterministic but varied results.
    Refreshes when day changes.
    """
    seed = hash((settlement_name, day // 7))  # refresh weekly
    rng = random.Random(seed)
    companions = []
    used_names = set()
    for _ in range(count):
        name = rng.choice([n for n in _COMPANION_NAMES if n not in used_names])
        used_names.add(name)
        race = rng.choice(_RACES)
        cls = rng.choice(list(ALL_CLASSES))
        level = max(1, player_level + rng.randint(-3, 1))
        personality = rng.choice(_PERSONALITIES)
        companions.append(Companion(name, race, cls, level, personality))
    return companions
