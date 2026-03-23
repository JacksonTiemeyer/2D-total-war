"""Unit type definitions. All squad templates and stats live here.

Phase 3: Full fantasy roster — 100+ units across 13 races.
Legacy medieval units kept as Human roster.
"""

from data.spells import (
    ALL_SPELLS, LIGHTNING_BOLT, CHAIN_LIGHTNING, COMET, WIND_BLAST,
    FROST_BOLT, BLIZZARD, SHADOW_BOLT, DREAD, CLOAK_OF_SHADOWS, SOUL_DRAIN,
    FIREBALL, INFERNO, FLAME_WALL, BLAZING_SWORD,
    RAISE_DEAD, SPIRIT_LEECH, CURSE_OF_YEARS, WIND_OF_DEATH,
    ENCHANT_ARMOR, SEARING_DOOM, TRANSMUTATION, RUNE_OF_WRATH,
    SUMMON_WOLVES, WILD_FURY,
)


def _resolve_spell_list(spell_names):
    """Convert a tuple of spell name strings to Spell objects."""
    return tuple(ALL_SPELLS[n] for n in spell_names if n in ALL_SPELLS)


class UnitStats:
    """Stats for an individual soldier within a squad.

    Phase 3 additions: traits, damage_type, size_category, magic_resistance,
    damage_vulnerabilities, damage_immunities, race, spell_school, spell_list.
    All new fields have backward-compatible defaults so existing units still work.
    """
    def __init__(self, name, health, melee_attack, melee_defense,
                 ranged_attack=0, range_distance=0, speed=2.0,
                 charge_bonus=0, armor=0, shield=False,
                 squad_size=20, cost=100, upkeep=10,
                 weapon_strength=10, ranged_strength=0,
                 armor_penetration=0, ranged_armor_penetration=0,
                 exhaustion_rate=1.0, mass=1.0,
                 can_brace=False, is_spear=False,
                 can_fire_while_moving=False,
                 description="",
                 # ── Phase 3: Fantasy fields ──
                 race="human",
                 traits=(),
                 size_category="normal",
                 damage_type="physical",
                 magic_resistance=0,
                 damage_vulnerabilities=(),
                 damage_immunities=(),
                 spell_school="",
                 spell_list=(),
                 # ── Mana / Casting ──
                 max_mana=0,
                 mana_regen=0.0):
        self.name = name
        self.health = health
        self.melee_attack = melee_attack
        self.melee_defense = melee_defense
        self.ranged_attack = ranged_attack
        self.range_distance = range_distance
        self.speed = speed
        self.charge_bonus = charge_bonus
        self.armor = armor
        self.shield = shield
        self.squad_size = squad_size
        self.cost = cost
        self.upkeep = upkeep
        self.weapon_strength = weapon_strength      # base melee damage
        self.ranged_strength = ranged_strength      # base ranged damage
        self.armor_penetration = armor_penetration  # % of armor ignored (0-100)
        self.ranged_armor_penetration = ranged_armor_penetration
        self.exhaustion_rate = exhaustion_rate       # multiplier on fatigue gain
        self.mass = mass                             # affects charge impact
        self.description = description

        # ── Phase 3: Fantasy fields ──
        self.race = race
        self.traits = tuple(traits)
        self.size_category = size_category
        self.damage_type = damage_type
        self.magic_resistance = magic_resistance
        self.damage_vulnerabilities = tuple(damage_vulnerabilities)
        self.damage_immunities = tuple(damage_immunities)
        self.spell_school = spell_school
        self.spell_list = tuple(spell_list)

        # ── Mana / Casting ──
        self.max_mana = max_mana
        self.mana = max_mana  # start full
        self.mana_regen = mana_regen  # per second

        # Legacy compatibility: derive old flags from traits if traits are set,
        # otherwise use the explicit parameters
        if traits:
            self.can_brace = "can_brace" in self.traits
            self.is_spear = "can_brace" in self.traits
            self.can_fire_while_moving = "fire_while_moving" in self.traits
        else:
            self.can_brace = can_brace
            self.is_spear = is_spear
            self.can_fire_while_moving = can_fire_while_moving


# ═══════════════════════════════════════════════════════════════════════════
# HUMANS — Renaissance / gunpowder theme
# ═══════════════════════════════════════════════════════════════════════════

HUMAN_LEVY_MILITIA = UnitStats(
    name="Levy Militia", health=80, melee_attack=8, melee_defense=6,
    speed=2.0, charge_bonus=2, armor=5, shield=True,
    squad_size=30, cost=75, upkeep=5, race="human",
    weapon_strength=8, armor_penetration=5,
    exhaustion_rate=1.2, mass=1.5,
    description="Cheap and plentiful. They hold the line... barely.",
)

HUMAN_MEN_AT_ARMS = UnitStats(
    name="Men-at-Arms", health=100, melee_attack=12, melee_defense=10,
    speed=2.0, charge_bonus=4, armor=15, shield=True,
    squad_size=24, cost=150, upkeep=12, race="human",
    weapon_strength=14, armor_penetration=15,
    exhaustion_rate=1.0, mass=1.5,
    description="Reliable swords and shields. The backbone of any army.",
)

HUMAN_HALBERDIERS = UnitStats(
    name="Halberdiers", health=95, melee_attack=11, melee_defense=14,
    speed=1.8, charge_bonus=3, armor=12, shield=False,
    squad_size=24, cost=140, upkeep=12, race="human",
    traits=("can_brace", "anti_large"),
    weapon_strength=14, armor_penetration=25,
    exhaustion_rate=1.0, mass=1.5,
    description="Anti-cavalry polearms. Brace for impact!",
)

HUMAN_LONGBOWMEN = UnitStats(
    name="Longbowmen", health=60, melee_attack=4, melee_defense=3,
    ranged_attack=16, range_distance=350,
    speed=2.0, armor=5, race="human",
    squad_size=20, cost=150, upkeep=12,
    weapon_strength=6, ranged_strength=18,
    armor_penetration=5, ranged_armor_penetration=15,
    exhaustion_rate=0.8, mass=1.0,
    description="Long-range archers. Rain arrows upon your foes.",
)

HUMAN_HANDGUNNERS = UnitStats(
    name="Handgunners", health=65, melee_attack=5, melee_defense=4,
    ranged_attack=22, range_distance=200,
    speed=1.8, armor=10, race="human",
    squad_size=16, cost=200, upkeep=16,
    weapon_strength=7, ranged_strength=28,
    armor_penetration=5, ranged_armor_penetration=50,
    exhaustion_rate=0.9, mass=1.0,
    description="Short-range gunpowder infantry. Punches through armor.",
)

HUMAN_KNIGHTS = UnitStats(
    name="Knights", health=150, melee_attack=14, melee_defense=10,
    speed=3.5, charge_bonus=22, armor=28, shield=True,
    squad_size=8, cost=350, upkeep=30, race="human",
    traits=("mounted",),
    weapon_strength=18, armor_penetration=30,
    exhaustion_rate=1.3, mass=4.5, size_category="large",
    description="Heavy cavalry. The hammer to your infantry's anvil.",
)

HUMAN_PISTOLIERS = UnitStats(
    name="Pistoliers", health=80, melee_attack=6, melee_defense=4,
    ranged_attack=14, range_distance=140,
    speed=4.2, charge_bonus=6, armor=8, race="human",
    traits=("mounted", "fire_while_moving"),
    squad_size=10, cost=260, upkeep=22,
    weapon_strength=8, ranged_strength=18,
    armor_penetration=10, ranged_armor_penetration=35,
    exhaustion_rate=0.8, mass=3.0, size_category="large",
    description="Mounted gunners. Fire while moving. Harass and kite.",
)

HUMAN_WAR_WAGON = UnitStats(
    name="War Wagon", health=500, melee_attack=8, melee_defense=20,
    ranged_attack=18, range_distance=180,
    speed=1.5, armor=40, race="human",
    traits=("armored_construct",),
    squad_size=1, cost=500, upkeep=40,
    weapon_strength=15, ranged_strength=22,
    armor_penetration=10, ranged_armor_penetration=40,
    exhaustion_rate=0.0, mass=8.0, size_category="massive",
    damage_immunities=("poison",),
    description="Mobile fortress. Carries gunners and shrugs off attacks.",
)

