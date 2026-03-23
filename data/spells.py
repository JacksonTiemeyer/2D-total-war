"""Spell definitions — all spells organized by school.

Each spell defines its name, school, mana cost, cooldown, cast time,
range, area of effect, and effect callback.

Full implementation in Batch 11 (Magic System).
"""


class Spell:
    """Definition of a castable spell."""

    def __init__(self, name, school, mana_cost, cooldown_seconds,
                 cast_time_seconds=1.0, range_distance=300,
                 aoe_radius=0, damage=0, damage_type="magical",
                 duration_seconds=0, description="",
                 effect_type="damage", targeting="unit",
                 heal=0):
        self.name = name
        self.school = school
        self.mana_cost = mana_cost
        self.cooldown_seconds = cooldown_seconds
        self.cast_time_seconds = cast_time_seconds
        self.range_distance = range_distance
        self.aoe_radius = aoe_radius
        self.damage = damage
        self.heal = heal
        self.damage_type = damage_type
        self.duration_seconds = duration_seconds
        self.description = description
        self.effect_type = effect_type  # "damage", "buff", "debuff", "summon", "terrain"
        self.targeting = targeting  # "self", "unit", "area", "projectile"
        # Runtime cooldown tracking (per-caster, set externally)
        self.cooldown_remaining = 0


# ── Spell Schools ────────────────────────────────────────────────────────

SCHOOL_FIRE = "fire"
SCHOOL_ICE = "ice"
SCHOOL_SHADOW = "shadow"
SCHOOL_LIFE = "life"
SCHOOL_DEATH = "death"
SCHOOL_HEAVENS = "heavens"
SCHOOL_BEASTS = "beasts"
SCHOOL_METAL = "metal"

ALL_SCHOOLS = (
    SCHOOL_FIRE, SCHOOL_ICE, SCHOOL_SHADOW, SCHOOL_LIFE,
    SCHOOL_DEATH, SCHOOL_HEAVENS, SCHOOL_BEASTS, SCHOOL_METAL,
)

# ── Spell Definitions ───────────────────────────────────────────────────
# Full spell list with balanced values will be added in Batch 11.
# These are placeholder definitions establishing the data structure.

# Fire School
FIREBALL = Spell("Fireball", SCHOOL_FIRE, mana_cost=30, cooldown_seconds=15,
                 cast_time_seconds=1.5, aoe_radius=60, damage=80,
                 damage_type="fire", description="AOE fire damage, medium radius.",
                 effect_type="damage", targeting="area")

FLAME_WALL = Spell("Flame Wall", SCHOOL_FIRE, mana_cost=20, cooldown_seconds=20,
                   cast_time_seconds=1.0, damage=30, damage_type="fire",
                   duration_seconds=10,
                   description="Line of fire that damages units crossing it.",
                   effect_type="terrain")

INFERNO = Spell("Inferno", SCHOOL_FIRE, mana_cost=50, cooldown_seconds=45,
                cast_time_seconds=3.0, aoe_radius=100, damage=150,
                damage_type="fire",
                description="Large AOE, massive damage, long cast time.",
                effect_type="damage", targeting="area")

BLAZING_SWORD = Spell("Blazing Sword", SCHOOL_FIRE, mana_cost=15, cooldown_seconds=25,
                      cast_time_seconds=0.5, duration_seconds=15,
                      description="Target squad deals fire damage for 15s.",
                      effect_type="buff", targeting="self")

# Ice School
FROST_BOLT = Spell("Frost Bolt", SCHOOL_ICE, mana_cost=20, cooldown_seconds=12,
                   cast_time_seconds=1.0, damage=50, damage_type="ice",
                   description="Single target damage + slow.",
                   effect_type="damage")

BLIZZARD = Spell("Blizzard", SCHOOL_ICE, mana_cost=40, cooldown_seconds=30,
                 cast_time_seconds=2.0, aoe_radius=80, damage=60,
                 damage_type="ice", duration_seconds=8,
                 description="AOE ice damage + movement speed debuff.",
                 effect_type="damage", targeting="area")

ICE_WALL = Spell("Ice Wall", SCHOOL_ICE, mana_cost=25, cooldown_seconds=25,
                 cast_time_seconds=1.0, duration_seconds=20,
                 description="Create impassable ice barrier for 20s.",
                 effect_type="terrain")

