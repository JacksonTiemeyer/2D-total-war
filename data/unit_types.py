"""Unit type definitions. All squad templates and stats live here."""


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
                 spell_list=()):
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


# === INFANTRY ===

MILITIA = UnitStats(
    name="Militia",
    health=80, melee_attack=8, melee_defense=6,
    speed=2.0, charge_bonus=2, armor=5, shield=True,
    squad_size=30, cost=75, upkeep=5,
    weapon_strength=8, armor_penetration=5,
    exhaustion_rate=1.2, mass=1.5,
    description="Cheap and plentiful. They hold the line... barely.",
)

SWORDSMEN = UnitStats(
    name="Swordsmen",
    health=100, melee_attack=12, melee_defense=10,
    speed=2.0, charge_bonus=4, armor=15, shield=True,
    squad_size=24, cost=150, upkeep=12,
    weapon_strength=14, armor_penetration=15,
    exhaustion_rate=1.0, mass=1.5,
    description="Reliable infantry. The backbone of any army.",
)

SPEARMEN = UnitStats(
    name="Spearmen",
    health=90, melee_attack=10, melee_defense=14,
    speed=1.8, charge_bonus=2, armor=10, shield=True,
    squad_size=24, cost=120, upkeep=10,
    weapon_strength=12, armor_penetration=20,
    exhaustion_rate=1.0, mass=1.5, can_brace=True, is_spear=True,
    description="Anti-cavalry specialists. Brace for impact!",
)

HEAVY_INFANTRY = UnitStats(
    name="Heavy Infantry",
    health=140, melee_attack=16, melee_defense=14,
    speed=1.5, charge_bonus=6, armor=30, shield=True,
    squad_size=16, cost=300, upkeep=25,
    weapon_strength=20, armor_penetration=25,
    exhaustion_rate=1.4, mass=2.0,
    description="Armored elite. Slow but devastating. Tires faster under all that steel.",
)

BERSERKERS = UnitStats(
    name="Berserkers",
    health=110, melee_attack=22, melee_defense=4,
    speed=2.5, charge_bonus=10, armor=5, shield=False,
    squad_size=16, cost=250, upkeep=20,
    weapon_strength=28, armor_penetration=35,
    exhaustion_rate=0.6, mass=1.5,
    description="All offense, no defense. Rage fuels them past exhaustion.",
)

# === RANGED ===

ARCHERS = UnitStats(
    name="Archers",
    health=60, melee_attack=4, melee_defense=3,
    ranged_attack=14, range_distance=320,
    speed=2.0, armor=5,
    squad_size=20, cost=130, upkeep=10,
    weapon_strength=6, ranged_strength=16,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=1.0,
    description="Rain arrows upon your foes from a safe distance.",
)

CROSSBOWMEN = UnitStats(
    name="Crossbowmen",
    health=70, melee_attack=5, melee_defense=4,
    ranged_attack=20, range_distance=200,
    speed=1.8, armor=10,
    squad_size=16, cost=180, upkeep=15,
    weapon_strength=7, ranged_strength=24,
    armor_penetration=5, ranged_armor_penetration=40,
    exhaustion_rate=0.9, mass=1.0,
    description="Slower to fire, but bolts punch through armor like butter.",
)

SKIRMISHERS = UnitStats(
    name="Skirmishers",
    health=55, melee_attack=6, melee_defense=4,
    ranged_attack=10, range_distance=150,
    speed=2.8, armor=0,
    squad_size=16, cost=100, upkeep=8,
    weapon_strength=8, ranged_strength=12,
    armor_penetration=10, ranged_armor_penetration=15,
    exhaustion_rate=0.7, mass=1.0,
    description="Fast and annoying. Hit and run specialists. Never seem to tire.",
)

# === CAVALRY ===

LIGHT_CAVALRY = UnitStats(
    name="Light Cavalry",
    health=90, melee_attack=10, melee_defense=6,
    speed=4.0, charge_bonus=12, armor=10,
    squad_size=12, cost=200, upkeep=18,
    weapon_strength=12, armor_penetration=10,
    exhaustion_rate=0.8, mass=3.0,
    description="Fast flankers. Great for running down routers.",
)

HEAVY_CAVALRY = UnitStats(
    name="Heavy Cavalry",
    health=150, melee_attack=14, melee_defense=10,
    speed=3.5, charge_bonus=20, armor=25, shield=True,
    squad_size=8, cost=350, upkeep=30,
    weapon_strength=18, armor_penetration=30,
    exhaustion_rate=1.3, mass=4.5,
    description="The hammer to your infantry's anvil. Massive charge impact.",
)

HORSE_ARCHERS = UnitStats(
    name="Horse Archers",
    health=70, melee_attack=5, melee_defense=3,
    ranged_attack=12, range_distance=180,
    speed=4.2, charge_bonus=4, armor=5,
    squad_size=10, cost=220, upkeep=20,
    weapon_strength=7, ranged_strength=14,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.9, mass=3.0,
    can_fire_while_moving=True,
    description="Shoot and scoot. Your opponent will hate you.",
)

