"""Companion system — named NPC heroes that join the player.

Companions serve as additional hero units in battle and can lead
detached armies at high levels. They have their own race, class,
level, abilities, and loyalty.

Full implementation in Batch 10.
"""

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
