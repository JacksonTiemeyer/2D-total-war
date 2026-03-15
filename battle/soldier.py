"""Individual soldier within a squad."""

import math
import random
from core.settings import (
    EXHAUSTION_DAMAGE_PENALTY, EXHAUSTION_COOLDOWN_PENALTY,
)
from core.utils import distance, angle_between, normalize
from data.traits import (
    compute_damage_type_multiplier, compute_trait_damage_multiplier,
    compute_frenzy_speed_bonus, should_evade, is_immune_to_poison,
    get_damage_type, has_trait,
    TRAIT_FRENZY, TRAIT_POISON_ATTACK, TRAIT_FLYING,
    TRAIT_REGENERATING, TRAIT_ARMORED_CONSTRUCT,
    DMG_PHYSICAL,
    POISON_DOT_DAMAGE, POISON_DOT_DURATION,
    REGENERATION_RATE, FLYING_RANGED_VULN,
)


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
        self.facing_angle = 0.0  # individual facing for shape rotation
        self.exhaustion = 0.0   # 0-100
        # Engagement lock (A1): soldier currently locked in melee with
        self.engaged_with = None    # reference to enemy Soldier or None
        # Animation state
        self.hit_flash_timer = 0    # frames remaining for white flash
        self.death_timer = -1       # -1 = alive, >0 = dying animation frames
        self.death_alpha = 1.0      # fade out on death
        # Trait state
        self.poison_timer = 0       # frames remaining for poison DOT
        self.poison_dps = 0.0       # poison damage per frame

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

    def take_damage(self, amount, armor_penetration=0, damage_type=DMG_PHYSICAL,
                    attacker_stats=None):
        """Take damage with armor penetration and damage type support.

        armor_penetration: 0-100, percentage of armor ignored.
        damage_type: str from data.traits (physical, magical, fire, etc.)
        attacker_stats: UnitStats of the attacker for trait interactions.
        """
        # Small unit evasion check
        if should_evade(self.stats):
            return 0

        # Damage type multiplier (vulnerabilities, immunities, magic resistance)
        type_mult = compute_damage_type_multiplier(damage_type, self.stats)
        if type_mult <= 0:
            return 0

        # Trait-based multiplier (anti_large, anti_infantry, ethereal, size)
        trait_mult = 1.0
        if attacker_stats is not None:
            trait_mult = compute_trait_damage_multiplier(attacker_stats, self.stats)

        # Physical armor only reduces physical damage
        if damage_type == DMG_PHYSICAL:
            pen_factor = 1.0 - (armor_penetration / 100.0)
            effective_armor = self.stats.armor * pen_factor * random.uniform(0.5, 1.0)
        else:
            # Non-physical damage ignores physical armor
            effective_armor = 0

        damage = max(1, amount * type_mult * trait_mult - effective_armor)

        if self.stats.shield and random.random() < 0.2:
            damage *= 0.5  # shield block

        self.health -= damage
        self.hit_flash_timer = 6  # flash white for 6 frames
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.death_timer = 15  # 15-frame death animation
            self.death_alpha = 1.0
        return damage

    def attack(self, target_soldier, is_charging=False, flank_mult=1.0,
               defense_terrain_mult=1.0):
        """Melee attack using weapon_strength and armor_penetration."""
        if self.attack_cooldown > 0:
            return 0

        # Base damage from weapon strength
        weapon_dmg = self.effective_weapon_strength()
        if is_charging:
            weapon_dmg += self.stats.charge_bonus * self.stats.mass

        # Attack skill vs defense skill determines hit quality
        attack_roll = self.stats.melee_attack * random.uniform(0.7, 1.3)
        defense_roll = (target_soldier.stats.melee_defense *
                        random.uniform(0.6, 1.0) * defense_terrain_mult)
        hit_quality = max(0.5, attack_roll / max(1, defense_roll))

        # Final damage = weapon strength * hit quality * flank bonus
        damage = weapon_dmg * min(hit_quality, 2.0) * flank_mult

        # Frenzy: attack speed bonus as HP drops
        cooldown_mult = 1.0
        if has_trait(self.stats, TRAIT_FRENZY):
            cooldown_mult = 1.0 / compute_frenzy_speed_bonus(self.health, self.max_health)

        dmg_type = get_damage_type(self.stats)
        actual = target_soldier.take_damage(
            damage, self.stats.armor_penetration,
            damage_type=dmg_type, attacker_stats=self.stats)

        # Poison DOT application
        if has_trait(self.stats, TRAIT_POISON_ATTACK) and actual > 0:
            if not is_immune_to_poison(getattr(target_soldier.stats, 'traits', ())):
                target_soldier.poison_timer = POISON_DOT_DURATION
                target_soldier.poison_dps = POISON_DOT_DAMAGE / 60.0  # per frame

        self.attack_cooldown = int(self.effective_cooldown(30) * cooldown_mult)
        return actual

    def ranged_attack(self, target_soldier, accuracy_mult=1.0, damage_mult=1.0):
        """Ranged attack using ranged_strength and ranged_armor_penetration."""
        if self.attack_cooldown > 0 or self.stats.ranged_attack == 0:
            return 0

        dist = distance(self.x, self.y, target_soldier.x, target_soldier.y)
        if dist > self.stats.range_distance:
            return 0

        # Accuracy falls off with distance, worsened by exhaustion, modified by terrain
        exhaust_acc_penalty = self.get_exhaustion_factor() * 0.15
        accuracy = max(0.2, 1.0 - (dist / self.stats.range_distance) * 0.6 - exhaust_acc_penalty)
        accuracy *= accuracy_mult
        if random.random() > accuracy:
            self.attack_cooldown = self.effective_cooldown(60)
            return 0  # miss

        # Damage from ranged strength
        damage = self.effective_ranged_strength() * random.uniform(0.7, 1.2)
        # Ranged skill modulates damage
        skill_mult = self.stats.ranged_attack / 15.0  # normalized around 1.0
        damage *= max(0.5, skill_mult)
        damage *= damage_mult  # terrain bonus

        # Flying units take bonus ranged damage
        if has_trait(target_soldier.stats, TRAIT_FLYING):
            damage *= FLYING_RANGED_VULN

        dmg_type = get_damage_type(self.stats)
        actual = target_soldier.take_damage(
            damage, self.stats.ranged_armor_penetration,
            damage_type=dmg_type, attacker_stats=self.stats)
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
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
        if self.death_timer > 0:
            self.death_timer -= 1
            self.death_alpha = max(0, self.death_timer / 15.0)

        if not self.alive:
            return

        # Poison DOT
        if self.poison_timer > 0:
            self.health -= self.poison_dps
            self.poison_timer -= 1
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.death_timer = 15
                self.death_alpha = 1.0

        # Regeneration
        if has_trait(self.stats, TRAIT_REGENERATING) and self.health < self.max_health:
            self.health = min(self.max_health,
                              self.health + self.max_health * REGENERATION_RATE / 60.0)