# === GENERAL TYPES ===

GENERAL_COMMANDER = UnitStats(
    name="Commander",
    health=200, melee_attack=18, melee_defense=16,
    speed=2.25, charge_bonus=8, armor=25, shield=True,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=20, armor_penetration=20,
    exhaustion_rate=0.8, mass=2.0,
    description="A balanced leader. Boosts morale of nearby troops.",
)

GENERAL_CHAMPION = UnitStats(
    name="Champion",
    health=250, melee_attack=28, melee_defense=12,
    speed=2.4, charge_bonus=12, armor=20, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=32, armor_penetration=40,
    exhaustion_rate=0.7, mass=1.5,
    description="A dueling monster. Seeks out enemy generals.",
)

GENERAL_STRATEGIST = UnitStats(
    name="Strategist",
    health=140, melee_attack=10, melee_defense=10,
    ranged_attack=22, range_distance=200,
    speed=2.1, armor=10, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=12, ranged_strength=26,
    armor_penetration=10, ranged_armor_penetration=30,
    exhaustion_rate=0.9, mass=1.0,
    description="Boosts ranged units and weakens enemy morale from afar.",
)

# === FACTION SPECIALTY UNITS (A9) ===

# Iron Empire
IRONCLAD_LEGIONNAIRES = UnitStats(
    name="Ironclad Legionnaires",
    health=180, melee_attack=14, melee_defense=20,
    speed=1.2, charge_bonus=4, armor=45, shield=True,
    squad_size=16, cost=400, upkeep=35,
    weapon_strength=16, armor_penetration=15,
    exhaustion_rate=1.6, mass=3.0, can_brace=True,
    description="Ultra-heavy infantry. Nearly immovable in defensive stance.",
)

SIEGE_ENGINEERS = UnitStats(
    name="Siege Engineers",
    health=90, melee_attack=8, melee_defense=8,
    speed=1.5, charge_bonus=0, armor=15, shield=False,
    squad_size=12, cost=250, upkeep=20,
    weapon_strength=10, armor_penetration=10,
    exhaustion_rate=1.0, mass=1.5,
    description="Battlefield utility specialists. Sturdy builders and fighters.",
)

# Forest Alliance
SHADOWSTALKERS = UnitStats(
    name="Shadowstalkers",
    health=55, melee_attack=6, melee_defense=3,
    ranged_attack=18, range_distance=220,
    speed=2.6, armor=0,
    squad_size=14, cost=280, upkeep=22,
    weapon_strength=6, ranged_strength=20,
    armor_penetration=5, ranged_armor_penetration=20,
    exhaustion_rate=0.6, mass=1.0,
    description="Stealth archers. Invisible until they fire or enemies get close.",
)

TREEWARDEN_SENTINELS = UnitStats(
    name="Treewarden Sentinels",
    health=120, melee_attack=12, melee_defense=16,
    speed=2.2, charge_bonus=3, armor=15, shield=True,
    squad_size=18, cost=200, upkeep=16,
    weapon_strength=14, armor_penetration=15,
    exhaustion_rate=0.9, mass=1.5, can_brace=True, is_spear=True,
    description="Forest spearmen. Gain bonuses fighting among the trees.",
)

# Desert Raiders
SANDSTORM_RIDERS = UnitStats(
    name="Sandstorm Riders",
    health=75, melee_attack=7, melee_defense=4,
    ranged_attack=14, range_distance=170,
    speed=4.5, charge_bonus=6, armor=5,
    squad_size=10, cost=300, upkeep=25,
    weapon_strength=8, ranged_strength=16,
    armor_penetration=5, ranged_armor_penetration=15,
    exhaustion_rate=0.8, mass=3.0,
    can_fire_while_moving=True,
    description="Horse archers who fire while moving. The only ones who can.",
)

DUNE_ASSASSINS = UnitStats(
    name="Dune Assassins",
    health=65, melee_attack=20, melee_defense=5,
    speed=3.5, charge_bonus=18, armor=5, shield=False,
    squad_size=10, cost=260, upkeep=22,
    weapon_strength=24, armor_penetration=30,
    exhaustion_rate=0.7, mass=1.0,
    description="Lightning-fast shock troops. Deadly on the charge, fragile in prolonged melee.",
)

# Northern Holds
NORTHERN_BERSERKERS = UnitStats(
    name="Berserker Ulfhednar",
    health=130, melee_attack=26, melee_defense=2,
    speed=2.8, charge_bonus=14, armor=0, shield=False,
    squad_size=12, cost=320, upkeep=28,
    weapon_strength=34, armor_penetration=40,
    exhaustion_rate=0.3, mass=1.5,
    description="Ignore exhaustion. Gain damage as health drops. Cannot rout.",
)

