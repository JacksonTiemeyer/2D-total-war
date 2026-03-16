"""General ability system with level-locked abilities.

Each general type has a unique ability tree. One ability is available at
level 1, and more unlock as the general gains experience from kills and
duels won.

Abilities have cooldowns and are activated during battle.
"""

import math
import random
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


# ── Warlord Abilities ──────────────────────────────────────────────────

class WarlordRally(Ability):
    """Restore morale to nearby friendly squads."""

    def __init__(self):
        super().__init__(
            name="Rally",
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


class ForcedMarch(Ability):
    """Boost army movement speed for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Forced March",
            description="All nearby squads gain +30% speed for 15 seconds.",
            cooldown_seconds=45, level_required=5, radius=250,
        )
        self.duration = 15 * 60
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        general._forced_march = True
        self.affected_squads = targets
        self.active_timer = self.duration
        for sq in targets:
            sq._forced_march = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_forced_march'):
                        sq._forced_march = False
                self.affected_squads = []


class WarlordSecondWind(Ability):
    """Remove exhaustion from nearby squads."""

    def __init__(self):
        super().__init__(
            name="Second Wind",
            description="Remove exhaustion from nearby friendly units.",
            cooldown_seconds=50, level_required=10, radius=200,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        for sq in targets:
            sq.reduce_exhaustion(100)
        self.cooldown = self.cooldown_max
        return True


class WarlordHoldTheLine(Ability):
    """Prevent routing for 10 seconds."""

    def __init__(self):
        super().__init__(
            name="Hold the Line",
            description="Nearby units cannot rout for 10 seconds.",
            cooldown_seconds=60, level_required=15, radius=200,
        )
        self.duration = 10 * 60
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


class InspiringCharge(Ability):
    """All squads get +50% charge bonus for 8 seconds."""

    def __init__(self):
        super().__init__(
            name="Inspiring Charge",
            description="All friendly squads gain +50% charge bonus for 8 seconds.",
            cooldown_seconds=55, level_required=20, radius=300,
        )
        self.duration = 8 * 60
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
            sq._inspiring_charge = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_inspiring_charge'):
                        sq._inspiring_charge = False
                self.affected_squads = []


class WarCry(Ability):
    """Boost friendly morale and reduce enemy morale."""

    def __init__(self):
        super().__init__(
            name="War Cry",
            description="+25 morale to friendlies, -15 morale to enemies in radius.",
            cooldown_seconds=40, level_required=25, radius=250,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        friendly_targets = self._squads_in_range(general, friendly_squads)
        enemy_targets = self._squads_in_range(general, enemy_squads)
        if not friendly_targets and not enemy_targets:
            return False
        for sq in friendly_targets:
            sq.apply_morale_modifier(25)
        for sq in enemy_targets:
            sq.apply_morale_modifier(-15)
        self.cooldown = self.cooldown_max
        return True


class IronDiscipline(Ability):
    """Squads immune to flanking morale penalty for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Iron Discipline",
            description="Squads immune to flanking morale penalty for 15 seconds.",
            cooldown_seconds=60, level_required=30, radius=250,
        )
        self.duration = 15 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._iron_discipline_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class DetachmentCommand(Ability):
    """Passive: +2 squad capacity."""

    def __init__(self):
        super().__init__(
            name="Detachment Command",
            description="Passive: +2 squad capacity for your army.",
            cooldown_seconds=9999, level_required=35, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._detachment_command = True
        self.cooldown = self.cooldown_max
        return True


class LegendaryCommander(Ability):
    """Passive: all squads get +15% stats."""

    def __init__(self):
        super().__init__(
            name="Legendary Commander",
            description="Passive: all friendly squads gain +15% to all stats.",
            cooldown_seconds=9999, level_required=40, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._legendary_commander = True
        self.cooldown = self.cooldown_max
        return True


class OverlordsDecree(Ability):
    """Passive: army size +5, upkeep -20%."""

    def __init__(self):
        super().__init__(
            name="Overlord's Decree",
            description="Passive: army size +5, upkeep -20%.",
            cooldown_seconds=9999, level_required=45, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._overlords_decree = True
        self.cooldown = self.cooldown_max
        return True


# ── Battlemage Abilities ──────────────────────────────────────────────

class ArcaneBolt(Ability):
    """Single-target magic damage to nearest enemy soldier."""

    def __init__(self):
        super().__init__(
            name="Arcane Bolt",
            description="Deal magic damage to the nearest enemy soldier.",
            cooldown_seconds=12, level_required=1, radius=200,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        best_soldier = None
        best_dist = self.radius
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(general.x, general.y, s.x, s.y)
                if d < best_dist:
                    best_dist = d
                    best_soldier = s
                    best_squad = sq
        if not best_soldier:
            return False
        dmg = general.melee_attack * 2.5
        best_soldier.take_damage(dmg, 80)
        if not best_soldier.alive:
            general.kills += 1
            best_squad.on_casualty()
        self.cooldown = self.cooldown_max
        return True


class ManaShield(Ability):
    """Temporary damage reduction on general for 10 seconds."""

    def __init__(self):
        super().__init__(
            name="Mana Shield",
            description="General takes 50% less damage for 10 seconds.",
            cooldown_seconds=35, level_required=5, radius=0,
        )
        self.duration = 10 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._mana_shield_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class ElementalBlast(Ability):
    """AOE magic damage in a medium radius."""

    def __init__(self):
        super().__init__(
            name="Elemental Blast",
            description="Deal magic damage to all enemies in a medium area.",
            cooldown_seconds=25, level_required=10, radius=120,
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
                    dmg = general.melee_attack * 1.8
                    s.take_damage(dmg, 70)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class EnchantWeapons(Ability):
    """Nearby squads deal bonus damage for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Enchant Weapons",
            description="Nearby squads deal +30% bonus damage for 15 seconds.",
            cooldown_seconds=45, level_required=15, radius=200,
        )
        self.duration = 15 * 60
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        general._enchant_weapons_active = True
        self.affected_squads = targets
        self.active_timer = self.duration
        for sq in targets:
            sq._enchanted_weapons = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_enchanted_weapons'):
                        sq._enchanted_weapons = False
                self.affected_squads = []


class SummonElemental(Ability):
    """Placeholder: deal damage in area (summon system TBD)."""

    def __init__(self):
        super().__init__(
            name="Summon Elemental",
            description="Summon an elemental that damages nearby enemies.",
            cooldown_seconds=50, level_required=20, radius=100,
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
                    dmg = general.melee_attack * 2.0
                    s.take_damage(dmg, 60)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class ChainLightning(Ability):
    """Hit up to 5 enemies in chain, decreasing damage."""

    def __init__(self):
        super().__init__(
            name="Chain Lightning",
            description="Lightning arcs through up to 5 enemies with decreasing damage.",
            cooldown_seconds=35, level_required=25, radius=250,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        # Gather all enemy soldiers in range
        candidates = []
        soldier_to_squad = {}
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(general.x, general.y, s.x, s.y)
                if d < self.radius:
                    candidates.append((d, s))
                    soldier_to_squad[id(s)] = sq
        if not candidates:
            return False
        candidates.sort(key=lambda x: x[0])
        hit_count = 0
        base_dmg = general.melee_attack * 3.0
        hit_soldiers = []
        # Start from nearest, chain up to 5
        for _, s in candidates:
            if hit_count >= 5:
                break
            if not s.alive:
                continue
            # Chain damage decreases by 20% per bounce
            dmg = base_dmg * (0.8 ** hit_count)
            s.take_damage(dmg, 90)
            hit_soldiers.append(s)
            hit_count += 1
            if not s.alive:
                general.kills += 1
                sq = soldier_to_squad.get(id(s))
                if sq:
                    sq.on_casualty()
        if hit_count > 0:
            self.cooldown = self.cooldown_max
            return True
        return False


class ArcaneStorm(Ability):
    """Massive AOE magic damage."""

    def __init__(self):
        super().__init__(
            name="Arcane Storm",
            description="Unleash a massive arcane storm damaging all nearby enemies.",
            cooldown_seconds=60, level_required=30, radius=180,
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
                    dmg = general.melee_attack * 2.5
                    s.take_damage(dmg, 80)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class MassTeleport(Ability):
    """Relocate nearest friendly squad to general's position."""

    def __init__(self):
        super().__init__(
            name="Mass Teleport",
            description="Teleport the nearest friendly squad to the general's position.",
            cooldown_seconds=70, level_required=35, radius=400,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            # Try all friendly squads regardless of range
            targets = [sq for sq in friendly_squads if not sq.is_destroyed]
        if not targets:
            return False
        target = min(targets,
                     key=lambda sq: distance(general.x, general.y, sq.x, sq.y))
        # Move squad to general position
        offset_x = random.uniform(-40, 40)
        offset_y = random.uniform(-40, 40)
        dx = general.x + offset_x - target.x
        dy = general.y + offset_y - target.y
        target.x += dx
        target.y += dy
        for s in target.alive_soldiers:
            s.x += dx
            s.y += dy
        self.cooldown = self.cooldown_max
        return True


class MageLord(Ability):
    """Passive: cooldown reduction 25%."""

    def __init__(self):
        super().__init__(
            name="Mage Lord",
            description="Passive: all ability cooldowns reduced by 25%.",
            cooldown_seconds=9999, level_required=40, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._cooldown_reduction = 25
        self.cooldown = self.cooldown_max
        return True


class Cataclysm(Ability):
    """Ultimate: massive damage to all enemies in large radius."""

    def __init__(self):
        super().__init__(
            name="Cataclysm",
            description="Ultimate: massive magic damage to all enemies in a huge area.",
            cooldown_seconds=90, level_required=45, radius=300,
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
                    dmg = general.melee_attack * 4.0
                    s.take_damage(dmg, 100)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


# ── Champion (Player Class) Abilities ─────────────────────────────────

class ChampionBloodlust(Ability):
    """Boost own attack power for 8 seconds."""

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


class ChampionIntimidate(Ability):
    """Reduce morale of nearby enemy squads."""

    def __init__(self):
        super().__init__(
            name="Intimidate",
            description="Nearby enemies lose 15 morale.",
            cooldown_seconds=35, level_required=5, radius=180,
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


class ChampionChallenge(Ability):
    """Force enemy general into a duel."""

    def __init__(self):
        super().__init__(
            name="Challenge",
            description="Force nearest enemy general into a duel.",
            cooldown_seconds=60, level_required=10, radius=300,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        from battle.general import DuelState
        if general.duel_state != DuelState.NONE:
            return False
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


class ChampionRampage(Ability):
    """AOE melee damage to nearby enemies."""

    def __init__(self):
        super().__init__(
            name="Rampage",
            description="Deal heavy melee damage to all enemies in a small area.",
            cooldown_seconds=45, level_required=15, radius=80,
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


class Deathblow(Ability):
    """Massive single-target damage to nearest enemy soldier."""

    def __init__(self):
        super().__init__(
            name="Deathblow",
            description="Deal massive damage to the nearest enemy soldier.",
            cooldown_seconds=30, level_required=20, radius=150,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        best_soldier = None
        best_dist = self.radius
        best_squad = None
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(general.x, general.y, s.x, s.y)
                if d < best_dist:
                    best_dist = d
                    best_soldier = s
                    best_squad = sq
        if not best_soldier:
            return False
        dmg = general.melee_attack * 5.0
        best_soldier.take_damage(dmg, 100)
        if not best_soldier.alive:
            general.kills += 1
            best_squad.on_casualty()
        self.cooldown = self.cooldown_max
        return True


class TerrifyingPresence(Ability):
    """Passive terror aura: -2 morale/sec to nearby enemies."""

    def __init__(self):
        super().__init__(
            name="Terrifying Presence",
            description="Passive: enemies near you lose morale continuously.",
            cooldown_seconds=9999, level_required=25, radius=150,
        )
        self._general = None

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        self._general = general
        general._terrifying_presence = True
        self.cooldown = self.cooldown_max
        return True


class Unstoppable(Ability):
    """Immune to slow and exhaustion for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Unstoppable",
            description="Immune to slow and exhaustion effects for 15 seconds.",
            cooldown_seconds=60, level_required=30, radius=0,
        )
        self.duration = 15 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._unstoppable_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class Slayer(Ability):
    """Anti-large bonus for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Slayer",
            description="Gain bonus damage against large units for 20 seconds.",
            cooldown_seconds=55, level_required=35, radius=0,
        )
        self.duration = 20 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._slayer_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class OneManArmy(Ability):
    """Massive stat boost for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="One-Man Army",
            description="+100% attack and defense for 15 seconds.",
            cooldown_seconds=75, level_required=40, radius=0,
        )
        self.duration = 15 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._one_man_army_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class AvatarOfWar(Ability):
    """Transform: huge size, damage, health for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Avatar of War",
            description="Transform: massive size, damage, and health for 20 seconds.",
            cooldown_seconds=90, level_required=45, radius=0,
        )
        self.duration = 20 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._avatar_active = True
        # Heal general to full and boost stats
        general.health = general.max_health
        general.melee_attack *= 2.0
        general.melee_defense *= 2.0
        self.active_timer = self.duration
        self._general = general
        self._original_attack = general.melee_attack / 2.0
        self._original_defense = general.melee_defense / 2.0
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                if hasattr(self, '_general') and self._general:
                    self._general._avatar_active = False
                    self._general.melee_attack = self._original_attack
                    self._general.melee_defense = self._original_defense


# ── Rogue Abilities ───────────────────────────────────────────────────

class Ambush(Ability):
    """Grant stealth to nearest friendly squad for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Ambush",
            description="Grant stealth to the nearest friendly squad for 15 seconds.",
            cooldown_seconds=35, level_required=1, radius=200,
        )
        self.duration = 15 * 60
        self.active_timer = 0
        self.affected_squad = None

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        target = min(targets,
                     key=lambda sq: distance(general.x, general.y, sq.x, sq.y))
        target._stealthy = True
        self.affected_squad = target
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                if self.affected_squad and hasattr(self.affected_squad, '_stealthy'):
                    self.affected_squad._stealthy = False
                self.affected_squad = None


class ScoutNetwork(Ability):
    """Reveal all enemies for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Scout Network",
            description="Reveal all enemy unit details for 20 seconds.",
            cooldown_seconds=45, level_required=5, radius=0,
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
                pass  # General update clears the flag


class PoisonedWeapons(Ability):
    """Nearby squads gain poison DOT on attacks for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Poisoned Weapons",
            description="Nearby squads apply poison on hit for 15 seconds.",
            cooldown_seconds=40, level_required=10, radius=200,
        )
        self.duration = 15 * 60
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
            sq._poisoned_weapons = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_poisoned_weapons'):
                        sq._poisoned_weapons = False
                self.affected_squads = []


class Bribe(Ability):
    """Reduce nearest enemy squad morale by 30."""

    def __init__(self):
        super().__init__(
            name="Bribe",
            description="Reduce nearest enemy squad morale by 30.",
            cooldown_seconds=40, level_required=15, radius=300,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, enemy_squads)
        if not targets:
            return False
        target = min(targets,
                     key=lambda sq: distance(general.x, general.y, sq.x, sq.y))
        target.apply_morale_modifier(-30)
        self.cooldown = self.cooldown_max
        return True


class Shadowstep(Ability):
    """Teleport general behind nearest enemy general."""

    def __init__(self):
        super().__init__(
            name="Shadowstep",
            description="Teleport behind the nearest enemy general.",
            cooldown_seconds=45, level_required=20, radius=400,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        best = None
        best_dist = self.radius
        for g in getattr(general, '_all_enemy_generals', []):
            if not g.alive:
                continue
            d = distance(general.x, general.y, g.x, g.y)
            if d < best_dist:
                best_dist = d
                best = g
        if not best:
            return False
        # Teleport behind the enemy general (offset by 30 units)
        angle = math.atan2(general.y - best.y, general.x - best.x)
        general.x = best.x - math.cos(angle) * 30
        general.y = best.y - math.sin(angle) * 30
        self.cooldown = self.cooldown_max
        return True


class Sabotage(Ability):
    """Reduce all enemy squad max speed by 20% for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Sabotage",
            description="Reduce all enemy squad speed by 20% for 20 seconds.",
            cooldown_seconds=55, level_required=25, radius=0,
        )
        self.duration = 20 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._sabotage_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class InciteRebellion(Ability):
    """Cause nearest enemy squad to stop fighting for 10 seconds."""

    def __init__(self):
        super().__init__(
            name="Incite Rebellion",
            description="Nearest enemy squad stops fighting for 10 seconds.",
            cooldown_seconds=65, level_required=30, radius=250,
        )
        self.duration = 10 * 60
        self.active_timer = 0
        self.affected_squad = None

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, enemy_squads)
        if not targets:
            return False
        target = min(targets,
                     key=lambda sq: distance(general.x, general.y, sq.x, sq.y))
        target._rebellion = True
        self.affected_squad = target
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                if self.affected_squad and hasattr(self.affected_squad, '_rebellion'):
                    self.affected_squad._rebellion = False
                self.affected_squad = None


class Assassinate(Ability):
    """Deal massive damage to nearest enemy general."""

    def __init__(self):
        super().__init__(
            name="Assassinate",
            description="Deal massive damage to the nearest enemy general.",
            cooldown_seconds=75, level_required=35, radius=300,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        best = None
        best_dist = self.radius
        for g in getattr(general, '_all_enemy_generals', []):
            if not g.alive:
                continue
            d = distance(general.x, general.y, g.x, g.y)
            if d < best_dist:
                best_dist = d
                best = g
        if not best:
            return False
        dmg = general.melee_attack * 6.0
        best.take_damage(dmg)
        if not best.alive:
            general.kills += 1
        self.cooldown = self.cooldown_max
        return True


class MasterOfCoin(Ability):
    """Passive: campaign economy effect (flag only in battle)."""

    def __init__(self):
        super().__init__(
            name="Master of Coin",
            description="Passive: increased income and reduced costs (campaign effect).",
            cooldown_seconds=9999, level_required=40, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._master_of_coin = True
        self.cooldown = self.cooldown_max
        return True


class ShadowWar(Ability):
    """Passive: campaign stealth effect."""

    def __init__(self):
        super().__init__(
            name="Shadow War",
            description="Passive: army gains stealth on campaign map.",
            cooldown_seconds=9999, level_required=45, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._shadow_war_active = True
        self.cooldown = self.cooldown_max
        return True


# ── Engineer Abilities ────────────────────────────────────────────────

class ConstructGolem(Ability):
    """Placeholder: deal damage in area (actual summon TBD)."""

    def __init__(self):
        super().__init__(
            name="Construct Golem",
            description="Deploy a golem that damages nearby enemies.",
            cooldown_seconds=30, level_required=1, radius=100,
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
                    s.take_damage(dmg, 50)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class FortifyPosition(Ability):
    """Grant +30% armor to nearby squads for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Fortify Position",
            description="Nearby squads gain +30% armor for 15 seconds.",
            cooldown_seconds=40, level_required=5, radius=200,
        )
        self.duration = 15 * 60
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
            sq._fortified = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_fortified'):
                        sq._fortified = False
                self.affected_squads = []


class FieldArtillery(Ability):
    """Long-range AOE damage at target location."""

    def __init__(self):
        super().__init__(
            name="Field Artillery",
            description="Fire artillery at the nearest enemy concentration.",
            cooldown_seconds=35, level_required=10, radius=350,
        )
        self.blast_radius = 100

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        # Find densest enemy cluster in range
        best_target = None
        best_count = 0
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            d = distance(general.x, general.y, sq.x, sq.y)
            if d < self.radius:
                count = len(sq.alive_soldiers)
                if count > best_count:
                    best_count = count
                    best_target = sq
        if not best_target:
            return False
        # Deal AOE damage around target squad center
        tx, ty = best_target.x, best_target.y
        hit_any = False
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(tx, ty, s.x, s.y)
                if d < self.blast_radius:
                    dmg = general.melee_attack * 2.0
                    s.take_damage(dmg, 70)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class ImprovedConstructs(Ability):
    """Passive: flag for construct bonuses."""

    def __init__(self):
        super().__init__(
            name="Improved Constructs",
            description="Passive: constructs deal +25% damage and have +25% health.",
            cooldown_seconds=9999, level_required=15, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._improved_constructs = True
        self.cooldown = self.cooldown_max
        return True


class SiegeExpert(Ability):
    """Passive: flag for siege damage bonus."""

    def __init__(self):
        super().__init__(
            name="Siege Expert",
            description="Passive: +50% damage to walls and gates in siege battles.",
            cooldown_seconds=9999, level_required=20, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._siege_expert = True
        self.cooldown = self.cooldown_max
        return True


class MechanicalArmy(Ability):
    """Passive: flag for more construct slots."""

    def __init__(self):
        super().__init__(
            name="Mechanical Army",
            description="Passive: +3 construct deployment slots.",
            cooldown_seconds=9999, level_required=25, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._mechanical_army = True
        self.cooldown = self.cooldown_max
        return True


class ExperimentalWeaponry(Ability):
    """Nearby ranged squads gain fire damage for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Experimental Weaponry",
            description="Nearby ranged squads gain fire damage for 15 seconds.",
            cooldown_seconds=50, level_required=30, radius=200,
        )
        self.duration = 15 * 60
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = [sq for sq in self._squads_in_range(general, friendly_squads)
                    if getattr(sq, 'is_ranged', False)]
        if not targets:
            return False
        self.affected_squads = targets
        self.active_timer = self.duration
        for sq in targets:
            sq._fire_damage = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_fire_damage'):
                        sq._fire_damage = False
                self.affected_squads = []


class MobileFortress(Ability):
    """Massive armor buff to all squads for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Mobile Fortress",
            description="All friendly squads gain massive armor for 20 seconds.",
            cooldown_seconds=70, level_required=35, radius=350,
        )
        self.duration = 20 * 60
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
            sq._mobile_fortress = True
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_mobile_fortress'):
                        sq._mobile_fortress = False
                self.affected_squads = []


class MasterEngineer(Ability):
    """Passive: cooldown reduction 25%."""

    def __init__(self):
        super().__init__(
            name="Master Engineer",
            description="Passive: all ability cooldowns reduced by 25%.",
            cooldown_seconds=9999, level_required=40, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._cooldown_reduction = 25
        self.cooldown = self.cooldown_max
        return True


class WarMachine(Ability):
    """Placeholder: massive AOE damage."""

    def __init__(self):
        super().__init__(
            name="War Machine",
            description="Deploy a devastating war machine that obliterates enemies.",
            cooldown_seconds=90, level_required=45, radius=250,
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
                    dmg = general.melee_attack * 3.5
                    s.take_damage(dmg, 90)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


# ── Necromancer Abilities ─────────────────────────────────────────────

class RaiseDead(Ability):
    """Heal a friendly squad or deal damage near corpses."""

    def __init__(self):
        super().__init__(
            name="Raise Dead",
            description="Restore soldiers to the weakest nearby friendly squad.",
            cooldown_seconds=35, level_required=1, radius=200,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        targets = self._squads_in_range(general, friendly_squads)
        if not targets:
            return False
        # Find weakest squad (most casualties)
        target = min(targets, key=lambda sq: len(sq.alive_soldiers))
        # Heal existing soldiers
        for s in target.alive_soldiers:
            s.health = min(s.health + 20, s.max_health)
        target.apply_morale_modifier(10)
        self.cooldown = self.cooldown_max
        return True


class LifeDrain(Ability):
    """Damage nearest enemy, heal general."""

    def __init__(self):
        super().__init__(
            name="Life Drain",
            description="Drain life from nearest enemy soldier, healing the general.",
            cooldown_seconds=20, level_required=5, radius=150,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        best_soldier = None
        best_dist = self.radius
        best_squad = None
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(general.x, general.y, s.x, s.y)
                if d < best_dist:
                    best_dist = d
                    best_soldier = s
                    best_squad = sq
        if not best_soldier:
            return False
        dmg = general.melee_attack * 2.0
        best_soldier.take_damage(dmg, 60)
        # Heal general for damage dealt
        heal = dmg * 0.5
        general.health = min(general.health + heal, general.max_health)
        if not best_soldier.alive:
            general.kills += 1
            best_squad.on_casualty()
        self.cooldown = self.cooldown_max
        return True


class SummonWraith(Ability):
    """Placeholder: AOE magic damage with ethereal theme."""

    def __init__(self):
        super().__init__(
            name="Summon Wraith",
            description="Summon a wraith that damages all nearby enemies.",
            cooldown_seconds=35, level_required=10, radius=120,
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
                    dmg = general.melee_attack * 1.8
                    s.take_damage(dmg, 70)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class CorpseExplosion(Ability):
    """AOE damage centered on weakest friendly squad."""

    def __init__(self):
        super().__init__(
            name="Corpse Explosion",
            description="Cause an explosion near your weakest squad, damaging nearby enemies.",
            cooldown_seconds=40, level_required=15, radius=300,
        )
        self.blast_radius = 100

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        # Find weakest friendly squad (fewest alive soldiers)
        valid = [sq for sq in friendly_squads if not sq.is_destroyed]
        if not valid:
            return False
        weakest = min(valid, key=lambda sq: len(sq.alive_soldiers))
        tx, ty = weakest.x, weakest.y
        hit_any = False
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(tx, ty, s.x, s.y)
                if d < self.blast_radius:
                    dmg = general.melee_attack * 2.5
                    s.take_damage(dmg, 80)
                    hit_any = True
                    if not s.alive:
                        general.kills += 1
                        sq.on_casualty()
        if hit_any:
            self.cooldown = self.cooldown_max
        return hit_any


class DeathAura(Ability):
    """DOT to nearby enemies for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Death Aura",
            description="Emit a death aura that damages nearby enemies for 15 seconds.",
            cooldown_seconds=50, level_required=20, radius=150,
        )
        self.duration = 15 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._death_aura_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class AnimateLegion(Ability):
    """Heal all friendly squads (restore soldiers' health)."""

    def __init__(self):
        super().__init__(
            name="Animate Legion",
            description="Heal all friendly squads, restoring soldier health.",
            cooldown_seconds=65, level_required=25, radius=350,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        healed_any = False
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            d = distance(general.x, general.y, sq.x, sq.y)
            if d < self.radius:
                for s in sq.alive_soldiers:
                    s.health = min(s.health + 30, s.max_health)
                sq.apply_morale_modifier(10)
                healed_any = True
        if healed_any:
            self.cooldown = self.cooldown_max
        return healed_any


class SoulHarvest(Ability):
    """Every kill restores cooldowns faster for 20 seconds."""

    def __init__(self):
        super().__init__(
            name="Soul Harvest",
            description="Kills restore cooldowns faster for 20 seconds.",
            cooldown_seconds=60, level_required=30, radius=0,
        )
        self.duration = 20 * 60
        self.active_timer = 0

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._soul_harvest_active = True
        self.active_timer = self.duration
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                pass  # General update clears the flag


class DreadLord(Ability):
    """Terror + fear immunity for all friendlies for 15 seconds."""

    def __init__(self):
        super().__init__(
            name="Dread Lord",
            description="Allies become immune to fear; enemies lose 20 morale.",
            cooldown_seconds=60, level_required=35, radius=250,
        )
        self.duration = 15 * 60
        self.active_timer = 0
        self.affected_squads = []

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        friendly_targets = self._squads_in_range(general, friendly_squads)
        enemy_targets = self._squads_in_range(general, enemy_squads)
        if not friendly_targets and not enemy_targets:
            return False
        self.affected_squads = friendly_targets
        self.active_timer = self.duration
        for sq in friendly_targets:
            sq._fear_immune = True
            sq._hold_the_line = True
        for sq in enemy_targets:
            sq.apply_morale_modifier(-20)
        self.cooldown = self.cooldown_max
        return True

    def tick(self):
        super().tick()
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0:
                for sq in self.affected_squads:
                    if hasattr(sq, '_fear_immune'):
                        sq._fear_immune = False
                    if hasattr(sq, '_hold_the_line'):
                        sq._hold_the_line = False
                self.affected_squads = []


class LichTransformation(Ability):
    """Passive: regen, no morale effects."""

    def __init__(self):
        super().__init__(
            name="Lich Transformation",
            description="Passive: general regenerates health and ignores morale effects.",
            cooldown_seconds=9999, level_required=40, radius=0,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        general._lich_transform_active = True
        self.cooldown = self.cooldown_max
        return True


class ArmyOfTheDamned(Ability):
    """Massive heal + morale restore to all friendly squads."""

    def __init__(self):
        super().__init__(
            name="Army of the Damned",
            description="Massive heal and morale boost to all friendly squads.",
            cooldown_seconds=90, level_required=45, radius=500,
        )

    def activate(self, general, friendly_squads, enemy_squads):
        if not self.ready:
            return False
        healed_any = False
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                s.health = min(s.health + 50, s.max_health)
            sq.apply_morale_modifier(40)
            healed_any = True
        if healed_any:
            self.cooldown = self.cooldown_max
        return healed_any


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


# ── Class Ability Trees (6 classes, 10 abilities each) ────────────────

def get_warlord_abilities():
    """Warlord: army leadership and morale mastery."""
    return [
        WarlordRally(),           # Lv 1
        ForcedMarch(),            # Lv 5
        WarlordSecondWind(),      # Lv 10
        WarlordHoldTheLine(),     # Lv 15
        InspiringCharge(),        # Lv 20
        WarCry(),                 # Lv 25
        IronDiscipline(),         # Lv 30
        DetachmentCommand(),      # Lv 35
        LegendaryCommander(),     # Lv 40
        OverlordsDecree(),        # Lv 45
    ]


def get_battlemage_abilities():
    """Battlemage: offensive magic and arcane power."""
    return [
        ArcaneBolt(),             # Lv 1
        ManaShield(),             # Lv 5
        ElementalBlast(),         # Lv 10
        EnchantWeapons(),         # Lv 15
        SummonElemental(),        # Lv 20
        ChainLightning(),         # Lv 25
        ArcaneStorm(),            # Lv 30
        MassTeleport(),           # Lv 35
        MageLord(),               # Lv 40
        Cataclysm(),              # Lv 45
    ]


def get_champion_class_abilities():
    """Champion (player class): personal combat prowess."""
    return [
        ChampionBloodlust(),      # Lv 1
        ChampionIntimidate(),     # Lv 5
        ChampionChallenge(),      # Lv 10
        ChampionRampage(),        # Lv 15
        Deathblow(),              # Lv 20
        TerrifyingPresence(),     # Lv 25
        Unstoppable(),            # Lv 30
        Slayer(),                 # Lv 35
        OneManArmy(),             # Lv 40
        AvatarOfWar(),            # Lv 45
    ]


def get_rogue_abilities():
    """Rogue: stealth, sabotage, and assassination."""
    return [
        Ambush(),                 # Lv 1
        ScoutNetwork(),           # Lv 5
        PoisonedWeapons(),        # Lv 10
        Bribe(),                  # Lv 15
        Shadowstep(),             # Lv 20
        Sabotage(),               # Lv 25
        InciteRebellion(),        # Lv 30
        Assassinate(),            # Lv 35
        MasterOfCoin(),           # Lv 40
        ShadowWar(),              # Lv 45
    ]


def get_engineer_abilities():
    """Engineer: constructs, fortifications, and siege mastery."""
    return [
        ConstructGolem(),         # Lv 1
        FortifyPosition(),        # Lv 5
        FieldArtillery(),         # Lv 10
        ImprovedConstructs(),     # Lv 15
        SiegeExpert(),            # Lv 20
        MechanicalArmy(),         # Lv 25
        ExperimentalWeaponry(),   # Lv 30
        MobileFortress(),         # Lv 35
        MasterEngineer(),         # Lv 40
        WarMachine(),             # Lv 45
    ]


def get_necromancer_abilities():
    """Necromancer: death magic, life drain, and undead mastery."""
    return [
        RaiseDead(),              # Lv 1
        LifeDrain(),              # Lv 5
        SummonWraith(),           # Lv 10
        CorpseExplosion(),        # Lv 15
        DeathAura(),              # Lv 20
        AnimateLegion(),          # Lv 25
        SoulHarvest(),            # Lv 30
        DreadLord(),              # Lv 35
        LichTransformation(),     # Lv 40
        ArmyOfTheDamned(),        # Lv 45
    ]


def get_abilities_for_class(player_class):
    """Return the unique 10-ability tree for a player class."""
    class_map = {
        "warlord": get_warlord_abilities,
        "battlemage": get_battlemage_abilities,
        "champion": get_champion_class_abilities,
        "rogue": get_rogue_abilities,
        "engineer": get_engineer_abilities,
        "necromancer": get_necromancer_abilities,
    }
    getter = class_map.get(player_class)
    if getter:
        return getter()
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