HUMAN_CANNON = UnitStats(
    name="Cannon", health=300, melee_attack=4, melee_defense=4,
    ranged_attack=30, range_distance=500,
    speed=1.0, armor=15, race="human",
    traits=("armored_construct",),
    squad_size=1, cost=450, upkeep=35,
    weapon_strength=5, ranged_strength=50,
    armor_penetration=5, ranged_armor_penetration=60,
    exhaustion_rate=0.0, mass=10.0, size_category="massive",
    damage_immunities=("poison",),
    description="Siege artillery. Extreme range, devastating shots.",
)

HUMAN_GREATSWORDS = UnitStats(
    name="Greatswords", health=130, melee_attack=18, melee_defense=12,
    speed=1.8, charge_bonus=6, armor=25, shield=False,
    squad_size=16, cost=280, upkeep=24, race="human",
    traits=("anti_infantry",),
    weapon_strength=22, armor_penetration=30,
    exhaustion_rate=1.2, mass=2.0,
    description="Elite two-handed infantry. Cleave through lesser troops.",
)

# ═══════════════════════════════════════════════════════════════════════════
# HIGH ELVES — Magic and elegance
# ═══════════════════════════════════════════════════════════════════════════

HE_SPELLBLADES = UnitStats(
    name="Spellblades", health=90, melee_attack=14, melee_defense=12,
    speed=2.2, charge_bonus=4, armor=15, shield=False,
    squad_size=20, cost=200, upkeep=16, race="high_elf",
    traits=(),
    weapon_strength=16, armor_penetration=20,
    damage_type="magical", magic_resistance=20,
    exhaustion_rate=0.9, mass=1.5,
    description="Enchanted blades ignore armor. Graceful and deadly.",
)

HE_PHOENIX_GUARD = UnitStats(
    name="Phoenix Guard", health=120, melee_attack=14, melee_defense=16,
    speed=1.8, charge_bonus=3, armor=25, shield=False,
    squad_size=16, cost=300, upkeep=25, race="high_elf",
    traits=("can_brace", "anti_large"),
    weapon_strength=16, armor_penetration=25,
    damage_immunities=("fire",), magic_resistance=30,
    exhaustion_rate=1.0, mass=1.5,
    description="Elite halberd guard. Fire-immune, magically resistant.",
)

HE_MAGE_APPRENTICES = UnitStats(
    name="Mage Apprentices", health=60, melee_attack=5, melee_defense=4,
    ranged_attack=18, range_distance=280,
    speed=2.0, armor=5, race="high_elf",
    traits=("spellcaster",),
    squad_size=12, cost=250, upkeep=20,
    weapon_strength=6, ranged_strength=22,
    damage_type="magical", magic_resistance=25,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="heavens", spell_list=(LIGHTNING_BOLT,),
    max_mana=30, mana_regen=3.0,
    description="Young mages. Arcane bolts bypass physical armor.",
)

HE_SILVER_HELMS = UnitStats(
    name="Silver Helms", health=120, melee_attack=12, melee_defense=10,
    speed=3.8, charge_bonus=16, armor=22, shield=True,
    squad_size=10, cost=280, upkeep=24, race="high_elf",
    traits=("mounted", "anti_large"),
    weapon_strength=14, armor_penetration=20,
    magic_resistance=15,
    exhaustion_rate=1.0, mass=3.5, size_category="large",
    description="Medium cavalry. Lance-armed, effective against large targets.",
)

HE_DRAGON_PRINCES = UnitStats(
    name="Dragon Princes", health=160, melee_attack=16, melee_defense=12,
    speed=3.6, charge_bonus=24, armor=30, shield=True,
    squad_size=8, cost=400, upkeep=35, race="high_elf",
    traits=("mounted", "fire_attack"),
    weapon_strength=20, armor_penetration=30,
    damage_type="fire", damage_immunities=("fire",), magic_resistance=20,
    exhaustion_rate=1.1, mass=4.0, size_category="large",
    description="Elite cavalry. Flaming lances, fire-immune mounts.",
)

HE_EAGLE_ARCHERS = UnitStats(
    name="Eagle Archers", health=65, melee_attack=5, melee_defense=4,
    ranged_attack=20, range_distance=360,
    speed=2.2, armor=5, race="high_elf",
    squad_size=18, cost=200, upkeep=16,
    weapon_strength=6, ranged_strength=20,
    armor_penetration=5, ranged_armor_penetration=15,
    magic_resistance=10,
    exhaustion_rate=0.7, mass=1.0,
    description="Elven precision. Longest range, highest accuracy.",
)

HE_ARCHMAGE = UnitStats(
    name="Archmage", health=180, melee_attack=10, melee_defense=10,
    ranged_attack=28, range_distance=300,
    speed=2.0, armor=10, race="high_elf",
    traits=("spellcaster",),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=12, ranged_strength=35,
    damage_type="magical", magic_resistance=50,
    armor_penetration=10, ranged_armor_penetration=20,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="heavens", spell_list=(LIGHTNING_BOLT, CHAIN_LIGHTNING, COMET, WIND_BLAST),
    max_mana=80, mana_regen=5.0,
    description="Master of the arcane. Devastating magical artillery.",
)

HE_PHOENIX = UnitStats(
    name="Phoenix", health=600, melee_attack=20, melee_defense=14,
    speed=4.0, charge_bonus=18, armor=20, race="high_elf",
    traits=("flying", "fire_attack", "regenerating", "terror", "massive"),
    squad_size=1, cost=600, upkeep=50,
    weapon_strength=30, armor_penetration=30,
    damage_type="fire", damage_immunities=("fire",), magic_resistance=30,
    exhaustion_rate=0.5, mass=8.0, size_category="massive",
    description="Reborn in flame. Flying, fire-breathing, regenerating.",
)

# ═══════════════════════════════════════════════════════════════════════════
# WOOD ELVES — Forest guerrillas
# ═══════════════════════════════════════════════════════════════════════════

WE_GLADE_RUNNERS = UnitStats(
    name="Glade Runners", health=70, melee_attack=10, melee_defense=8,
    speed=2.8, charge_bonus=4, armor=5, shield=False,
    squad_size=20, cost=120, upkeep=10, race="wood_elf",
    weapon_strength=12, armor_penetration=10,
    exhaustion_rate=0.6, mass=1.0,
    description="Fast skirmisher infantry. Strike and fade.",
)

WE_DEEPWOOD_RANGERS = UnitStats(
    name="Deepwood Rangers", health=60, melee_attack=6, melee_defense=4,
    ranged_attack=20, range_distance=300,
    speed=2.4, armor=5, race="wood_elf",
    traits=("stealthy",),
    squad_size=16, cost=250, upkeep=20,
    weapon_strength=8, ranged_strength=22,
    armor_penetration=5, ranged_armor_penetration=25,
    exhaustion_rate=0.6, mass=1.0,
    description="Elite stealthy archers. Invisible in forests.",
)

WE_WARDANCERS = UnitStats(
    name="Wardancers", health=85, melee_attack=20, melee_defense=14,
    speed=2.8, charge_bonus=8, armor=5, shield=False,
    squad_size=16, cost=280, upkeep=22, race="wood_elf",
    traits=("unbreakable", "frenzy"),
    weapon_strength=22, armor_penetration=30,
    exhaustion_rate=0.7, mass=1.0,
    description="Unbreakable blade-dancers. Frenzy as health drops.",
)

WE_WILD_RIDERS = UnitStats(
    name="Wild Riders", health=100, melee_attack=14, melee_defense=6,
    speed=4.2, charge_bonus=20, armor=10, shield=False,
    squad_size=10, cost=280, upkeep=24, race="wood_elf",
    traits=("mounted",),
    weapon_strength=16, armor_penetration=20,
    exhaustion_rate=0.8, mass=3.0, size_category="large",
    description="Fast cavalry. Devastating charges, fragile if caught.",
)

WE_TREEKIN = UnitStats(
    name="Treekin", health=250, melee_attack=14, melee_defense=18,
    speed=1.5, charge_bonus=8, armor=30, shield=False,
    squad_size=6, cost=300, upkeep=25, race="wood_elf",
    traits=("regenerating", "large"),
    weapon_strength=20, armor_penetration=15,
    damage_vulnerabilities=("fire",),
    exhaustion_rate=0.8, mass=4.0, size_category="large",
    description="Living wood. Tough, regenerating, but fear fire.",
)

