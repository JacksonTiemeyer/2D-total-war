"""Faction system — racial factions with personality traits and relations.

Phase 3: Medieval factions replaced with 11 racial factions + 2 NPC factions.
Each faction maps to a race_id and has a unique team index.
"""


class FactionPersonality:
    AGGRESSIVE = "aggressive"    # prefers war, attacks often
    DEFENSIVE = "defensive"      # prefers defense, builds up
    DIPLOMATIC = "diplomatic"    # prefers alliances, trades
    MERCANTILE = "mercantile"    # trade-focused, hires mercenaries
    ISOLATIONIST = "isolationist"  # avoids interaction, defends borders


class Faction:
    """A faction that controls armies and settlements on the campaign map."""

    def __init__(self, name, team, personality, color_name="red",
                 race_id="human", is_playable=True):
        self.name = name
        self.team = team
        self.personality = personality
        self.color_name = color_name
        self.race_id = race_id
        self.is_playable = is_playable
        self.is_player = False  # player starts factionless

    def __repr__(self):
        return f"Faction({self.name}, team={self.team}, race={self.race_id})"


# ── Racial Factions ─────────────────────────────────────────────────────
# Team indices: 1-11 = playable racial factions, 12-13 = NPC factions
# Team 0 = player/independent

FACTION_ROSTER = [
    # Playable racial factions
    Faction("Human Kingdoms", 1, FactionPersonality.DIPLOMATIC,
            "red", race_id="human"),
    Faction("High Elf Dominion", 2, FactionPersonality.DIPLOMATIC,
            "silver", race_id="high_elf"),
    Faction("Wood Elf Enclave", 3, FactionPersonality.DEFENSIVE,
            "forest_green", race_id="wood_elf"),
    Faction("Sea Elf Corsairs", 4, FactionPersonality.MERCANTILE,
            "teal", race_id="sea_elf"),
    Faction("Snow Elf Khanate", 5, FactionPersonality.ISOLATIONIST,
            "ice_blue", race_id="snow_elf"),
    Faction("Dark Elf Cabal", 6, FactionPersonality.AGGRESSIVE,
            "dark_purple", race_id="dark_elf"),
    Faction("Dwarf Holds", 7, FactionPersonality.DEFENSIVE,
            "bronze", race_id="dwarf"),
    Faction("Orc Waaagh!", 8, FactionPersonality.AGGRESSIVE,
            "orc_green", race_id="orc"),
    Faction("Undead Legion", 9, FactionPersonality.AGGRESSIVE,
            "bone", race_id="undead"),
    Faction("Troll & Ogre Tribes", 10, FactionPersonality.AGGRESSIVE,
            "mud_brown", race_id="troll_ogre"),
    Faction("Beastfolk Warherds", 11, FactionPersonality.AGGRESSIVE,
            "dark_red", race_id="beastfolk"),

    # NPC-only factions (not joinable)
    Faction("Feral Goblins", 12, FactionPersonality.AGGRESSIVE,
            "goblin_green", race_id="goblin", is_playable=False),
    Faction("Demon Horde", 13, FactionPersonality.AGGRESSIVE,
            "hellfire", race_id="demon", is_playable=False),
]

# Lookup by team
FACTION_BY_TEAM = {f.team: f for f in FACTION_ROSTER}

# Lookup by race_id
FACTION_BY_RACE = {f.race_id: f for f in FACTION_ROSTER}

# Independent / bandit teams (not true factions)
TEAM_INDEPENDENT = 0    # player starts here
TEAM_BANDITS = 90
TEAM_CULTISTS = 91
TEAM_CANNIBALS = 92
TEAM_DESERTERS = 93
TEAM_MERCENARY = 94

# Convenience: playable factions only
PLAYABLE_FACTIONS = [f for f in FACTION_ROSTER if f.is_playable]