SHIELDWALL_VETERANS = UnitStats(
    name="Shieldwall Veterans",
    health=160, melee_attack=12, melee_defense=22,
    speed=1.3, charge_bonus=2, armor=35, shield=True,
    squad_size=16, cost=350, upkeep=30,
    weapon_strength=14, armor_penetration=10,
    exhaustion_rate=1.2, mass=2.5, can_brace=True, is_spear=True,
    description="Highest brace bonus in the game. Massive morale. Immovable wall.",
)

# Maritime Republic
CORSAIR_CROSSBOWMEN = UnitStats(
    name="Corsair Crossbowmen",
    health=75, melee_attack=7, melee_defense=5,
    ranged_attack=22, range_distance=180,
    speed=2.0, armor=12,
    squad_size=14, cost=240, upkeep=18,
    weapon_strength=8, ranged_strength=28,
    armor_penetration=10, ranged_armor_penetration=50,
    exhaustion_rate=0.9, mass=1.0,
    description="Shorter range than archers but devastating armor-piercing bolts.",
)

MARINE_BOARDERS = UnitStats(
    name="Marine Boarders",
    health=100, melee_attack=16, melee_defense=10,
    speed=2.6, charge_bonus=6, armor=12, shield=False,
    squad_size=18, cost=220, upkeep=18,
    weapon_strength=18, armor_penetration=25,
    exhaustion_rate=0.8, mass=1.5, is_spear=True,
    description="Fast infantry with hook weapons. Excellent against cavalry.",
)

# Steppe Horde
KHANS_CHOSEN = UnitStats(
    name="Khan's Chosen",
    health=180, melee_attack=18, melee_defense=12,
    speed=3.8, charge_bonus=28, armor=30, shield=True,
    squad_size=8, cost=450, upkeep=40,
    weapon_strength=22, armor_penetration=35,
    exhaustion_rate=1.2, mass=4.0,
    description="Elite heavy cavalry. Highest mass and charge bonus in the game.",
)

STEPPE_HORSE_ARCHERS = UnitStats(
    name="Steppe Horse Archers",
    health=65, melee_attack=4, melee_defense=3,
    ranged_attack=13, range_distance=190,
    speed=4.6, charge_bonus=3, armor=3,
    squad_size=12, cost=240, upkeep=20,
    weapon_strength=6, ranged_strength=15,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.7, mass=3.0,
    can_fire_while_moving=True,
    description="Lighter and faster than other horse archers. Masters of kiting.",
)

# Holy Order
TEMPLAR_KNIGHTS = UnitStats(
    name="Templar Knights",
    health=170, melee_attack=16, melee_defense=14,
    speed=3.6, charge_bonus=22, armor=35, shield=True,
    squad_size=8, cost=420, upkeep=38,
    weapon_strength=20, armor_penetration=25,
    exhaustion_rate=1.1, mass=3.5,
    description="Heavy cavalry with a morale aura. Nearby allies gain courage.",
)

FLAGELLANTS = UnitStats(
    name="Flagellants",
    health=70, melee_attack=18, melee_defense=2,
    speed=2.4, charge_bonus=6, armor=0, shield=False,
    squad_size=30, cost=100, upkeep=5,
    weapon_strength=22, armor_penetration=20,
    exhaustion_rate=0.5, mass=1.0,
    description="Cheap zealot swarm. High damage, no defense, immune to rout.",
)

# Recruitment pools
INFANTRY_ROSTER = [MILITIA, SWORDSMEN, SPEARMEN, HEAVY_INFANTRY, BERSERKERS]
RANGED_ROSTER = [ARCHERS, CROSSBOWMEN, SKIRMISHERS]
CAVALRY_ROSTER = [LIGHT_CAVALRY, HEAVY_CAVALRY, HORSE_ARCHERS]
GENERAL_ROSTER = [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST]

ALL_RECRUITABLE = INFANTRY_ROSTER + RANGED_ROSTER + CAVALRY_ROSTER

# Faction specialty units keyed by faction team index
# Team indices: 1=Iron Empire, 2=Forest Alliance, 3=Desert Raiders,
# 4=Northern Holds, 5=Maritime Republic, 6=Steppe Horde, 7=Holy Order, 8=Free Cities
FACTION_SPECIALTY_UNITS = {
    1: [IRONCLAD_LEGIONNAIRES, SIEGE_ENGINEERS],
    2: [SHADOWSTALKERS, TREEWARDEN_SENTINELS],
    3: [SANDSTORM_RIDERS, DUNE_ASSASSINS],
    4: [NORTHERN_BERSERKERS, SHIELDWALL_VETERANS],
    5: [CORSAIR_CROSSBOWMEN, MARINE_BOARDERS],
    6: [KHANS_CHOSEN, STEPPE_HORSE_ARCHERS],
    7: [TEMPLAR_KNIGHTS, FLAGELLANTS],
    8: [],  # Free Cities hire mercenaries, no unique troops
}