WE_TREANT = UnitStats(
    name="Treant", health=700, melee_attack=18, melee_defense=16,
    speed=1.2, charge_bonus=14, armor=25, race="wood_elf",
    traits=("regenerating", "massive", "anti_infantry", "terror"),
    squad_size=1, cost=500, upkeep=40,
    weapon_strength=35, armor_penetration=20,
    damage_vulnerabilities=("fire",),
    exhaustion_rate=0.6, mass=10.0, size_category="massive",
    description="Ancient forest spirit. Crushes infantry, fears fire.",
)

WE_GIANT_EAGLE = UnitStats(
    name="Giant Eagle", health=200, melee_attack=14, melee_defense=10,
    speed=5.0, charge_bonus=12, armor=10, race="wood_elf",
    traits=("flying", "large"),
    squad_size=4, cost=300, upkeep=25,
    weapon_strength=18, armor_penetration=15,
    exhaustion_rate=0.6, mass=3.0, size_category="large",
    description="Swift flyers. Strike from above, harass and scout.",
)

WE_WAYWATCHERS = UnitStats(
    name="Waywatchers", health=55, melee_attack=8, melee_defense=5,
    ranged_attack=24, range_distance=320,
    speed=2.6, armor=5, race="wood_elf",
    traits=("stealthy",),
    squad_size=12, cost=320, upkeep=26,
    weapon_strength=8, ranged_strength=26,
    armor_penetration=10, ranged_armor_penetration=35,
    exhaustion_rate=0.6, mass=1.0,
    description="Elite snipers. Stealthy, armor-piercing arrows.",
)

# ═══════════════════════════════════════════════════════════════════════════
# SEA ELVES — Naval pirates and water magic
# ═══════════════════════════════════════════════════════════════════════════

SE_CORSAIR_REAVERS = UnitStats(
    name="Corsair Reavers", health=85, melee_attack=14, melee_defense=8,
    speed=2.4, charge_bonus=6, armor=10, shield=False,
    squad_size=20, cost=160, upkeep=14, race="sea_elf",
    traits=("poison_attack",),
    weapon_strength=16, armor_penetration=20,
    exhaustion_rate=0.8, mass=1.5,
    description="Fast melee infantry. Poisoned blades sap strength.",
)

SE_TIDE_CALLERS = UnitStats(
    name="Tide Callers", health=60, melee_attack=5, melee_defense=4,
    ranged_attack=18, range_distance=260,
    speed=2.0, armor=5, race="sea_elf",
    traits=("spellcaster",),
    squad_size=12, cost=240, upkeep=20,
    weapon_strength=6, ranged_strength=22,
    damage_type="ice", magic_resistance=20,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="ice", spell_list=(FROST_BOLT,),
    max_mana=30, mana_regen=3.0,
    description="Water mages. Ice bolts slow and shatter.",
)

SE_HARPOONISTS = UnitStats(
    name="Harpoonists", health=70, melee_attack=8, melee_defense=5,
    ranged_attack=16, range_distance=200,
    speed=2.0, armor=8, race="sea_elf",
    traits=("anti_large",),
    squad_size=16, cost=200, upkeep=16,
    weapon_strength=10, ranged_strength=20,
    armor_penetration=10, ranged_armor_penetration=40,
    exhaustion_rate=0.9, mass=1.0,
    description="Anti-large ranged. Harpoons pierce thick hides.",
)

SE_SEA_DRAGON_KNIGHTS = UnitStats(
    name="Sea Dragon Knights", health=140, melee_attack=14, melee_defense=10,
    speed=3.6, charge_bonus=18, armor=20, shield=True,
    squad_size=8, cost=350, upkeep=30, race="sea_elf",
    traits=("mounted", "aquatic"),
    weapon_strength=18, armor_penetration=25,
    exhaustion_rate=1.0, mass=4.0, size_category="large",
    description="Cavalry on sea-drakes. Bonus near water.",
)

SE_STORM_MAGE = UnitStats(
    name="Storm Mage", health=160, melee_attack=8, melee_defense=8,
    ranged_attack=26, range_distance=300,
    speed=2.0, armor=8, race="sea_elf",
    traits=("spellcaster",),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=10, ranged_strength=32,
    damage_type="magical", magic_resistance=40,
    armor_penetration=5, ranged_armor_penetration=15,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="heavens", spell_list=(LIGHTNING_BOLT, CHAIN_LIGHTNING, WIND_BLAST),
    max_mana=60, mana_regen=4.0,
    description="Master of storms. Chain lightning arcs between foes.",
)

SE_KRAKEN_SPAWN = UnitStats(
    name="Kraken Spawn", health=800, melee_attack=22, melee_defense=16,
    speed=1.8, charge_bonus=10, armor=20, race="sea_elf",
    traits=("aquatic", "massive", "terror", "regenerating"),
    squad_size=1, cost=600, upkeep=50,
    weapon_strength=35, armor_penetration=25,
    exhaustion_rate=0.5, mass=12.0, size_category="massive",
    description="Tentacled horror from the deep. Terror incarnate.",
)

# ═══════════════════════════════════════════════════════════════════════════
# SNOW ELVES — Steppe warrior-monks, ice magic
# ═══════════════════════════════════════════════════════════════════════════

SNE_FROST_WARDENS = UnitStats(
    name="Frost Wardens", health=110, melee_attack=12, melee_defense=16,
    speed=1.8, charge_bonus=3, armor=22, shield=True,
    squad_size=20, cost=180, upkeep=15, race="snow_elf",
    traits=("can_brace",),
    weapon_strength=14, armor_penetration=15,
    damage_immunities=("ice",),
    exhaustion_rate=1.0, mass=1.5,
    description="Heavy infantry. Ice-immune, built to hold ground.",
)

SNE_STEPPE_RIDERS = UnitStats(
    name="Steppe Riders", health=80, melee_attack=8, melee_defense=5,
    ranged_attack=14, range_distance=180,
    speed=4.4, charge_bonus=8, armor=8, race="snow_elf",
    traits=("mounted", "fire_while_moving"),
    squad_size=10, cost=240, upkeep=20,
    weapon_strength=10, ranged_strength=16,
    armor_penetration=10, ranged_armor_penetration=10,
    exhaustion_rate=0.7, mass=3.0, size_category="large",
    description="Fast mounted archers. Fire on the move.",
)

SNE_ICE_SHAMANS = UnitStats(
    name="Ice Shamans", health=65, melee_attack=5, melee_defense=4,
    ranged_attack=20, range_distance=280,
    speed=2.0, armor=5, race="snow_elf",
    traits=("spellcaster",),
    squad_size=10, cost=260, upkeep=22,
    weapon_strength=6, ranged_strength=24,
    damage_type="ice", damage_immunities=("ice",), magic_resistance=30,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="ice", spell_list=(FROST_BOLT, BLIZZARD),
    max_mana=40, mana_regen=3.5,
    description="Ice mages. Slow and shatter enemy formations.",
)

SNE_MAMMOTH_RIDERS = UnitStats(
    name="Mammoth Riders", health=800, melee_attack=18, melee_defense=14,
    speed=2.5, charge_bonus=30, armor=25, race="snow_elf",
    traits=("mounted", "massive", "terror"),
    squad_size=1, cost=550, upkeep=45,
    weapon_strength=35, armor_penetration=20,
    damage_immunities=("ice",),
    exhaustion_rate=0.8, mass=12.0, size_category="massive",
    description="War mammoth. Devastating charge, causes terror.",
)

SNE_BLIZZARD_GUARD = UnitStats(
    name="Blizzard Guard", health=120, melee_attack=16, melee_defense=14,
    speed=2.0, charge_bonus=5, armor=20, shield=False,
    squad_size=16, cost=300, upkeep=25, race="snow_elf",
    traits=("anti_large",),
    weapon_strength=20, armor_penetration=25,
    damage_type="ice", damage_immunities=("ice",),
    exhaustion_rate=1.0, mass=1.5,
    description="Elite infantry. Ice-enchanted blades vs large foes.",
)

SNE_FROST_WYRM = UnitStats(
    name="Frost Wyrm", health=700, melee_attack=20, melee_defense=14,
    speed=4.5, charge_bonus=16, armor=20, race="snow_elf",
    traits=("flying", "massive", "terror"),
    squad_size=1, cost=650, upkeep=55,
    weapon_strength=30, ranged_attack=22, range_distance=250,
    ranged_strength=28,
    damage_type="ice", damage_immunities=("ice",), damage_vulnerabilities=("fire",),
    armor_penetration=25, ranged_armor_penetration=15,
    exhaustion_rate=0.5, mass=10.0, size_category="massive",
    description="Dragon of ice. Breathes frost, flies, causes terror.",
)