FREEZE = Spell("Freeze", SCHOOL_ICE, mana_cost=30, cooldown_seconds=20,
               cast_time_seconds=1.5, duration_seconds=5,
               description="Immobilize target squad for 5s.",
               effect_type="debuff")

# Shadow School
SHADOW_BOLT = Spell("Shadow Bolt", SCHOOL_SHADOW, mana_cost=15, cooldown_seconds=10,
                    cast_time_seconds=0.5, damage=40, damage_type="magical",
                    description="Fast single target magic damage.",
                    effect_type="damage")

DREAD = Spell("Dread", SCHOOL_SHADOW, mana_cost=25, cooldown_seconds=20,
              cast_time_seconds=1.0, aoe_radius=70,
              description="AOE morale penalty.",
              effect_type="debuff")

CLOAK_OF_SHADOWS = Spell("Cloak of Shadows", SCHOOL_SHADOW, mana_cost=20,
                         cooldown_seconds=25, cast_time_seconds=1.0,
                         duration_seconds=15,
                         description="Target squad becomes stealthy for 15s.",
                         effect_type="buff", targeting="self")

SOUL_DRAIN = Spell("Soul Drain", SCHOOL_SHADOW, mana_cost=35, cooldown_seconds=25,
                   cast_time_seconds=1.5, damage=60, damage_type="magical",
                   description="Damage enemy, heal caster.",
                   effect_type="damage")

# Life School
HEALING_LIGHT = Spell("Healing Light", SCHOOL_LIFE, mana_cost=20, cooldown_seconds=15,
                      cast_time_seconds=1.0, heal=40,
                      description="Restore HP to target squad.",
                      effect_type="buff", targeting="self")

SHIELD_OF_THORNS = Spell("Shield of Thorns", SCHOOL_LIFE, mana_cost=25,
                         cooldown_seconds=20, cast_time_seconds=1.0,
                         duration_seconds=15,
                         description="Reflect damage on target squad.",
                         effect_type="buff", targeting="self")

REGROWTH = Spell("Regrowth", SCHOOL_LIFE, mana_cost=30, cooldown_seconds=25,
                 cast_time_seconds=1.5, aoe_radius=80, duration_seconds=10, heal=30,
                 description="Heal over time on large area.",
                 effect_type="buff", targeting="self")

BANISHMENT = Spell("Banishment", SCHOOL_LIFE, mana_cost=40, cooldown_seconds=35,
                   cast_time_seconds=2.0, damage=120, damage_type="holy",
                   description="Massive damage vs undead/demons only.",
                   effect_type="damage", targeting="area")

# Death School
RAISE_DEAD = Spell("Raise Dead", SCHOOL_DEATH, mana_cost=25, cooldown_seconds=30,
                   cast_time_seconds=2.0,
                   description="Summon skeleton squad from corpses.",
                   effect_type="summon")

SPIRIT_LEECH = Spell("Spirit Leech", SCHOOL_DEATH, mana_cost=20, cooldown_seconds=15,
                     cast_time_seconds=1.0, damage=50, damage_type="magical",
                     description="Single target damage, ignores armor.",
                     effect_type="damage")

CURSE_OF_YEARS = Spell("Curse of Years", SCHOOL_DEATH, mana_cost=35,
                       cooldown_seconds=30, cast_time_seconds=1.5,
                       duration_seconds=15, damage_type="magical",
                       description="DOT that accelerates over time.",
                       effect_type="debuff")

WIND_OF_DEATH = Spell("Wind of Death", SCHOOL_DEATH, mana_cost=60,
                      cooldown_seconds=60, cast_time_seconds=2.5,
                      damage=200, damage_type="magical", aoe_radius=40,
                      description="Line AOE, devastating magic damage.",
                      effect_type="damage", targeting="area")

# Heavens School
LIGHTNING_BOLT = Spell("Lightning Bolt", SCHOOL_HEAVENS, mana_cost=25,
                       cooldown_seconds=12, cast_time_seconds=0.8,
                       damage=60, damage_type="magical",
                       description="Fast single target, armor-piercing.",
                       effect_type="damage")

CHAIN_LIGHTNING = Spell("Chain Lightning", SCHOOL_HEAVENS, mana_cost=40,
                        cooldown_seconds=25, cast_time_seconds=1.5,
                        damage=40, damage_type="magical",
                        description="Bounces between nearby enemies.",
                        effect_type="damage")

