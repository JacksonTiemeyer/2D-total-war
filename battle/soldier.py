"""Individual soldier within a squad."""

import math
import random
from core.settings import (
    EXHAUSTION_DAMAGE_PENALTY, EXHAUSTION_COOLDOWN_PENALTY,
)
from core.utils import distance, angle_between, normalize


class Soldier:
    def __init__(self, x, y, stats, team):
        self.x = x
        self.y = y
        self.stats = stats
        self.team = team
        self.health = stats.health
        self.max_health = stats.health
        self.alive = True
        self.target = None
        self.attack_cooldown = 0
        self.formation_x = 0.0  # offset from squad center
        self.formation_y = 0.0
        self.exhaustion = 0.0   # 0-100

    def get_exhaustion_factor(self):
        """Returns 0.0 (fresh) to 1.0 (fully exhausted)."""
        return self.exhaustion / 100.0

    def effective_weapon_strength(self):
        """Weapon strength reduced by exhaustion."""
        penalty = self.get_exhaustion_factor() * EXHAUSTION_DAMAGE_PENALTY
        return self.stats.weapon_strength * (1.0 - penalty)

    def effective_ranged_strength(self):
        """Ranged strength reduced by exhaustion."""
        penalty = self.get_exhaustion_factor() * EXHAUSTION_DAMAGE_PENALTY
        return self.stats.ranged_strength * (1.0 - penalty)

    def effective_cooldown(self, base_cooldown):
        """Attack cooldown increased by exhaustion."""
        penalty = self.get_exhaustion_factor() * EXHAUSTION_COOLDOWN_PENALTY
        return int(base_cooldown * (1.0 + penalty))

    def take_damage(self, amount, armor_penetration=0):
        """Take damage with armor penetration support.

        armor_penetration: 0-100, percentage of armor ignored.
        """
        # Calculate effective armor after penetration
        pen_factor = 1.0 - (armor_penetration / 100.0)
        effective_armor = self.stats.armor * pen_factor * random.uniform(0.5, 1.0)

        damage = max(1, amount - effective_armor)

        if self.stats.shield and random.random() < 0.2:
            damage *= 0.5  # shield block

        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return damage

    def attack(self, target_soldier, is_charging=False, flank_mult=1.0):
        """Melee attack using weapon_strength and armor_penetration."""
        if self.attack_cooldown > 0:
            return 0

        # Base damage from weapon strength
        weapon_dmg = self.effective_weapon_strength()
        if is_charging:
            weapon_dmg += self.stats.charge_bonus * self.stats.mass

        # Attack skill vs defense skill determines hit quality
        attack_roll = self.stats.melee_attack * random.uniform(0.7, 1.3)
        defense_roll = target_soldier.stats.melee_defense * random.uniform(0.6, 1.0)
        hit_quality = max(0.5, attack_roll / max(1, defense_roll))

        # Final damage = weapon strength * hit quality * flank bonus
        damage = weapon_dmg * min(hit_quality, 2.0) * flank_mult

        actual = target_soldier.take_damage(damage, self.stats.armor_penetration)
        self.attack_cooldown = self.effective_cooldown(30)
        return actual

    def ranged_attack(self, target_soldier):
        """Ranged attack using ranged_strength and ranged_armor_penetration."""
        if self.attack_cooldown > 0 or self.stats.ranged_attack == 0:
            return 0

        dist = distance(self.x, self.y, target_soldier.x, target_soldier.y)
        if dist > self.stats.range_distance:
            return 0

        # Accuracy falls off with distance, worsened by exhaustion
        exhaust_acc_penalty = self.get_exhaustion_factor() * 0.15
        accuracy = max(0.2, 1.0 - (dist / self.stats.range_distance) * 0.6 - exhaust_acc_penalty)
        if random.random() > accuracy:
            self.attack_cooldown = self.effective_cooldown(60)
            return 0  # miss

        # Damage from ranged strength
        damage = self.effective_ranged_strength() * random.uniform(0.7, 1.2)
        # Ranged skill modulates damage
        skill_mult = self.stats.ranged_attack / 15.0  # normalized around 1.0
        damage *= max(0.5, skill_mult)

        actual = target_soldier.take_damage(damage, self.stats.ranged_armor_penetration)
        self.attack_cooldown = self.effective_cooldown(60)
        return actual

    def brace_counter_attack(self, charging_soldier):
        """Counter-damage when braced spearman is charged by cavalry."""
        from core.settings import BRACE_CHARGE_DAMAGE_MULT
        damage = self.effective_weapon_strength() * BRACE_CHARGE_DAMAGE_MULT
        damage *= random.uniform(0.8, 1.2)
        actual = charging_soldier.take_damage(damage, self.stats.armor_penetration)
        return actual

    def update(self):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
