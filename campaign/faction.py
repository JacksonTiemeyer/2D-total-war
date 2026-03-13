"""Faction system - AI factions with personality traits and relations."""


class FactionPersonality:
    AGGRESSIVE = "aggressive"    # prefers war, attacks often
    DEFENSIVE = "defensive"      # prefers defense, builds up
    DIPLOMATIC = "diplomatic"    # prefers alliances, trades
    MERCANTILE = "mercantile"    # trade-focused, hires mercenaries


class Faction:
    """A faction that controls armies and settlements on the campaign map."""

    def __init__(self, name, team, personality, color_name="red"):
        self.name = name
        self.team = team
        self.personality = personality
        self.color_name = color_name
        self.is_player = False  # player starts factionless

    def __repr__(self):
        return f"Faction({self.name}, team={self.team})"


# Team color mapping in settings.py:
# 0=blue(player), 1=red, 2=green, 3=orange, 4=teal, 5=purple, 6=brown, 7=gold, 8=grey(independent)

FACTION_ROSTER = [
    Faction("Iron Empire", 1, FactionPersonality.AGGRESSIVE, "red"),
    Faction("Forest Alliance", 2, FactionPersonality.DEFENSIVE, "green"),
    Faction("Desert Raiders", 3, FactionPersonality.AGGRESSIVE, "orange"),
    Faction("Northern Holds", 4, FactionPersonality.DEFENSIVE, "teal"),
    Faction("Maritime Republic", 5, FactionPersonality.MERCANTILE, "purple"),
    Faction("Steppe Horde", 6, FactionPersonality.AGGRESSIVE, "brown"),
    Faction("Holy Order", 7, FactionPersonality.DIPLOMATIC, "gold"),
    Faction("Free Cities", 8, FactionPersonality.MERCANTILE, "grey"),
]

# Lookup by team
FACTION_BY_TEAM = {f.team: f for f in FACTION_ROSTER}

# Independent / bandit teams (not true factions)
TEAM_INDEPENDENT = 0    # player starts here
TEAM_BANDITS = 90
TEAM_CULTISTS = 91
TEAM_CANNIBALS = 92
TEAM_DESERTERS = 93
TEAM_MERCENARY = 94
