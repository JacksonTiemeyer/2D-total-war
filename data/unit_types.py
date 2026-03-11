"""Unit type definitions. All squad templates and stats live here."""


class UnitStats:
    """Stats for an individual soldier within a squad."""
    def __init__(self, name, health, melee_attack, melee_defense,
                 ranged_attack=0, range_distance=0, speed=2.0,
                 charge_bonus=0, armor=0, shield=False,
                 squad_size=20, cost=100, upkeep=10,
                 weapon_strength=10, ranged_strength=0,
                 armor_penetration=0, ranged_armor_penetration=0,
                 exhaustion_rate=1.0, mass=1.0,
                 can_brace=False,
                 description=""):
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
        self.can_brace = can_brace                   # can brace vs charges
        self.description = description


# === INFANTRY ===

MILITIA = UnitStats(
    name="Militia",
    health=80, melee_attack=8, melee_defense=6,
    speed=2.0, charge_bonus=2, armor=5, shield=True,
    squad_size=30, cost=75, upkeep=5,
    weapon_strength=8, armor_penetration=5,
    exhaustion_rate=1.2, mass=1.0,
    description="Cheap and plentiful. They hold the line... barely.",
)

SWORDSMEN = UnitStats(
    name="Swordsmen",
    health=100, melee_attack=12, melee_defense=10,
    speed=2.0, charge_bonus=4, armor=15, shield=True,
    squad_size=24, cost=150, upkeep=12,
    weapon_strength=14, armor_penetration=15,
    exhaustion_rate=1.0, mass=1.0,
    description="Reliable infantry. The backbone of any army.",
)

SPEARMEN = UnitStats(
    name="Spearmen",
    health=90, melee_attack=10, melee_defense=14,
    speed=1.8, charge_bonus=2, armor=10, shield=True,
    squad_size=24, cost=120, upkeep=10,
    weapon_strength=12, armor_penetration=20,
    exhaustion_rate=1.0, mass=1.0, can_brace=True,
    description="Anti-cavalry specialists. Brace for impact!",
)

HEAVY_INFANTRY = UnitStats(
    name="Heavy Infantry",
    health=140, melee_attack=16, melee_defense=14,
    speed=1.5, charge_bonus=6, armor=30, shield=True,
    squad_size=16, cost=300, upkeep=25,
    weapon_strength=20, armor_penetration=25,
    exhaustion_rate=1.4, mass=1.3,
    description="Armored elite. Slow but devastating. Tires faster under all that steel.",
)

BERSERKERS = UnitStats(
    name="Berserkers",
    health=110, melee_attack=22, melee_defense=4,
    speed=2.5, charge_bonus=10, armor=5, shield=False,
    squad_size=16, cost=250, upkeep=20,
    weapon_strength=28, armor_penetration=35,
    exhaustion_rate=0.6, mass=1.1,
    description="All offense, no defense. Rage fuels them past exhaustion.",
)

# === RANGED ===

ARCHERS = UnitStats(
    name="Archers",
    health=60, melee_attack=4, melee_defense=3,
    ranged_attack=14, range_distance=250,
    speed=2.0, armor=5,
    squad_size=20, cost=130, upkeep=10,
    weapon_strength=6, ranged_strength=16,
    armor_penetration=5, ranged_armor_penetration=10,
    exhaustion_rate=0.8, mass=0.8,
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
    exhaustion_rate=0.9, mass=0.9,
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
    exhaustion_rate=0.7, mass=0.7,
    description="Fast and annoying. Hit and run specialists. Never seem to tire.",
)

# === CAVALRY ===

LIGHT_CAVALRY = UnitStats(
    name="Light Cavalry",
    health=90, melee_attack=10, melee_defense=6,
    speed=4.0, charge_bonus=12, armor=10,
    squad_size=12, cost=200, upkeep=18,
    weapon_strength=12, armor_penetration=10,
    exhaustion_rate=0.8, mass=2.0,
    description="Fast flankers. Great for running down routers.",
)

HEAVY_CAVALRY = UnitStats(
    name="Heavy Cavalry",
    health=150, melee_attack=14, melee_defense=10,
    speed=3.5, charge_bonus=20, armor=25, shield=True,
    squad_size=8, cost=350, upkeep=30,
    weapon_strength=18, armor_penetration=30,
    exhaustion_rate=1.3, mass=3.0,
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
    exhaustion_rate=0.9, mass=1.8,
    description="Shoot and scoot. Your opponent will hate you.",
)

# === GENERAL TYPES ===

GENERAL_COMMANDER = UnitStats(
    name="Commander",
    health=200, melee_attack=18, melee_defense=16,
    speed=3.0, charge_bonus=8, armor=25, shield=True,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=20, armor_penetration=20,
    exhaustion_rate=0.8, mass=2.0,
    description="A balanced leader. Boosts morale of nearby troops.",
)

GENERAL_CHAMPION = UnitStats(
    name="Champion",
    health=250, melee_attack=28, melee_defense=12,
    speed=3.2, charge_bonus=12, armor=20, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=32, armor_penetration=40,
    exhaustion_rate=0.7, mass=1.5,
    description="A dueling monster. Seeks out enemy generals.",
)

GENERAL_STRATEGIST = UnitStats(
    name="Strategist",
    health=140, melee_attack=10, melee_defense=10,
    ranged_attack=22, range_distance=200,
    speed=2.8, armor=10, shield=False,
    squad_size=1, cost=0, upkeep=0,
    weapon_strength=12, ranged_strength=26,
    armor_penetration=10, ranged_armor_penetration=30,
    exhaustion_rate=0.9, mass=1.0,
    description="Boosts ranged units and weakens enemy morale from afar.",
)

# Recruitment pools
INFANTRY_ROSTER = [MILITIA, SWORDSMEN, SPEARMEN, HEAVY_INFANTRY, BERSERKERS]
RANGED_ROSTER = [ARCHERS, CROSSBOWMEN, SKIRMISHERS]
CAVALRY_ROSTER = [LIGHT_CAVALRY, HEAVY_CAVALRY, HORSE_ARCHERS]
GENERAL_ROSTER = [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST]

ALL_RECRUITABLE = INFANTRY_ROSTER + RANGED_ROSTER + CAVALRY_ROSTER