# ═══════════════════════════════════════════════════════════════════════════
# DARK ELVES — Cruelty, demons, debuffs
# ═══════════════════════════════════════════════════════════════════════════

DE_SHADOWBLADES = UnitStats(
    name="Shadowblades", health=80, melee_attack=16, melee_defense=8,
    speed=2.4, charge_bonus=6, armor=10, shield=False,
    squad_size=20, cost=180, upkeep=15, race="dark_elf",
    traits=("poison_attack", "stealthy"),
    weapon_strength=18, armor_penetration=25,
    exhaustion_rate=0.8, mass=1.0,
    description="Stealthy assassins. Poisoned blades from the shadows.",
)

DE_SLAVE_SOLDIERS = UnitStats(
    name="Slave Soldiers", health=60, melee_attack=6, melee_defense=4,
    speed=2.0, charge_bonus=2, armor=5, shield=True,
    squad_size=35, cost=60, upkeep=3, race="dark_elf",
    weapon_strength=8, armor_penetration=5,
    exhaustion_rate=1.2, mass=1.0,
    description="Expendable fodder. Cheap, numerous, and disposable.",
)

DE_DARKSHARDS = UnitStats(
    name="Darkshards", health=65, melee_attack=6, melee_defense=5,
    ranged_attack=18, range_distance=200,
    speed=2.0, armor=12, race="dark_elf",
    squad_size=16, cost=180, upkeep=15,
    weapon_strength=8, ranged_strength=22,
    armor_penetration=5, ranged_armor_penetration=40,
    exhaustion_rate=0.9, mass=1.0,
    description="Repeater crossbows. Armor-piercing hail of bolts.",
)

DE_COLD_ONE_KNIGHTS = UnitStats(
    name="Cold One Knights", health=160, melee_attack=14, melee_defense=12,
    speed=3.4, charge_bonus=20, armor=28, shield=True,
    squad_size=8, cost=380, upkeep=32, race="dark_elf",
    traits=("mounted", "fear"),
    weapon_strength=18, armor_penetration=25,
    exhaustion_rate=1.1, mass=4.5, size_category="large",
    description="Armored reptilian cavalry. Fear aura.",
)

DE_WITCH_ELVES = UnitStats(
    name="Witch Elves", health=75, melee_attack=22, melee_defense=6,
    speed=2.6, charge_bonus=8, armor=0, shield=False,
    squad_size=20, cost=250, upkeep=20, race="dark_elf",
    traits=("frenzy", "unbreakable", "poison_attack"),
    weapon_strength=26, armor_penetration=30,
    exhaustion_rate=0.6, mass=1.0,
    description="Frenzied blade-dancers. Unbreakable, poisoned, lethal.",
)

DE_HYDRA = UnitStats(
    name="Hydra", health=900, melee_attack=20, melee_defense=14,
    speed=2.0, charge_bonus=12, armor=25, race="dark_elf",
    traits=("regenerating", "massive", "terror", "anti_infantry"),
    squad_size=1, cost=600, upkeep=50,
    weapon_strength=35, armor_penetration=20,
    exhaustion_rate=0.5, mass=10.0, size_category="massive",
    description="Multi-headed beast. Regenerates, causes terror.",
)

DE_DARK_SORCERESS = UnitStats(
    name="Dark Sorceress", health=160, melee_attack=8, melee_defense=8,
    ranged_attack=24, range_distance=280,
    speed=2.0, armor=8, race="dark_elf",
    traits=("spellcaster",),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=10, ranged_strength=30,
    damage_type="magical", magic_resistance=40,
    armor_penetration=5, ranged_armor_penetration=15,
    exhaustion_rate=0.8, mass=1.0,
    spell_school="shadow", spell_list=(SHADOW_BOLT, DREAD, CLOAK_OF_SHADOWS, SOUL_DRAIN),
    max_mana=60, mana_regen=4.0,
    description="Dark magic specialist. Debuffs and drains life.",
)

# ═══════════════════════════════════════════════════════════════════════════
# DWARVES — Mountain holds, heavy armor, engineering
# ═══════════════════════════════════════════════════════════════════════════

DW_IRONBREAKERS = UnitStats(
    name="Ironbreakers", health=140, melee_attack=14, melee_defense=22,
    speed=1.4, charge_bonus=4, armor=45, shield=True,
    squad_size=16, cost=350, upkeep=30, race="dwarf",
    weapon_strength=16, armor_penetration=15,
    magic_resistance=20,
    exhaustion_rate=1.4, mass=2.5,
    description="Heaviest armor in the game. Unbreakable wall of gromril.",
)

DW_TUNNEL_FIGHTERS = UnitStats(
    name="Tunnel Fighters", health=110, melee_attack=12, melee_defense=14,
    speed=1.6, charge_bonus=3, armor=20, shield=True,
    squad_size=20, cost=180, upkeep=15, race="dwarf",
    traits=("burrowing", "anti_large", "can_brace"),
    weapon_strength=14, armor_penetration=25,
    exhaustion_rate=1.0, mass=2.0,
    description="Underground fighters. Anti-large, can tunnel in siege.",
)

DW_THUNDERERS = UnitStats(
    name="Thunderers", health=80, melee_attack=6, melee_defense=6,
    ranged_attack=20, range_distance=220,
    speed=1.4, armor=18, race="dwarf",
    squad_size=16, cost=220, upkeep=18,
    weapon_strength=8, ranged_strength=26,
    armor_penetration=5, ranged_armor_penetration=45,
    magic_resistance=15,
    exhaustion_rate=1.0, mass=1.5,
    description="Dwarven gunpowder infantry. Armor-piercing volleys.",
)

DW_GYROCOPTER = UnitStats(
    name="Gyrocopter", health=200, melee_attack=8, melee_defense=6,
    ranged_attack=16, range_distance=200,
    speed=4.5, armor=15, race="dwarf",
    traits=("flying", "fire_attack", "large"),
    squad_size=3, cost=350, upkeep=30,
    weapon_strength=10, ranged_strength=20,
    damage_type="fire",
    armor_penetration=10, ranged_armor_penetration=30,
    exhaustion_rate=0.0, mass=3.0, size_category="large",
    damage_immunities=("poison",),
    description="Flying war machine. Drops fire bombs from above.",
)

DW_MECH_SUIT = UnitStats(
    name="Mech Suit", health=350, melee_attack=18, melee_defense=16,
    speed=1.8, charge_bonus=10, armor=40, shield=False,
    squad_size=4, cost=400, upkeep=35, race="dwarf",
    traits=("armored_construct", "large"),
    weapon_strength=28, armor_penetration=35,
    damage_immunities=("poison",), magic_resistance=15,
    exhaustion_rate=0.0, mass=5.0, size_category="large",
    description="Steam-powered armor. Immune to morale, poison, fatigue.",
)

DW_CANNON = UnitStats(
    name="Dwarf Cannon", health=350, melee_attack=4, melee_defense=4,
    ranged_attack=28, range_distance=480,
    speed=1.0, armor=20, race="dwarf",
    traits=("armored_construct",),
    squad_size=1, cost=400, upkeep=30,
    weapon_strength=5, ranged_strength=48,
    armor_penetration=5, ranged_armor_penetration=55,
    exhaustion_rate=0.0, mass=8.0, size_category="massive",
    damage_immunities=("poison",),
    description="Dwarven engineering. Long range, devastating payload.",
)

DW_SLAYERS = UnitStats(
    name="Slayers", health=100, melee_attack=22, melee_defense=4,
    speed=2.2, charge_bonus=8, armor=0, shield=False,
    squad_size=16, cost=250, upkeep=20, race="dwarf",
    traits=("frenzy", "unbreakable", "anti_large"),
    weapon_strength=28, armor_penetration=35,
    exhaustion_rate=0.5, mass=1.5,
    description="Seek glorious death. Frenzy, unbreakable, anti-large.",
)

