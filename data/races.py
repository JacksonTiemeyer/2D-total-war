"""Race definitions — faction identities, diplomacy matrices, starting data.

Each race defines:
- Display name and team color (RGB tuples)
- Starting region on the world map
- Base diplomacy modifiers with other races
- Racial bonuses (combat, economic, magical)

Phase 3 Batch 8: Fully fleshed out with colors and bonuses.
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


# ── Race IDs ────────────────────────────────────────────────────────────

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


# ── Full Race Definitions ──────────────────────────────────────────────

RACE_DEFINITIONS = {
    RACE_HUMAN: Race(
        "Human Kingdoms", RACE_HUMAN,
        team_color=(200, 50, 50), team_color_light=(220, 100, 100),
        starting_region="Central Plains",
        description="Versatile and adaptable. Gunpowder, heavy cavalry, strong economy.",
        racial_bonuses={"income_mult": 1.15, "diplomacy_bonus": 5},
    ),
    RACE_HIGH_ELF: Race(
        "High Elf Dominion", RACE_HIGH_ELF,
        team_color=(180, 180, 220), team_color_light=(210, 210, 240),
        starting_region="Eastern Highlands",
        description="Masters of magic. Elegant warriors, powerful spellcasters.",
        racial_bonuses={"mana_regen_mult": 1.2, "magic_resistance": 10},
    ),
    RACE_WOOD_ELF: Race(
        "Wood Elf Enclave", RACE_WOOD_ELF,
        team_color=(40, 140, 40), team_color_light=(100, 200, 100),
        starting_region="Northwest Forests",
        description="Forest guerrillas. Stealth, speed, and archery.",
        racial_bonuses={"forest_speed_mult": 1.3, "ranged_accuracy": 1.1},
    ),
    RACE_SEA_ELF: Race(
        "Sea Elf Corsairs", RACE_SEA_ELF,
        team_color=(60, 160, 160), team_color_light=(120, 200, 200),
        starting_region="Southwest Coast",
        description="Naval raiders and water mages. Trade-focused, poison weapons.",
        racial_bonuses={"income_mult": 1.2, "water_combat_bonus": 1.2},
    ),
    RACE_SNOW_ELF: Race(
        "Snow Elf Khanate", RACE_SNOW_ELF,
        team_color=(140, 180, 220), team_color_light=(180, 210, 240),
        starting_region="Far North Tundra",
        description="Steppe warrior-monks. Ice magic, mammoth riders, isolationist.",
        racial_bonuses={"winter_immunity": True, "ice_resistance": 1.0},
    ),
    RACE_DARK_ELF: Race(
        "Dark Elf Cabal", RACE_DARK_ELF,
        team_color=(100, 40, 120), team_color_light=(160, 80, 180),
        starting_region="Underground South",
        description="Cruel slavers. Poison, stealth, dark magic, expendable fodder.",
        racial_bonuses={"slave_income": 0.5, "ambush_chance": 0.2},
    ),
    RACE_DWARF: Race(
        "Dwarf Holds", RACE_DWARF,
        team_color=(180, 140, 60), team_color_light=(220, 180, 100),
        starting_region="Northeast Mountains",
        description="Mountain fortresses. Heaviest armor, engineering, rune magic.",
        racial_bonuses={"armor_bonus": 5, "siege_defense": 1.3, "magic_resistance": 15},
    ),
    RACE_ORC: Race(
        "Orc Waaagh!", RACE_ORC,
        team_color=(80, 140, 40), team_color_light=(120, 180, 80),
        starting_region="Southeast Wastes",
        description="Brute force and numbers. Cheap troops, devastating charges.",
        racial_bonuses={"upkeep_mult": 0.8, "charge_bonus": 1.1},
    ),
    RACE_UNDEAD: Race(
        "Undead Legion", RACE_UNDEAD,
        team_color=(120, 110, 90), team_color_light=(170, 160, 140),
        starting_region="Cursed Lands",
        description="Tireless hordes. Never rout, never rest. Raise the fallen.",
        racial_bonuses={"raise_dead_cost_mult": 0.5, "no_upkeep_basic": True},
    ),
    RACE_TROLL_OGRE: Race(
        "Troll & Ogre Tribes", RACE_TROLL_OGRE,
        team_color=(140, 100, 60), team_color_light=(190, 150, 100),
        starting_region="Wild Mountains",
        description="Few but mighty. Monster units, regeneration, brute strength.",
        racial_bonuses={"regen_rate_mult": 1.2, "food_consumption": 1.5},
    ),
    RACE_BEASTFOLK: Race(
        "Beastfolk Warherds", RACE_BEASTFOLK,
        team_color=(140, 40, 40), team_color_light=(190, 90, 90),
        starting_region="Southern Steppes",
        description="Fast and ferocious. Cavalry-focused, terror tactics.",
        racial_bonuses={"ambush_chance": 0.15, "charge_bonus": 1.15},
    ),
    RACE_GOBLIN: Race(
        "Feral Goblins", RACE_GOBLIN,
        team_color=(80, 120, 40), team_color_light=(120, 160, 80),
        starting_region="Scattered",
        description="Countless, cowardly, cunning. Roaming swarms.",
        is_playable=False,
    ),
    RACE_DEMON: Race(
        "Demon Horde", RACE_DEMON,
        team_color=(180, 40, 20), team_color_light=(220, 80, 60),
        starting_region="The Rift",
        description="Endgame crisis. Fire-immune, tireless, devastating.",
        is_playable=False,
    ),
}


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
    (RACE_HUMAN, RACE_BEASTFOLK): -30,
    (RACE_HUMAN, RACE_TROLL_OGRE): -20,

    # Dwarf relations
    (RACE_DWARF, RACE_HIGH_ELF): -15,         # Distrust elves
    (RACE_DWARF, RACE_WOOD_ELF): -15,
    (RACE_DWARF, RACE_ORC): -50,              # Ancient enemies
    (RACE_DWARF, RACE_UNDEAD): -40,
    (RACE_DWARF, RACE_TROLL_OGRE): -25,

    # Orc relations
    (RACE_ORC, RACE_UNDEAD): -20,             # Wary
    (RACE_ORC, RACE_TROLL_OGRE): 15,          # Grudging allies
    (RACE_ORC, RACE_BEASTFOLK): 10,           # Some respect
    (RACE_ORC, RACE_HIGH_ELF): -40,
    (RACE_ORC, RACE_WOOD_ELF): -30,
    (RACE_ORC, RACE_DWARF): -50,

    # Undead — hated by all living
    (RACE_UNDEAD, RACE_HIGH_ELF): -70,
    (RACE_UNDEAD, RACE_WOOD_ELF): -60,
    (RACE_UNDEAD, RACE_DARK_ELF): -10,        # Dark magic kinship
    (RACE_UNDEAD, RACE_DWARF): -40,
    (RACE_UNDEAD, RACE_ORC): -20,
    (RACE_UNDEAD, RACE_TROLL_OGRE): -30,
    (RACE_UNDEAD, RACE_BEASTFOLK): -25,
    (RACE_UNDEAD, RACE_SEA_ELF): -50,
    (RACE_UNDEAD, RACE_SNOW_ELF): -40,

    # Beastfolk
    (RACE_BEASTFOLK, RACE_HUMAN): -30,
    (RACE_BEASTFOLK, RACE_DWARF): -25,
    (RACE_BEASTFOLK, RACE_HIGH_ELF): -35,
    (RACE_BEASTFOLK, RACE_WOOD_ELF): -20,

    # Troll/Ogre
    (RACE_TROLL_OGRE, RACE_HUMAN): -20,
    (RACE_TROLL_OGRE, RACE_HIGH_ELF): -25,

    # Everyone hates demons
    (RACE_DEMON, RACE_HUMAN): -80,
    (RACE_DEMON, RACE_HIGH_ELF): -80,
    (RACE_DEMON, RACE_WOOD_ELF): -80,
    (RACE_DEMON, RACE_SEA_ELF): -80,
    (RACE_DEMON, RACE_SNOW_ELF): -80,
    (RACE_DEMON, RACE_DARK_ELF): -40,       # Dark elves might ally...
    (RACE_DEMON, RACE_DWARF): -80,
    (RACE_DEMON, RACE_ORC): -60,
    (RACE_DEMON, RACE_UNDEAD): -50,
    (RACE_DEMON, RACE_TROLL_OGRE): -60,
    (RACE_DEMON, RACE_BEASTFOLK): -60,
    (RACE_DEMON, RACE_GOBLIN): -40,
}


def get_base_diplomacy(race_a, race_b):
    """Get base diplomacy modifier between two races. Returns 0 if not specified."""
    if race_a == race_b:
        return 50  # Same race = friendly
    return BASE_DIPLOMACY.get((race_a, race_b),
           BASE_DIPLOMACY.get((race_b, race_a), 0))


def get_race_definition(race_id):
    """Get the Race definition for a given race_id."""
    return RACE_DEFINITIONS.get(race_id)
