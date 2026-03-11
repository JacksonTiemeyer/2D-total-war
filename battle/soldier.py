"""Individual soldier within a squad."""

import math
import random
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

    def take_damage(self, amount):
        effective_armor = self.stats.armor * random.uniform(0.5, 1.0)
        damage = max(1, amount - effective_armor)
        if self.stats.shield and random.random() < 0.2:
            damage *= 0.5  # shield block
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return damage

    def attack(self, target_soldier, is_charging=False):
        if self.attack_cooldown > 0:
            return 0
        attack_power = self.stats.melee_attack
        if is_charging:
            attack_power += self.stats.charge_bonus
        # Randomize
        attack_roll = attack_power * random.uniform(0.7, 1.3)
        defense_roll = target_soldier.stats.melee_defense * random.uniform(0.6, 1.0)
        damage = max(1, attack_roll - defense_roll * 0.5)
        actual = target_soldier.take_damage(damage)
        self.attack_cooldown = 30  # half a second
        return actual

    def ranged_attack(self, target_soldier):
        if self.attack_cooldown > 0 or self.stats.ranged_attack == 0:
            return 0
        dist = distance(self.x, self.y, target_soldier.x, target_soldier.y)
        if dist > self.stats.range_distance:
            return 0
        # Accuracy falls off with distance
        accuracy = max(0.3, 1.0 - (dist / self.stats.range_distance) * 0.6)
        if random.random() > accuracy:
            self.attack_cooldown = 60  # 1 second between shots
            return 0  # miss
        damage = self.stats.ranged_attack * random.uniform(0.6, 1.2)
        actual = target_soldier.take_damage(damage)
        self.attack_cooldown = 60
        return actual

    def update(self):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