DW_RUNESMITH = UnitStats(
    name="Runesmith", health=200, melee_attack=14, melee_defense=16,
    speed=1.4, armor=30, shield=True, race="dwarf",
    traits=("spellcaster",),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=16, armor_penetration=20,
    magic_resistance=50,
    exhaustion_rate=0.8, mass=2.0,
    spell_school="metal", spell_list=(ENCHANT_ARMOR, SEARING_DOOM, TRANSMUTATION, RUNE_OF_WRATH),
    max_mana=50, mana_regen=3.0,
    description="Rune magic. Buffs armor, debuffs enemies. Highly resistant.",
)

# ═══════════════════════════════════════════════════════════════════════════
# ORCS — Brute force and numbers
# ═══════════════════════════════════════════════════════════════════════════

ORC_BOYZ = UnitStats(
    name="Orc Boyz", health=110, melee_attack=12, melee_defense=8,
    speed=2.0, charge_bonus=5, armor=10, shield=True,
    squad_size=24, cost=120, upkeep=8, race="orc",
    weapon_strength=14, armor_penetration=10,
    exhaustion_rate=1.0, mass=2.0,
    description="Basic orc infantry. Tough, decent stats, cheap.",
)

ORC_GOBLIN_SKIRMISHERS = UnitStats(
    name="Goblin Skirmishers", health=40, melee_attack=4, melee_defense=2,
    ranged_attack=10, range_distance=150,
    speed=2.6, armor=0, race="orc",
    traits=(),
    squad_size=30, cost=60, upkeep=3,
    weapon_strength=4, ranged_strength=10,
    armor_penetration=5, ranged_armor_penetration=5,
    exhaustion_rate=0.8, mass=0.8, size_category="small",
    description="Cheap goblin archers. Numerous but terrible.",
)

ORC_BLACK_ORC_ELITES = UnitStats(
    name="Black Orc Elites", health=160, melee_attack=18, melee_defense=14,
    speed=1.8, charge_bonus=8, armor=30, shield=True,
    squad_size=16, cost=320, upkeep=28, race="orc",
    traits=("anti_infantry",),
    weapon_strength=22, armor_penetration=30,
    exhaustion_rate=1.2, mass=2.5,
    description="Elite armored orcs. Cleave through infantry.",
)

ORC_BOAR_RIDERS = UnitStats(
    name="Boar Riders", health=140, melee_attack=14, melee_defense=8,
    speed=3.5, charge_bonus=22, armor=15, shield=False,
    squad_size=8, cost=280, upkeep=24, race="orc",
    traits=("mounted",),
    weapon_strength=18, armor_penetration=20,
    exhaustion_rate=1.0, mass=4.0, size_category="large",
    description="Devastating charge on war boars. Orcish cavalry.",
)

ORC_TROLL = UnitStats(
    name="Orc Troll", health=300, melee_attack=14, melee_defense=8,
    speed=2.0, charge_bonus=10, armor=10, shield=False,
    squad_size=4, cost=280, upkeep=24, race="orc",
    traits=("regenerating", "fear", "large"),
    weapon_strength=24, armor_penetration=15,
    damage_vulnerabilities=("fire",),
    exhaustion_rate=0.8, mass=4.0, size_category="large",
    description="Big, dumb, regenerating. Fear fire.",
)

ORC_WARBOSS = UnitStats(
    name="Warboss", health=280, melee_attack=24, melee_defense=14,
    speed=2.2, charge_bonus=10, armor=25, shield=True,
    squad_size=1, cost=0, upkeep=0, race="orc",
    traits=("fear",),
    weapon_strength=30, armor_penetration=30,
    exhaustion_rate=0.7, mass=2.5,
    description="Orc champion. Intimidation aura, massive damage.",
)

ORC_ROCK_LOBBA = UnitStats(
    name="Rock Lobba", health=250, melee_attack=4, melee_defense=4,
    ranged_attack=22, range_distance=420,
    speed=0.8, armor=10, race="orc",
    squad_size=1, cost=300, upkeep=22,
    weapon_strength=5, ranged_strength=40,
    armor_penetration=5, ranged_armor_penetration=40,
    exhaustion_rate=0.0, mass=6.0, size_category="massive",
    description="Catapult. Lobs boulders at extreme range.",
)

ORC_GOBLIN_WOLF_RIDERS = UnitStats(
    name="Goblin Wolf Riders", health=50, melee_attack=6, melee_defense=3,
    speed=4.0, charge_bonus=8, armor=5, shield=False,
    squad_size=12, cost=120, upkeep=10, race="orc",
    traits=("mounted",),
    weapon_strength=8, armor_penetration=5,
    exhaustion_rate=0.6, mass=2.0, size_category="small",
    description="Cheap, fast goblin cavalry. Harassment specialists.",
)

# ═══════════════════════════════════════════════════════════════════════════
# UNDEAD — Necromancy and attrition
# ═══════════════════════════════════════════════════════════════════════════

UD_SKELETON_WARRIORS = UnitStats(
    name="Skeleton Warriors", health=60, melee_attack=8, melee_defense=6,
    speed=1.6, charge_bonus=2, armor=10, shield=True,
    squad_size=30, cost=80, upkeep=3, race="undead",
    traits=("undead",),
    weapon_strength=10, armor_penetration=5,
    damage_vulnerabilities=("holy",), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=1.0,
    description="Fragile but tireless. Never rout, never rest.",
)

UD_ZOMBIES = UnitStats(
    name="Zombies", health=80, melee_attack=6, melee_defense=2,
    speed=1.0, charge_bonus=0, armor=0, shield=False,
    squad_size=40, cost=50, upkeep=2, race="undead",
    traits=("undead", "regenerating"),
    weapon_strength=8, armor_penetration=5,
    damage_vulnerabilities=("holy", "fire"), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=1.0,
    description="Slow, numerous, regenerating. Drown enemies in bodies.",
)

UD_GRAVE_GUARD = UnitStats(
    name="Grave Guard", health=100, melee_attack=14, melee_defense=14,
    speed=1.6, charge_bonus=4, armor=25, shield=True,
    squad_size=20, cost=220, upkeep=15, race="undead",
    traits=("undead",),
    weapon_strength=16, armor_penetration=20,
    damage_vulnerabilities=("holy",), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=1.5,
    description="Elite undead infantry. Armored, relentless.",
)

UD_BLACK_KNIGHTS = UnitStats(
    name="Black Knights", health=140, melee_attack=14, melee_defense=10,
    speed=3.6, charge_bonus=20, armor=25, shield=True,
    squad_size=8, cost=320, upkeep=25, race="undead",
    traits=("undead", "mounted", "ethereal"),
    weapon_strength=18, armor_penetration=25,
    damage_type="magical", damage_vulnerabilities=("holy",), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=3.5, size_category="large",
    description="Ghostly cavalry. Ethereal charge phases through lines.",
)

UD_WRAITH = UnitStats(
    name="Wraith", health=120, melee_attack=16, melee_defense=4,
    speed=2.4, charge_bonus=4, armor=0, shield=False,
    squad_size=8, cost=280, upkeep=22, race="undead",
    traits=("undead", "ethereal", "fear"),
    weapon_strength=22, armor_penetration=10,
    damage_type="magical", damage_vulnerabilities=("holy",), damage_immunities=("poison", "physical"),
    exhaustion_rate=0.0, mass=0.5,
    description="Spectral horrors. Immune to physical, weak to holy.",
)

UD_VARGHULF = UnitStats(
    name="Varghulf", health=400, melee_attack=20, melee_defense=10,
    speed=3.8, charge_bonus=14, armor=15, race="undead",
    traits=("undead", "flying", "regenerating", "terror", "large"),
    squad_size=1, cost=400, upkeep=35,
    weapon_strength=30, armor_penetration=25,
    damage_vulnerabilities=("holy", "fire"), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=5.0, size_category="large",
    description="Vampiric bat-beast. Flies, regenerates, causes terror.",
)

UD_BONE_GIANT = UnitStats(
    name="Bone Giant", health=800, melee_attack=18, melee_defense=12,
    speed=1.6, charge_bonus=14, armor=20, race="undead",
    traits=("undead", "massive", "terror", "anti_infantry"),
    squad_size=1, cost=500, upkeep=40,
    weapon_strength=35, armor_penetration=20,
    damage_vulnerabilities=("holy",), damage_immunities=("poison",),
    exhaustion_rate=0.0, mass=10.0, size_category="massive",
    description="Reanimated colossus. Crushes infantry underfoot.",
)

