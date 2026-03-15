"""Race definitions — faction identities, diplomacy matrices, starting data.

Each race defines:
- Display name and team color
- Starting region on the world map
- Base diplomacy modifiers with other races
- Which unit roster they have access to
- Racial bonuses (combat, economic, magical)

Full implementation in Batch 8.
"""


class Race:
    """Definition of a playable race/faction."""

    def __init__(self, name, race_id, team_color, team_color_light,
                 starting_region="", description="",
                 diplomacy_modifiers=None, racial_bonuses=None,
                 is_playable=True):
        self.name = name
        self.race_id = race_id               # "human", "high_elf", etc.
        self.team_color = team_color
        self.team_color_light = team_color_light
        self.starting_region = starting_region
        self.description = description
        self.diplomacy_modifiers = diplomacy_modifiers or {}  # {race_id: int}
        self.racial_bonuses = racial_bonuses or {}
        self.is_playable = is_playable


# ── Race Roster ──────────────────────────────────────────────────────────
# Full definitions with diplomacy matrices will be added in Batch 8.
# These are the canonical race IDs used throughout the codebase.

RACE_HUMAN = "human"
RACE_HIGH_ELF = "high_elf"
RACE_WOOD_ELF = "wood_elf"
RACE_SEA_ELF = "sea_elf"
RACE_SNOW_ELF = "snow_elf"
RACE_DARK_ELF = "dark_elf"
RACE_DWARF = "dwarf"
RACE_ORC = "orc"
RACE_UNDEAD = "undead"
RACE_TROLL_OGRE = "troll_ogre"
RACE_BEASTFOLK = "beastfolk"

# Non-playable
RACE_GOBLIN = "goblin"     # Feral roaming faction
RACE_DEMON = "demon"       # Endgame crisis only

ALL_PLAYABLE_RACES = (
    RACE_HUMAN, RACE_HIGH_ELF, RACE_WOOD_ELF, RACE_SEA_ELF, RACE_SNOW_ELF,
    RACE_DARK_ELF, RACE_DWARF, RACE_ORC, RACE_UNDEAD, RACE_TROLL_OGRE,
    RACE_BEASTFOLK,
)

ALL_RACES = ALL_PLAYABLE_RACES + (RACE_GOBLIN, RACE_DEMON)

# ── Base Diplomacy Matrix ────────────────────────────────────────────────
# Positive = friendly, Negative = hostile. Scale: -100 to +100.
# Symmetric by default; overrides specified per pair.

BASE_DIPLOMACY = {
    # Elven internal relations
    (RACE_HIGH_ELF, RACE_WOOD_ELF): 40,       # Friendly
    (RACE_HIGH_ELF, RACE_DARK_ELF): -60,      # Hostile
    (RACE_WOOD_ELF, RACE_DARK_ELF): -50,      # Hostile
    (RACE_SEA_ELF, RACE_DARK_ELF): 10,        # Trade partners
    (RACE_SNOW_ELF, RACE_HIGH_ELF): -10,      # Isolationist, cool
    (RACE_SNOW_ELF, RACE_WOOD_ELF): -10,
    (RACE_SNOW_ELF, RACE_SEA_ELF): -20,
    (RACE_SNOW_ELF, RACE_DARK_ELF): -30,

    # Human relations
    (RACE_HUMAN, RACE_DWARF): 20,             # Traditional allies
    (RACE_HUMAN, RACE_HIGH_ELF): 10,          # Respectful
    (RACE_HUMAN, RACE_ORC): -40,              # Hostile
    (RACE_HUMAN, RACE_UNDEAD): -60,           # Enemies

    # Dwarf relations
    (RACE_DWARF, RACE_HIGH_ELF): -15,         # Distrust elves
    (RACE_DWARF, RACE_WOOD_ELF): -15,
    (RACE_DWARF, RACE_ORC): -50,              # Ancient enemies
    (RACE_DWARF, RACE_UNDEAD): -40,

    # Orc relations
    (RACE_ORC, RACE_UNDEAD): -20,             # Wary
    (RACE_ORC, RACE_TROLL_OGRE): 15,          # Grudging allies
    (RACE_ORC, RACE_BEASTFOLK): 10,           # Some respect

    # Undead
    (RACE_UNDEAD, RACE_HIGH_ELF): -70,        # Hated
    (RACE_UNDEAD, RACE_WOOD_ELF): -60,
    (RACE_UNDEAD, RACE_DARK_ELF): -10,        # Tolerated, dark magic kinship

    # Beastfolk
    (RACE_BEASTFOLK, RACE_HUMAN): -30,
    (RACE_BEASTFOLK, RACE_DWARF): -25,
}


def get_base_diplomacy(race_a, race_b):
    """Get base diplomacy modifier between two races. Returns 0 if not specified."""
    if race_a == race_b:
        return 50  # Same race = friendly
    return BASE_DIPLOMACY.get((race_a, race_b),
           BASE_DIPLOMACY.get((race_b, race_a), 0))