COMET = Spell("Comet", SCHOOL_HEAVENS, mana_cost=55, cooldown_seconds=45,
              cast_time_seconds=2.0, aoe_radius=70, damage=180,
              damage_type="magical",
              description="Delayed massive AOE (2s delay, huge damage).",
              effect_type="damage", targeting="area")

WIND_BLAST = Spell("Wind Blast", SCHOOL_HEAVENS, mana_cost=15, cooldown_seconds=15,
                   cast_time_seconds=0.5, aoe_radius=50,
                   description="Push back and scatter a formation.",
                   effect_type="debuff")

# Beasts School
SUMMON_WOLVES = Spell("Summon Wolves", SCHOOL_BEASTS, mana_cost=20,
                      cooldown_seconds=30, cast_time_seconds=2.0,
                      description="Temporary wolf pack (fast, flankers).",
                      effect_type="summon")

WILD_FURY = Spell("Wild Fury", SCHOOL_BEASTS, mana_cost=25, cooldown_seconds=25,
                  cast_time_seconds=1.0, duration_seconds=15,
                  description="Target squad gains frenzy.",
                  effect_type="buff", targeting="self")

AMBER_SPEAR = Spell("Amber Spear", SCHOOL_BEASTS, mana_cost=30, cooldown_seconds=18,
                    cast_time_seconds=1.0, damage=80, damage_type="magical",
                    description="Magic projectile, anti_large.",
                    effect_type="damage")

SUMMON_MANTICORE = Spell("Summon Manticore", SCHOOL_BEASTS, mana_cost=50,
                         cooldown_seconds=60, cast_time_seconds=3.0,
                         description="Temporary massive flying unit.",
                         effect_type="summon")

# Metal School (Rune variant for Dwarves)
ENCHANT_ARMOR = Spell("Enchant Armor", SCHOOL_METAL, mana_cost=20, cooldown_seconds=20,
                      cast_time_seconds=1.0, duration_seconds=20,
                      description="+30% armor for target squad.",
                      effect_type="buff", targeting="self")

SEARING_DOOM = Spell("Searing Doom", SCHOOL_METAL, mana_cost=30, cooldown_seconds=20,
                     cast_time_seconds=1.5, aoe_radius=60, damage=70,
                     damage_type="magical",
                     description="AOE bonus damage to armored targets.",
                     effect_type="damage", targeting="area")

TRANSMUTATION = Spell("Transmutation", SCHOOL_METAL, mana_cost=25,
                      cooldown_seconds=25, cast_time_seconds=1.0,
                      duration_seconds=15,
                      description="Reduce enemy armor by 50% for 15s.",
                      effect_type="debuff", targeting="unit")

RUNE_OF_WRATH = Spell("Rune of Wrath", SCHOOL_METAL, mana_cost=40,
                      cooldown_seconds=30, cast_time_seconds=1.5,
                      damage=100, damage_type="magical",
                      description="Place rune on ground, explodes when enemies cross.",
                      effect_type="terrain")

# ── Spell Registry ──────────────────────────────────────────────────────

ALL_SPELLS = {s.name: s for s in [
    FIREBALL, FLAME_WALL, INFERNO, BLAZING_SWORD,
    FROST_BOLT, BLIZZARD, ICE_WALL, FREEZE,
    SHADOW_BOLT, DREAD, CLOAK_OF_SHADOWS, SOUL_DRAIN,
    HEALING_LIGHT, SHIELD_OF_THORNS, REGROWTH, BANISHMENT,
    RAISE_DEAD, SPIRIT_LEECH, CURSE_OF_YEARS, WIND_OF_DEATH,
    LIGHTNING_BOLT, CHAIN_LIGHTNING, COMET, WIND_BLAST,
    SUMMON_WOLVES, WILD_FURY, AMBER_SPEAR, SUMMON_MANTICORE,
    ENCHANT_ARMOR, SEARING_DOOM, TRANSMUTATION, RUNE_OF_WRATH,
]}

SPELLS_BY_SCHOOL = {}
for spell in ALL_SPELLS.values():
    SPELLS_BY_SCHOOL.setdefault(spell.school, []).append(spell)
