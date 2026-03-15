"""Trait system — unit tags that enable special combat rules.

Traits are string tags stored as a tuple on UnitStats. Combat code checks
for trait presence to apply special mechanics (damage bonuses, immunities,
movement modes, etc.).

This module defines the canonical trait names, their descriptions, and
helper functions for computing trait-based combat interactions.
"""

# ── Movement Traits ──────────────────────────────────────────────────────

TRAIT_FLYING = "flying"
"""Ignores terrain penalties, can move over obstacles. Vulnerable to ranged."""

TRAIT_BURROWING = "burrowing"
"""Can tunnel under walls in siege. Ambush from underground."""

TRAIT_AQUATIC = "aquatic"
"""Can cross water terrain. Bonus fighting near water."""

TRAIT_MOUNTED = "mounted"
"""Cavalry-class movement and charge bonuses."""

# ── Durability Traits ────────────────────────────────────────────────────

TRAIT_UNDEAD = "undead"
"""Immune to morale (never routs). Immune to fear/terror. Weak to holy."""

TRAIT_REGENERATING = "regenerating"
"""Recovers HP slowly during battle (~1% max HP per second)."""

TRAIT_ETHEREAL = "ethereal"
"""50% physical damage reduction. Vulnerable to magical damage."""

TRAIT_ARMORED_CONSTRUCT = "armored_construct"
"""Immune to morale, poison, and exhaustion. (Golems, mechs, war machines.)"""

TRAIT_LARGE = "large"
"""Takes bonus damage from anti_large weapons. Harder to flank."""

TRAIT_MASSIVE = "massive"
"""Single-entity unit. Area attacks. Inherent terror aura."""

# ── Offensive Traits ─────────────────────────────────────────────────────

TRAIT_FIRE_ATTACK = "fire_attack"
"""Deals fire damage type. Bonus vs regenerating/undead."""

TRAIT_POISON_ATTACK = "poison_attack"
"""Applies damage-over-time on hit. No effect on undead/constructs."""

TRAIT_ANTI_LARGE = "anti_large"
"""Bonus damage vs large and massive units."""

TRAIT_ANTI_INFANTRY = "anti_infantry"
"""Bonus damage vs normal and small units."""

TRAIT_FEAR = "fear"
"""Causes morale penalty to nearby enemy units."""

TRAIT_TERROR = "terror"
"""Stronger fear effect. Causes morale shock on charge."""

TRAIT_FRENZY = "frenzy"
"""Attack speed increases as health drops."""

# ── Special Traits ───────────────────────────────────────────────────────

TRAIT_SPELLCASTER = "spellcaster"
"""Can cast spells from a spell list."""

TRAIT_SUMMONER = "summoner"
"""Can summon temporary units on the battlefield."""

TRAIT_UNBREAKABLE = "unbreakable"
"""Cannot rout or break (but can still die)."""

TRAIT_STEALTHY = "stealthy"
"""Hidden until attacking or entering close range."""

TRAIT_FIRE_WHILE_MOVING = "fire_while_moving"
"""Can shoot ranged weapons while moving (horse archers, etc.)."""

TRAIT_CAN_BRACE = "can_brace"
"""Can brace against charges when stationary (spearmen, halberdiers)."""

# ── All trait names for validation ───────────────────────────────────────

ALL_TRAITS = frozenset({
    TRAIT_FLYING, TRAIT_BURROWING, TRAIT_AQUATIC, TRAIT_MOUNTED,
    TRAIT_UNDEAD, TRAIT_REGENERATING, TRAIT_ETHEREAL, TRAIT_ARMORED_CONSTRUCT,
    TRAIT_LARGE, TRAIT_MASSIVE,
    TRAIT_FIRE_ATTACK, TRAIT_POISON_ATTACK,
    TRAIT_ANTI_LARGE, TRAIT_ANTI_INFANTRY,
    TRAIT_FEAR, TRAIT_TERROR, TRAIT_FRENZY,
    TRAIT_SPELLCASTER, TRAIT_SUMMONER, TRAIT_UNBREAKABLE, TRAIT_STEALTHY,
    TRAIT_FIRE_WHILE_MOVING, TRAIT_CAN_BRACE,
})

# ── Damage Types ─────────────────────────────────────────────────────────

DMG_PHYSICAL = "physical"
DMG_MAGICAL = "magical"
DMG_FIRE = "fire"
DMG_HOLY = "holy"
DMG_POISON = "poison"
DMG_ICE = "ice"

ALL_DAMAGE_TYPES = frozenset({
    DMG_PHYSICAL, DMG_MAGICAL, DMG_FIRE, DMG_HOLY, DMG_POISON, DMG_ICE,
})

# ── Size Categories ──────────────────────────────────────────────────────

SIZE_SMALL = "small"
SIZE_NORMAL = "normal"
SIZE_LARGE = "large"
SIZE_MASSIVE = "massive"

ALL_SIZES = frozenset({SIZE_SMALL, SIZE_NORMAL, SIZE_LARGE, SIZE_MASSIVE})

# ── Combat Interaction Constants ─────────────────────────────────────────

# Damage type multipliers: (attacker_damage_type, defender_vulnerability) -> mult
DAMAGE_TYPE_BONUS = 1.5       # Bonus damage when attacking a vulnerability
DAMAGE_TYPE_IMMUNITY_MULT = 0.0  # Multiplier when target is immune
DAMAGE_TYPE_RESIST_MULT = 0.5   # Multiplier when target resists (not immune)