UD_NECROMANCER_LORD = UnitStats(
    name="Necromancer Lord", health=160, melee_attack=8, melee_defense=8,
    ranged_attack=22, range_distance=260,
    speed=1.8, armor=10, race="undead",
    traits=("undead", "spellcaster", "summoner"),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=10, ranged_strength=28,
    damage_type="magical", magic_resistance=40,
    damage_vulnerabilities=("holy",), damage_immunities=("poison",),
    armor_penetration=5, ranged_armor_penetration=15,
    exhaustion_rate=0.0, mass=1.0,
    spell_school="death", spell_list=(RAISE_DEAD, SPIRIT_LEECH, CURSE_OF_YEARS, WIND_OF_DEATH),
    max_mana=80, mana_regen=5.0,
    description="Master of death. Raises the fallen, drains life.",
)

# ═══════════════════════════════════════════════════════════════════════════
# TROLLS / OGRES — Monster faction, few but mighty
# ═══════════════════════════════════════════════════════════════════════════

TO_OGRE_BULLS = UnitStats(
    name="Ogre Bulls", health=250, melee_attack=14, melee_defense=8,
    speed=2.2, charge_bonus=10, armor=10, shield=False,
    squad_size=6, cost=220, upkeep=18, race="troll_ogre",
    traits=("large",),
    weapon_strength=22, armor_penetration=15,
    exhaustion_rate=1.0, mass=4.0, size_category="large",
    description="Basic ogre melee. Tough, hard-hitting, large.",
)

TO_TROLL_WARRIORS = UnitStats(
    name="Troll Warriors", health=300, melee_attack=12, melee_defense=8,
    speed=2.0, charge_bonus=8, armor=10, shield=False,
    squad_size=4, cost=260, upkeep=22, race="troll_ogre",
    traits=("regenerating", "fear", "large"),
    weapon_strength=24, armor_penetration=15,
    damage_vulnerabilities=("fire",),
    exhaustion_rate=0.8, mass=4.5, size_category="large",
    description="Regenerating brutes. Fear fire.",
)

TO_OGRE_LEADBELCHERS = UnitStats(
    name="Ogre Leadbelchers", health=230, melee_attack=12, melee_defense=6,
    ranged_attack=16, range_distance=180,
    speed=2.0, armor=10, race="troll_ogre",
    traits=("large",),
    squad_size=4, cost=280, upkeep=24,
    weapon_strength=18, ranged_strength=24,
    armor_penetration=10, ranged_armor_penetration=35,
    exhaustion_rate=1.0, mass=4.0, size_category="large",
    description="Ogres with crude cannons. Devastating at close range.",
)

TO_STONE_TROLL = UnitStats(
    name="Stone Troll", health=350, melee_attack=14, melee_defense=14,
    speed=1.8, charge_bonus=8, armor=30, shield=False,
    squad_size=4, cost=320, upkeep=28, race="troll_ogre",
    traits=("regenerating", "large"),
    weapon_strength=22, armor_penetration=15,
    magic_resistance=40,
    exhaustion_rate=0.8, mass=5.0, size_category="large",
    description="Rock-skinned trolls. High armor and magic resistance.",
)

TO_SABRETUSK_PACK = UnitStats(
    name="Sabretusk Pack", health=80, melee_attack=14, melee_defense=4,
    speed=4.0, charge_bonus=10, armor=5, shield=False,
    squad_size=8, cost=160, upkeep=12, race="troll_ogre",
    traits=("anti_infantry",),
    weapon_strength=16, armor_penetration=15,
    exhaustion_rate=0.6, mass=2.0,
    description="Fast predator pack. Tears through infantry.",
)

TO_GIANT = UnitStats(
    name="Giant", health=900, melee_attack=20, melee_defense=10,
    speed=2.2, charge_bonus=16, armor=15, race="troll_ogre",
    traits=("massive", "terror", "anti_infantry"),
    squad_size=1, cost=500, upkeep=40,
    weapon_strength=40, armor_penetration=20,
    exhaustion_rate=0.8, mass=12.0, size_category="massive",
    description="Towering monstrosity. Stomps infantry, causes terror.",
)

TO_OGRE_TYRANT = UnitStats(
    name="Ogre Tyrant", health=350, melee_attack=22, melee_defense=14,
    speed=2.2, charge_bonus=12, armor=20, shield=False,
    squad_size=1, cost=0, upkeep=0, race="troll_ogre",
    traits=("large", "fear"),
    weapon_strength=30, armor_penetration=30,
    exhaustion_rate=0.7, mass=5.0, size_category="large",
    description="Ogre champion. Eats enemies to restore health.",
)

# ═══════════════════════════════════════════════════════════════════════════
# BEASTFOLK — Fast, cavalry-focused
# ═══════════════════════════════════════════════════════════════════════════

BF_GOR_WARRIORS = UnitStats(
    name="Gor Warriors", health=100, melee_attack=12, melee_defense=6,
    speed=2.4, charge_bonus=6, armor=5, shield=True,
    squad_size=24, cost=110, upkeep=8, race="beastfolk",
    weapon_strength=14, armor_penetration=10,
    exhaustion_rate=0.8, mass=1.5,
    description="Basic beastfolk infantry. Fast and ferocious.",
)

BF_UNGOR_RAIDERS = UnitStats(
    name="Ungor Raiders", health=55, melee_attack=4, melee_defense=3,
    ranged_attack=10, range_distance=160,
    speed=2.6, armor=0, race="beastfolk",
    squad_size=20, cost=80, upkeep=5,
    weapon_strength=6, ranged_strength=12,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.7, mass=1.0,
    description="Cheap skirmisher ranged. Harass and annoy.",
)

BF_CENTIGORS = UnitStats(
    name="Centigors", health=130, melee_attack=14, melee_defense=6,
    speed=4.0, charge_bonus=18, armor=8, shield=False,
    squad_size=8, cost=260, upkeep=22, race="beastfolk",
    traits=("mounted",),
    weapon_strength=18, armor_penetration=15,
    exhaustion_rate=0.8, mass=3.5, size_category="large",
    description="Half-beast cavalry. Fast, devastating charge.",
)

BF_MINOTAURS = UnitStats(
    name="Minotaurs", health=280, melee_attack=18, melee_defense=8,
    speed=2.8, charge_bonus=22, armor=10, shield=False,
    squad_size=4, cost=320, upkeep=28, race="beastfolk",
    traits=("frenzy", "fear", "large"),
    weapon_strength=28, armor_penetration=30,
    exhaustion_rate=0.8, mass=4.5, size_category="large",
    description="Frenzied bull-beasts. Devastating charge, fear aura.",
)

BF_RAZORGOR_CHARIOT = UnitStats(
    name="Razorgor Chariot", health=250, melee_attack=14, melee_defense=10,
    speed=3.5, charge_bonus=24, armor=15, shield=False,
    squad_size=3, cost=300, upkeep=25, race="beastfolk",
    traits=("mounted", "anti_infantry", "large"),
    weapon_strength=20, armor_penetration=20,
    exhaustion_rate=0.8, mass=5.0, size_category="large",
    description="Beast-drawn chariots. Smash through infantry lines.",
)

BF_BEASTLORD = UnitStats(
    name="Beastlord", health=260, melee_attack=22, melee_defense=12,
    speed=2.6, charge_bonus=10, armor=15, shield=False,
    squad_size=1, cost=0, upkeep=0, race="beastfolk",
    traits=("terror",),
    weapon_strength=28, armor_penetration=30,
    exhaustion_rate=0.6, mass=2.0,
    description="Beast champion. Terror aura, brutal combatant.",
)

BF_JABBERSLYTHE = UnitStats(
    name="Jabberslythe", health=700, melee_attack=18, melee_defense=10,
    speed=3.5, charge_bonus=14, armor=15, race="beastfolk",
    traits=("flying", "massive", "terror", "poison_attack"),
    squad_size=1, cost=550, upkeep=45,
    weapon_strength=30, armor_penetration=25,
    exhaustion_rate=0.6, mass=8.0, size_category="massive",
    description="Flying horror. Poison attacks, terror, massive.",
)

# ═══════════════════════════════════════════════════════════════════════════
# FERAL GOBLINS — Roaming, non-playable
# ═══════════════════════════════════════════════════════════════════════════

GOB_MOB = UnitStats(
    name="Goblin Mob", health=35, melee_attack=4, melee_defense=2,
    speed=2.2, charge_bonus=2, armor=0, shield=False,
    squad_size=40, cost=40, upkeep=2, race="goblin",
    weapon_strength=6, armor_penetration=5,
    exhaustion_rate=1.0, mass=0.8, size_category="small",
    description="Countless little green menaces. Swarm and overwhelm.",
)

