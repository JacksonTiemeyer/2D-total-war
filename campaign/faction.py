"""Faction system - AI factions with personality traits and relations."""


class FactionPersonality:
    AGGRESSIVE = "aggressive"    # prefers war, attacks often
    DEFENSIVE = "defensive"      # prefers defense, builds up
    DIPLOMATIC = "diplomatic"    # prefers alliances, trades


class Faction:
    """A faction that controls armies and settlements on the campaign map."""

    def __init__(self, name, team, personality, color_name="red"):
        self.name = name
        self.team = team
        self.personality = personality
        self.color_name = color_name
        self.is_player = (team == 0)

    def __repr__(self):
        return f"Faction({self.name}, team={self.team})"


# Pre-defined factions
PLAYER_FACTION = Faction("Your Kingdom", 0, FactionPersonality.DIPLOMATIC, "blue")

FACTION_ROSTER = [
    PLAYER_FACTION,
    Faction("Iron Empire", 1, FactionPersonality.AGGRESSIVE, "red"),
    Faction("Forest Alliance", 2, FactionPersonality.DEFENSIVE, "green"),
    Faction("Desert Raiders", 3, FactionPersonality.AGGRESSIVE, "orange"),
]