# Trait-based combat modifiers
ANTI_LARGE_BONUS = 1.5       # Damage mult for anti_large vs large/massive
ANTI_INFANTRY_BONUS = 1.3    # Damage mult for anti_infantry vs normal/small
ETHEREAL_PHYS_REDUCTION = 0.5  # Physical damage mult against ethereal units
FRENZY_MAX_SPEED_BONUS = 0.5   # Max attack speed increase at low HP
FEAR_MORALE_PENALTY = 3.0    # Morale lost per frame by units near fear source
TERROR_MORALE_PENALTY = 6.0  # Morale lost per frame by units near terror source
TERROR_CHARGE_SHOCK = 15.0   # One-time morale hit when terror unit charges
REGENERATION_RATE = 0.01     # % of max HP per second
POISON_DOT_DAMAGE = 2.0      # Damage per second from poison
POISON_DOT_DURATION = 180    # Frames (3 seconds at 60 FPS)
STEALTH_REVEAL_RANGE = 80    # World units — closer than this reveals stealthy units
FLYING_RANGED_VULN = 1.3     # Ranged damage multiplier against flying units

# Size interaction modifiers
SMALL_EVASION_BONUS = 0.15   # 15% chance to evade attacks
SMALL_DAMAGE_PENALTY = 0.85  # 85% damage output
MASSIVE_AREA_ATTACK_RADIUS = 40  # World units — massive units hit in an area


def has_trait(unit_stats, trait):
    """Check if a UnitStats has a specific trait."""
    return trait in getattr(unit_stats, 'traits', ())


def get_damage_type(unit_stats):
    """Get the primary damage type for a unit."""
    return getattr(unit_stats, 'damage_type', DMG_PHYSICAL)


def get_size(unit_stats):
    """Get the size category for a unit."""
    return getattr(unit_stats, 'size_category', SIZE_NORMAL)


def compute_damage_type_multiplier(damage_type, defender_stats):
    """Compute damage multiplier based on attacker's damage type vs defender."""
    # Check immunities
    immunities = getattr(defender_stats, 'damage_immunities', ())
    if damage_type in immunities:
        return DAMAGE_TYPE_IMMUNITY_MULT

    # Check vulnerabilities
    vulnerabilities = getattr(defender_stats, 'damage_vulnerabilities', ())
    if damage_type in vulnerabilities:
        return DAMAGE_TYPE_BONUS

    # Magic resistance reduces magical/elemental damage
    if damage_type != DMG_PHYSICAL:
        magic_resist = getattr(defender_stats, 'magic_resistance', 0)
        if magic_resist > 0:
            return 1.0 - (magic_resist / 200.0)  # 100 MR = 50% reduction

    return 1.0


def compute_trait_damage_multiplier(attacker_stats, defender_stats):
    """Compute damage multiplier based on attacker/defender traits and sizes."""
    mult = 1.0
    attacker_traits = getattr(attacker_stats, 'traits', ())
    defender_traits = getattr(defender_stats, 'traits', ())
    defender_size = get_size(defender_stats)

    # Anti-large vs large/massive
    if TRAIT_ANTI_LARGE in attacker_traits and defender_size in (SIZE_LARGE, SIZE_MASSIVE):
        mult *= ANTI_LARGE_BONUS

    # Anti-infantry vs normal/small
    if TRAIT_ANTI_INFANTRY in attacker_traits and defender_size in (SIZE_NORMAL, SIZE_SMALL):
        mult *= ANTI_INFANTRY_BONUS

    # Ethereal: physical damage halved
    if TRAIT_ETHEREAL in defender_traits:
        attacker_dmg_type = get_damage_type(attacker_stats)
        if attacker_dmg_type == DMG_PHYSICAL:
            mult *= ETHEREAL_PHYS_REDUCTION

    # Small units deal less damage
    attacker_size = get_size(attacker_stats)
    if attacker_size == SIZE_SMALL:
        mult *= SMALL_DAMAGE_PENALTY

    return mult


def compute_frenzy_speed_bonus(current_hp, max_hp):
    """Compute attack speed multiplier for frenzy trait based on HP ratio."""
    hp_ratio = current_hp / max(1, max_hp)
    # Linearly increases as HP drops: 0% at full HP, FRENZY_MAX_SPEED_BONUS at 0 HP
    return 1.0 + FRENZY_MAX_SPEED_BONUS * (1.0 - hp_ratio)


def should_evade(defender_stats):
    """Check if a small unit evades an attack (random roll)."""
    import random
    if get_size(defender_stats) == SIZE_SMALL:
        return random.random() < SMALL_EVASION_BONUS
    return False


def get_fear_morale_penalty(traits):
    """Get per-frame morale penalty for units near this entity."""
    if TRAIT_TERROR in traits:
        return TERROR_MORALE_PENALTY
    if TRAIT_FEAR in traits:
        return FEAR_MORALE_PENALTY
    return 0.0


def is_immune_to_morale(traits):
    """Check if unit is immune to morale effects."""
    return (TRAIT_UNDEAD in traits or
            TRAIT_ARMORED_CONSTRUCT in traits or
            TRAIT_UNBREAKABLE in traits)


def is_immune_to_poison(traits):
    """Check if unit is immune to poison damage."""
    return (TRAIT_UNDEAD in traits or
            TRAIT_ARMORED_CONSTRUCT in traits)


def is_immune_to_exhaustion(traits):
    """Check if unit is immune to exhaustion."""
    return TRAIT_ARMORED_CONSTRUCT in traits
