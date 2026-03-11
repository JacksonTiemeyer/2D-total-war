"""General ability system with level-locked abilities.

Each general type has a unique ability tree. One ability is available at
level 1, and more unlock as the general gains experience from kills and
duels won.

Abilities have cooldowns and are activated during battle.
"""

import math
from core.utils import distance


# ── Ability Definitions ─────────────────────────────────────────────────

class Ability:
    """Base class for an activatable ability."""

    def __init__(self, name, description, cooldown_seconds, level_required,
                 radius=150):
        self.name = name
        self.description = description
        self.cooldown_max = cooldown_seconds * 60  # frames
        self.cooldown = 0
        self.level_required = level_required
        self.radius = radius  # area of effect

    @property
    def ready(self):
        return self.cooldown <= 0

    def tick(self):
        if self.cooldown > 0:
            self.cooldown -= 1

    def activate(self, general, friendly_squads, enemy_squads):
        """Override in subclasses. Returns True if activated."""
        raise NotImplementedError

    def _squads_in_range(self, general, squads):
        return [sq for sq in squads
                if not sq.is_destroyed and
                distance(general.x, general.y, sq.x, sq.y) < self.radius]


# ── Commander Abilities ──────────────────────────────────────────────────

class RallyTheTroops(Ability):
    """Restore morale to nearby friendly squads."""

    def __init__(self):
        super().__init__(
            name="Rally the Troops",
            description="Restore 20 morale to nearby friendly units.",
            cooldown_seconds=30, level_required=1, radius=200,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        for sq in targets:
            sq.apply_morale_modifier(20)
        self.cooldown = self.cooldown_max
        return True


class SecondWind(Ability):
    """Reduce exhaustion of nearby friendly squads."""

    def __init__(self):
        super().__init__(
            name="Second Wind",
            description="Reduce exhaustion of nearby units by 30.",
            cooldown_seconds=45, level_required=2, radius=180,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        for sq in targets:
            sq.reduce_exhaustion(30)
        self.cooldown = self.cooldown_max
        return True


class HoldTheLine(Ability):
    """Prevent nearby squads from routing for 10 seconds."""

    def __init__(self):
        super().__init__(
            name="Hold the Line",
            description="Nearby units cannot rout for 10 seconds. +10 morale.",
            cooldown_seconds=60, level_required=3, radius=200,
        )
        self.duration = 10 * 60  # frames
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        self.affected_squads = targets
        self.active_timer = self.duration
        for sq in targets:
            sq.apply_morale_modifier(10)
            sq._hold_the_line = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_hold_the_line'):
                        sq._hold_the_line = False
                self.affected_squads = []


class InspiringPresence(Ability):
    """Permanently boost morale recovery rate of nearby squads for the battle."""

    def __init__(self):
        super().__init__(
            name="Inspiring Presence",
            description="Nearby units gain +50% morale recovery for the battle.",
            cooldown_seconds=90, level_required=4, radius=250,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        for sq in targets:
            sq._inspired = True
        self.cooldown = self.cooldown_max
        return True


# ── Champion Abilities ──────────────────────────────────────────────────

class Bloodlust(Ability):
    """Boost own attack power temporarily after a kill."""

    def __init__(self):
        super().__init__(
            name="Bloodlust",
            description="Gain +50% attack for 8 seconds.",
            cooldown_seconds=25, level_required=1, radius=0,
        )
        self.duration = 8 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._bloodlust_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1


class Intimidate(Ability):
    """Reduce morale of nearby enemy squads."""

    def __init__(self):
        super().__init__(
            name="Intimidate",
            description="Nearby enemies lose 15 morale.",
            cooldown_seconds=35, level_required=2, radius=180,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, enemy_squads)
        if not targets:
            return False
        for sq in targets:
            sq.apply_morale_modifier(-15)
        self.cooldown = self.cooldown_max
        return True


class DuelChallenge(Ability):
    """Force the nearest enemy general into a duel (cannot refuse)."""

    def __init__(self):
        super().__init__(
            name="Challenge!",
            description="Force nearest enemy general into a duel.",
            cooldown_seconds=60, level_required=3, radius=300,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        from battle.general import DuelState
        if general.duel_state != DuelState.NONE:
            return False
        # Find nearest enemy general
        best = None
        best_dist = self.radius
        for g in getattr(general, '_all_enemy_generals', []):
            if not g.alive or g.duel_state != DuelState.NONE:
                continue
            d = distance(general.x, general.y, g.x, g.y)
            if d < best_dist:
                best_dist = d
                best = g
        if not best:
            return False
        general.challenge_duel(best)
        self.cooldown = self.cooldown_max
        return True


class Rampage(Ability):
    """Deal damage to all enemy soldiers within a small radius."""

    def __init__(self):
        super().__init__(
            name="Rampage",
            description="Deal heavy damage to all enemies in a small area.",
            cooldown_seconds=50, level_required=4, radius=80,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        hit_any = False
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(general.x, general.y, s.x, s.y)
                if d < self.radius:
                    dmg = general.melee_attack * 1.5
                    s.take_damage(dmg, general.unit_stats.armor_penetration)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


# ── Strategist Abilities ────────────────────────────────────────────────

class PrecisionVolley(Ability):
    """Boost ranged accuracy and damage of nearby ranged squads."""

    def __init__(self):
        super().__init__(
            name="Precision Volley",
            description="Nearby ranged units get +30% damage for 10 seconds.",
            cooldown_seconds=30, level_required=1, radius=200,
        )
        self.duration = 10 * 60
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = [sq for sq in self._squads_in_range(general, friendly_squads)
                    if sq.is_ranged]
        if not targets:
            return False
        self.affected_squads = targets
        self.active_timer = self.duration
        for sq in targets:
            sq._precision_volley = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_precision_volley'):
                        sq._precision_volley = False
                self.affected_squads = []


class WeakenResolve(Ability):
    """Reduce morale of a targeted enemy squad significantly."""

    def __init__(self):
        super().__init__(
            name="Weaken Resolve",
            description="Target enemy squad loses 25 morale.",
            cooldown_seconds=40, level_required=2, radius=250,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        # Target nearest enemy
        targets = self._squads_in_range(general, enemy_squads)
        if not targets:
            return False
        target = min(targets,
                     key=lambda sq: distance(general.x, general.y, sq.x, sq.y))
        target.apply_morale_modifier(-25)
        self.cooldown = self.cooldown_max
        return True


class SappingFire(Ability):
    """Nearby ranged attacks increase enemy exhaustion."""

    def __init__(self):
        super().__init__(
            name="Sapping Fire",
            description="Ranged attacks exhaust enemies for 15 seconds.",
            cooldown_seconds=50, level_required=3, radius=200,
        )
        self.duration = 15 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._sapping_fire = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General's update will check the timer


class ScoutReport(Ability):
    """Reveal enemy squad stats and exact morale/exhaustion values."""

    def __init__(self):
        super().__init__(
            name="Scout Report",
            description="Reveal all enemy unit details for 20 seconds.",
            cooldown_seconds=45, level_required=4, radius=0,
        )
        self.duration = 20 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._scout_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General's update will check


# ── Ability Trees ────────────────────────────────────────────────────────

def get_commander_abilities():
    return [RallyTheTroops(), SecondWind(), HoldTheLine(), InspiringPresence()]


def get_champion_abilities():
    return [Bloodlust(), Intimidate(), DuelChallenge(), Rampage()]


def get_strategist_abilities():
    return [PrecisionVolley(), WeakenResolve(), SappingFire(), ScoutReport()]


def get_abilities_for_type(general_type):
    if general_type == "Commander":
        return get_commander_abilities()
    elif general_type == "Champion":
        return get_champion_abilities()
    elif general_type == "Strategist":
        return get_strategist_abilities()
    return []


# ── Leveling ─────────────────────────────────────────────────────────────

LEVEL_THRESHOLDS = [0, 3, 8, 15]  # XP needed for levels 1-4

def xp_for_level(level):
    """Return XP threshold for a given level (1-indexed)."""
    if level <= 0:
        return 0
    if level > len(LEVEL_THRESHOLDS):
        return LEVEL_THRESHOLDS[-1] + (level - len(LEVEL_THRESHOLDS)) * 10
    return LEVEL_THRESHOLDS[level - 1]


def level_from_xp(xp):
    """Return current level based on XP."""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
    return level