GOB_ARCHERS = UnitStats(
    name="Goblin Archers", health=30, melee_attack=2, melee_defense=1,
    ranged_attack=8, range_distance=140,
    speed=2.2, armor=0, race="goblin",
    squad_size=30, cost=40, upkeep=2,
    weapon_strength=3, ranged_strength=8,
    armor_penetration=5, ranged_armor_penetration=5,
    exhaustion_rate=1.0, mass=0.7, size_category="small",
    description="Terrible archers in great numbers.",
)

GOB_SQUIG_RIDERS = UnitStats(
    name="Squig Riders", health=60, melee_attack=10, melee_defense=2,
    speed=3.5, charge_bonus=10, armor=0, shield=False,
    squad_size=12, cost=100, upkeep=8, race="goblin",
    traits=("mounted",),
    weapon_strength=14, armor_penetration=15,
    exhaustion_rate=0.8, mass=2.0, size_category="small",
    description="Bouncing fungi-beasts. Fast, unpredictable, bitey.",
)

GOB_TROLL = UnitStats(
    name="Goblin Troll", health=300, melee_attack=14, melee_defense=8,
    speed=2.0, charge_bonus=10, armor=10, shield=False,
    squad_size=2, cost=200, upkeep=16, race="goblin",
    traits=("regenerating", "fear", "large"),
    weapon_strength=24, armor_penetration=15,
    damage_vulnerabilities=("fire",),
    exhaustion_rate=0.8, mass=4.0, size_category="large",
    description="Trolls allied with goblins. Big and regenerating.",
)

GOB_SHAMAN = UnitStats(
    name="Goblin Shaman", health=80, melee_attack=4, melee_defense=4,
    ranged_attack=14, range_distance=200,
    speed=2.0, armor=0, race="goblin",
    traits=("spellcaster",),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=4, ranged_strength=18,
    damage_type="magical",
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=0.7, size_category="small",
    spell_school="beasts", spell_list=(SUMMON_WOLVES, WILD_FURY),
    max_mana=25, mana_regen=2.5,
    description="Unpredictable magic. Might help, might blow up.",
)

# ═══════════════════════════════════════════════════════════════════════════
# DEMONS — Endgame crisis, non-playable
# ═══════════════════════════════════════════════════════════════════════════

DEMON_BLOODLETTERS = UnitStats(
    name="Bloodletters", health=120, melee_attack=20, melee_defense=10,
    speed=2.4, charge_bonus=8, armor=15, shield=False,
    squad_size=20, cost=300, upkeep=25, race="demon",
    traits=("fire_attack", "fear"),
    weapon_strength=24, armor_penetration=30,
    damage_type="fire", damage_immunities=("fire", "poison"),
    exhaustion_rate=0.0, mass=2.0,
    description="Demonic infantry. Fire swords, fearless, tireless.",
)

DEMON_HELLFIRE_ARCHERS = UnitStats(
    name="Hellfire Archers", health=90, melee_attack=8, melee_defense=6,
    ranged_attack=20, range_distance=260,
    speed=2.2, armor=10, race="demon",
    squad_size=16, cost=280, upkeep=22,
    weapon_strength=10, ranged_strength=24,
    damage_type="fire", damage_immunities=("fire", "poison"),
    armor_penetration=10, ranged_armor_penetration=35,
    exhaustion_rate=0.0, mass=1.5,
    description="Demonic ranged. Fire arrows that pierce armor.",
)

DEMON_HELLHOUNDS = UnitStats(
    name="Hellhounds", health=100, melee_attack=14, melee_defense=4,
    speed=4.5, charge_bonus=12, armor=5, shield=False,
    squad_size=8, cost=200, upkeep=16, race="demon",
    traits=("fire_attack", "fear"),
    weapon_strength=18, armor_penetration=20,
    damage_type="fire", damage_immunities=("fire", "poison"),
    exhaustion_rate=0.0, mass=2.5, size_category="large",
    description="Flaming beasts. Fast, fiery, fear-causing.",
)

DEMON_PRINCE = UnitStats(
    name="Demon Prince", health=1000, melee_attack=24, melee_defense=16,
    speed=4.0, charge_bonus=20, armor=30, race="demon",
    traits=("flying", "massive", "terror", "spellcaster", "fire_attack"),
    squad_size=1, cost=800, upkeep=60,
    weapon_strength=40, armor_penetration=35,
    damage_type="fire", damage_immunities=("fire", "poison"), magic_resistance=40,
    exhaustion_rate=0.0, mass=10.0, size_category="massive",
    spell_school="fire", spell_list=(FIREBALL, INFERNO),
    max_mana=60, mana_regen=4.0,
    description="Winged destroyer. Fire magic, terror, near-invincible.",
)

DEMON_BALROG = UnitStats(
    name="Balrog", health=1200, melee_attack=22, melee_defense=14,
    speed=2.5, charge_bonus=18, armor=25, race="demon",
    traits=("massive", "terror", "fire_attack", "regenerating"),
    squad_size=1, cost=900, upkeep=70,
    weapon_strength=45, armor_penetration=40,
    damage_type="fire", damage_immunities=("fire", "poison"), magic_resistance=30,
    exhaustion_rate=0.0, mass=14.0, size_category="massive",
    description="Ancient fire demon. Regenerating, terrifying, devastating.",
)

DEMON_PIT_FIEND = UnitStats(
    name="Pit Fiend", health=300, melee_attack=14, melee_defense=12,
    ranged_attack=24, range_distance=280,
    speed=2.2, armor=15, race="demon",
    traits=("spellcaster", "summoner", "fear"),
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=18, ranged_strength=30,
    damage_type="fire", damage_immunities=("fire", "poison"), magic_resistance=50,
    armor_penetration=15, ranged_armor_penetration=20,
    exhaustion_rate=0.0, mass=3.0,
    spell_school="fire", spell_list=(FIREBALL, FLAME_WALL, INFERNO, BLAZING_SWORD),
    max_mana=70, mana_regen=5.0,
    description="Demon sorcerer. Summons lesser demons, devastating fire magic.",
)


# ═══════════════════════════════════════════════════════════════════════════
# GENERAL TYPES — Used by all races until race-specific heroes are set up
# ═══════════════════════════════════════════════════════════════════════════

GENERAL_COMMANDER = UnitStats(
    name="Commander", health=200, melee_attack=18, melee_defense=16,
    speed=2.25, charge_bonus=8, armor=25, shield=True,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=20, armor_penetration=20,
    exhaustion_rate=0.8, mass=2.0,
    description="A balanced leader. Boosts morale of nearby troops.",
)

GENERAL_CHAMPION = UnitStats(
    name="Champion", health=250, melee_attack=28, melee_defense=12,
    speed=2.4, charge_bonus=12, armor=20, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=32, armor_penetration=40,
    exhaustion_rate=0.7, mass=1.5,
    description="A dueling monster. Seeks out enemy generals.",
)

GENERAL_STRATEGIST = UnitStats(
    name="Strategist", health=140, melee_attack=10, melee_defense=10,
    ranged_attack=22, range_distance=200,
    speed=2.1, armor=10, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=12, ranged_strength=26,
    armor_penetration=10, ranged_armor_penetration=30,
    exhaustion_rate=0.9, mass=1.0,
    description="Boosts ranged units and weakens enemy morale from afar.",
)

# ═══════════════════════════════════════════════════════════════════════════
# LEGACY ALIASES — Keep old names working for save compat and existing code
# ═══════════════════════════════════════════════════════════════════════════

MILITIA = HUMAN_LEVY_MILITIA
SWORDSMEN = HUMAN_MEN_AT_ARMS
SPEARMEN = HUMAN_HALBERDIERS
HEAVY_INFANTRY = HUMAN_GREATSWORDS
BERSERKERS = UnitStats(
    name="Berserkers", health=110, melee_attack=22, melee_defense=4,
    speed=2.5, charge_bonus=10, armor=5, shield=False,
    squad_size=16, cost=250, upkeep=20, race="human",
    traits=("frenzy", "unbreakable"),
    weapon_strength=28, armor_penetration=35,
    exhaustion_rate=0.6, mass=1.5,
    description="All offense, no defense. Rage fuels them past exhaustion.",
)
ARCHERS = HUMAN_LONGBOWMEN
CROSSBOWMEN = HUMAN_HANDGUNNERS
SKIRMISHERS = UnitStats(
    name="Skirmishers", health=55, melee_attack=6, melee_defense=4,
    ranged_attack=10, range_distance=150,
    speed=2.8, armor=0, race="human",
    squad_size=16, cost=100, upkeep=8,
    weapon_strength=8, ranged_strength=12,
    armor_penetration=10, ranged_armor_penetration=15,
    exhaustion_rate=0.7, mass=1.0,
    description="Fast and annoying. Hit and run specialists.",
)
LIGHT_CAVALRY = UnitStats(
    name="Light Cavalry", health=90, melee_attack=10, melee_defense=6,
    speed=4.0, charge_bonus=12, armor=10, race="human",
    traits=("mounted",),
    squad_size=12, cost=200, upkeep=18,
    weapon_strength=12, armor_penetration=10,
    exhaustion_rate=0.8, mass=3.0, size_category="large",
    description="Fast flankers. Great for running down routers.",
)
HEAVY_CAVALRY = HUMAN_KNIGHTS
HORSE_ARCHERS = HUMAN_PISTOLIERS

# Legacy specialty aliases
IRONCLAD_LEGIONNAIRES = DW_IRONBREAKERS
SIEGE_ENGINEERS = UnitStats(
    name="Siege Engineers", health=90, melee_attack=8, melee_defense=8,
    speed=1.5, charge_bonus=0, armor=15, shield=False, race="human",
    squad_size=12, cost=250, upkeep=20,
    weapon_strength=10, armor_penetration=10,
    exhaustion_rate=1.0, mass=1.5,
    description="Battlefield utility specialists.",
)
SHADOWSTALKERS = WE_DEEPWOOD_RANGERS
TREEWARDEN_SENTINELS = WE_TREEKIN
SANDSTORM_RIDERS = SNE_STEPPE_RIDERS
DUNE_ASSASSINS = DE_SHADOWBLADES
NORTHERN_BERSERKERS = DW_SLAYERS
SHIELDWALL_VETERANS = DW_IRONBREAKERS
CORSAIR_CROSSBOWMEN = SE_HARPOONISTS
MARINE_BOARDERS = SE_CORSAIR_REAVERS
KHANS_CHOSEN = ORC_BOAR_RIDERS
STEPPE_HORSE_ARCHERS = ORC_GOBLIN_WOLF_RIDERS
TEMPLAR_KNIGHTS = HE_DRAGON_PRINCES
FLAGELLANTS = UD_SKELETON_WARRIORS


# ═══════════════════════════════════════════════════════════════════════════
# RACIAL ROSTERS — Maps race_id to available unit types
# ═══════════════════════════════════════════════════════════════════════════

RACE_ROSTER = {
    "human": [
        HUMAN_LEVY_MILITIA, HUMAN_MEN_AT_ARMS, HUMAN_HALBERDIERS,
        HUMAN_LONGBOWMEN, HUMAN_HANDGUNNERS, HUMAN_KNIGHTS,
        HUMAN_PISTOLIERS, HUMAN_WAR_WAGON, HUMAN_CANNON,
        HUMAN_GREATSWORDS,
    ],
    "high_elf": [
        HE_SPELLBLADES, HE_PHOENIX_GUARD, HE_MAGE_APPRENTICES,
        HE_SILVER_HELMS, HE_DRAGON_PRINCES, HE_EAGLE_ARCHERS,
        HE_PHOENIX,
    ],
    "wood_elf": [
        WE_GLADE_RUNNERS, WE_DEEPWOOD_RANGERS, WE_WARDANCERS,
        WE_WILD_RIDERS, WE_TREEKIN, WE_TREANT,
        WE_GIANT_EAGLE, WE_WAYWATCHERS,
    ],
    "sea_elf": [
        SE_CORSAIR_REAVERS, SE_TIDE_CALLERS, SE_HARPOONISTS,
        SE_SEA_DRAGON_KNIGHTS, SE_KRAKEN_SPAWN,
    ],
    "snow_elf": [
        SNE_FROST_WARDENS, SNE_STEPPE_RIDERS, SNE_ICE_SHAMANS,
        SNE_MAMMOTH_RIDERS, SNE_BLIZZARD_GUARD, SNE_FROST_WYRM,
    ],
    "dark_elf": [
        DE_SHADOWBLADES, DE_SLAVE_SOLDIERS, DE_DARKSHARDS,
        DE_COLD_ONE_KNIGHTS, DE_WITCH_ELVES, DE_HYDRA,
    ],
    "dwarf": [
        DW_IRONBREAKERS, DW_TUNNEL_FIGHTERS, DW_THUNDERERS,
        DW_GYROCOPTER, DW_MECH_SUIT, DW_CANNON,
        DW_SLAYERS,
    ],
    "orc": [
        ORC_BOYZ, ORC_GOBLIN_SKIRMISHERS, ORC_BLACK_ORC_ELITES,
        ORC_BOAR_RIDERS, ORC_TROLL, ORC_ROCK_LOBBA,
        ORC_GOBLIN_WOLF_RIDERS,
    ],
    "undead": [
        UD_SKELETON_WARRIORS, UD_ZOMBIES, UD_GRAVE_GUARD,
        UD_BLACK_KNIGHTS, UD_WRAITH, UD_VARGHULF,
        UD_BONE_GIANT,
    ],
    "troll_ogre": [
        TO_OGRE_BULLS, TO_TROLL_WARRIORS, TO_OGRE_LEADBELCHERS,
        TO_STONE_TROLL, TO_SABRETUSK_PACK, TO_GIANT,
    ],
    "beastfolk": [
        BF_GOR_WARRIORS, BF_UNGOR_RAIDERS, BF_CENTIGORS,
        BF_MINOTAURS, BF_RAZORGOR_CHARIOT, BF_JABBERSLYTHE,
    ],
    "goblin": [
        GOB_MOB, GOB_ARCHERS, GOB_SQUIG_RIDERS, GOB_TROLL,
    ],
    "demon": [
        DEMON_BLOODLETTERS, DEMON_HELLFIRE_ARCHERS, DEMON_HELLHOUNDS,
    ],
}

# Hero units per race (used for general assignment)
RACE_HEROES = {
    "human": [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST],
    "high_elf": [HE_ARCHMAGE, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "wood_elf": [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST],
    "sea_elf": [SE_STORM_MAGE, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "snow_elf": [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST],
    "dark_elf": [DE_DARK_SORCERESS, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "dwarf": [DW_RUNESMITH, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "orc": [ORC_WARBOSS, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "undead": [UD_NECROMANCER_LORD, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "troll_ogre": [TO_OGRE_TYRANT, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "beastfolk": [BF_BEASTLORD, GENERAL_COMMANDER, GENERAL_CHAMPION],
    "goblin": [GOB_SHAMAN],
    "demon": [DEMON_PIT_FIEND, DEMON_PRINCE],
}


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY RECRUITMENT POOLS — Kept for backward compatibility
# ═══════════════════════════════════════════════════════════════════════════

INFANTRY_ROSTER = [MILITIA, SWORDSMEN, SPEARMEN, HEAVY_INFANTRY, BERSERKERS]
RANGED_ROSTER = [ARCHERS, CROSSBOWMEN, SKIRMISHERS]
CAVALRY_ROSTER = [LIGHT_CAVALRY, HEAVY_CAVALRY, HORSE_ARCHERS]
GENERAL_ROSTER = [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST]

ALL_RECRUITABLE = INFANTRY_ROSTER + RANGED_ROSTER + CAVALRY_ROSTER

# Legacy faction specialty units (team index keyed)
FACTION_SPECIALTY_UNITS = {
    1: [IRONCLAD_LEGIONNAIRES, SIEGE_ENGINEERS],
    2: [SHADOWSTALKERS, TREEWARDEN_SENTINELS],
    3: [SANDSTORM_RIDERS, DUNE_ASSASSINS],
    4: [NORTHERN_BERSERKERS, SHIELDWALL_VETERANS],
    5: [CORSAIR_CROSSBOWMEN, MARINE_BOARDERS],
    6: [KHANS_CHOSEN, STEPPE_HORSE_ARCHERS],
    7: [TEMPLAR_KNIGHTS, FLAGELLANTS],
    8: [],
}
