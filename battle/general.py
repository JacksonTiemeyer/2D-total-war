"""General/Hero system with Three Kingdoms-style dueling."""

import math
import random
import pygame
from core.settings import (
    GENERAL_RADIUS, GENERAL_HEALTH_MULTIPLIER,
    DUEL_RANGE, DUEL_CIRCLE_RADIUS, DUEL_DURATION_MAX,
    MELEE_RANGE, MORALE_GENERAL_AURA, MORALE_GENERAL_DEATH_PENALTY,
    TEAM_COLORS, GOLD, WHITE, BLACK, YELLOW,
)
from core.utils import distance, angle_between, normalize, clamp
from battle.soldier import Soldier


class DuelState:
    NONE = "none"
    CHALLENGED = "challenged"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"


class General:
    """A hero unit that leads an army and can engage in duels."""

    def __init__(self, name, unit_stats, team, x, y):
        self.name = name
        self.unit_stats = unit_stats
        self.team = team
        self.x = x
        self.y = y
        self.health = unit_stats.health * GENERAL_HEALTH_MULTIPLIER
        self.max_health = self.health
        self.alive = True
        self.speed = unit_stats.speed
        self.target_x = x
        self.target_y = y
        self.selected = False
        self.attached_squad = None  # squad this general is embedded in

        # Combat
        self.attack_cooldown = 0
        self.melee_attack = unit_stats.melee_attack
        self.melee_defense = unit_stats.melee_defense
        self.charge_bonus = unit_stats.charge_bonus
        self.armor = unit_stats.armor

        # Duel system
        self.duel_state = DuelState.NONE
        self.duel_opponent = None
        self.duel_timer = 0
        self.duel_clashes = []  # visual effects
        self.duel_score = 0  # accumulated advantage

        # Abilities based on type
        self.general_type = unit_stats.name  # Commander, Champion, Strategist
        self.aura_radius = 150 if self.general_type == "Commander" else 100
        self.morale_aura = MORALE_GENERAL_AURA
        if self.general_type == "Commander":
            self.morale_aura *= 1.5
        self.kills = 0
        self.duels_won = 0

    def give_move_order(self, tx, ty):
        self.target_x = tx
        self.target_y = ty

    def challenge_duel(self, other_general):
        """Initiate a duel challenge (Three Kingdoms style)."""
        if not other_general.alive or not self.alive:
            return False
        if self.duel_state != DuelState.NONE or other_general.duel_state != DuelState.NONE:
            return False
        dist = distance(self.x, self.y, other_general.x, other_general.y)
        if dist > DUEL_RANGE * 3:
            return False
        self.duel_state = DuelState.ACTIVE
        self.duel_opponent = other_general
        self.duel_timer = 0
        self.duel_score = 0
        other_general.duel_state = DuelState.ACTIVE
        other_general.duel_opponent = self
        other_general.duel_timer = 0
        other_general.duel_score = 0
        return True

    def update(self, friendly_squads, enemy_squads):
        if not self.alive:
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # Duel takes priority
        if self.duel_state == DuelState.ACTIVE:
            self._update_duel()
            return

        # Movement
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 5:
            nx, ny = normalize(dx, dy)
            self.x += nx * self.speed
            self.y += ny * self.speed

        # If attached to a squad, follow it
        if self.attached_squad and not self.attached_squad.is_destroyed:
            cx, cy = self.attached_squad.center
            self.x = cx
            self.y = cy

        # Apply morale aura to friendly squads
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < self.aura_radius:
                sq.apply_morale_modifier(self.morale_aura * 0.01)

    def _update_duel(self):
        """Process one frame of a duel."""
        if not self.duel_opponent or not self.duel_opponent.alive:
            self.duel_state = DuelState.WON
            self.duels_won += 1
            return

        opp = self.duel_opponent
        self.duel_timer += 1

        # Move toward each other
        d = distance(self.x, self.y, opp.x, opp.y)
        if d > DUEL_RANGE:
            nx, ny = normalize(opp.x - self.x, opp.y - self.y)
            self.x += nx * self.speed * 0.8
            self.y += ny * self.speed * 0.8

        # Clash every ~40 frames
        if self.duel_timer % 40 == 0 and self.attack_cooldown == 0:
            self._duel_clash(opp)

        # Duel timeout - whoever has more score wins the exchange
        if self.duel_timer >= DUEL_DURATION_MAX:
            if self.duel_score > opp.duel_score:
                # Winner gets a big final hit
                opp.take_damage(self.melee_attack * 3)
            elif opp.duel_score > self.duel_score:
                self.take_damage(opp.melee_attack * 3)
            self._end_duel()

    def _duel_clash(self, opponent):
        """A single clash exchange in a duel."""
        # Both attack simultaneously with rock-paper-scissors-like mechanics
        my_roll = self.melee_attack * random.uniform(0.6, 1.4)
        opp_roll = opponent.melee_attack * random.uniform(0.6, 1.4)

        # Champion type gets duel bonus
        if self.general_type == "Champion":
            my_roll *= 1.3
        if opponent.general_type == "Champion":
            opp_roll *= 1.3

        # Determine clash winner
        if my_roll > opp_roll:
            damage = max(5, my_roll - opponent.melee_defense * 0.3)
            opponent.take_damage(damage)
            self.duel_score += 1
            # Add visual clash effect
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            self.duel_clashes.append((mid_x, mid_y, 15))  # x, y, frames
        else:
            damage = max(5, opp_roll - self.melee_defense * 0.3)
            self.take_damage(damage)
            opponent.duel_score += 1
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            opponent.duel_clashes.append((mid_x, mid_y, 15))

        self.attack_cooldown = 20

        # Check for death during duel
        if not opponent.alive:
            self.duel_state = DuelState.WON
            self.duels_won += 1
            self.kills += 1
            opponent.duel_state = DuelState.LOST
        elif not self.alive:
            opponent.duel_state = DuelState.WON
            opponent.duels_won += 1
            opponent.kills += 1
            self.duel_state = DuelState.LOST

    def _end_duel(self):
        if self.duel_opponent:
            self.duel_opponent.duel_state = DuelState.NONE
            self.duel_opponent.duel_opponent = None
        self.duel_state = DuelState.NONE
        self.duel_opponent = None

    def take_damage(self, amount):
        effective_armor = self.armor * random.uniform(0.5, 1.0)
        damage = max(1, amount - effective_armor)
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return damage

    def on_death(self, friendly_squads):
        """Apply morale penalty when a general dies."""
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            sq.apply_morale_modifier(-MORALE_GENERAL_DEATH_PENALTY)

    def draw(self, surface, camera):
        if not self.alive:
            return

        sx, sy = camera.world_to_screen(self.x, self.y)
        r = camera.scale(GENERAL_RADIUS)
        color = TEAM_COLORS[self.team]

        # Duel circle
        if self.duel_state == DuelState.ACTIVE:
            duel_r = camera.scale(DUEL_CIRCLE_RADIUS)
            duel_surf = pygame.Surface((duel_r * 2, duel_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(duel_surf, (255, 215, 0, 50), (duel_r, duel_r), duel_r)
            pygame.draw.circle(duel_surf, GOLD, (duel_r, duel_r), duel_r, 2)
            surface.blit(duel_surf, (sx - duel_r, sy - duel_r))

        # General body - diamond shape
        points = [
            (sx, sy - r - 2),
            (sx + r + 2, sy),
            (sx, sy + r + 2),
            (sx - r - 2, sy),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, GOLD, points, 2)

        # Health bar
        bar_w = camera.scale(30)
        bar_h = max(2, camera.scale(4))
        bar_x = sx - bar_w // 2
        bar_y = sy - r - camera.scale(12)
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
        hp_w = int(bar_w * self.health / self.max_health)
        hp_color = (50, 220, 50) if self.health / self.max_health > 0.5 else (
            (220, 200, 50) if self.health / self.max_health > 0.25 else (220, 50, 50))
        pygame.draw.rect(surface, hp_color, (bar_x, bar_y, hp_w, bar_h))

        # Name label
        if camera.zoom > 0.4:
            font = pygame.font.SysFont(None, max(14, camera.scale(16)))
            label = f"{self.name} ({self.general_type})"
            text = font.render(label, True, GOLD)
            surface.blit(text, (sx - text.get_width() // 2, bar_y - 16))

        # Selection circle
        if self.selected:
            pygame.draw.circle(surface, GOLD, (sx, sy), r + 4, 2)

        # Draw duel clash effects
        new_clashes = []
        for cx, cy, frames in self.duel_clashes:
            if frames > 0:
                scx, scy = camera.world_to_screen(cx, cy)
                spark_r = camera.scale(8 + (15 - frames))
                alpha = int(255 * frames / 15)
                spark_surf = pygame.Surface((spark_r * 2, spark_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(spark_surf, (255, 255, 100, alpha),
                                   (spark_r, spark_r), spark_r)
                surface.blit(spark_surf, (scx - spark_r, scy - spark_r))
                new_clashes.append((cx, cy, frames - 1))
        self.duel_clashes = new_clashes

        # Aura radius (when selected)
        if self.selected:
            aura_r = camera.scale(self.aura_radius)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*GOLD, 25), (aura_r, aura_r), aura_r)
            pygame.draw.circle(aura_surf, (*GOLD, 60), (aura_r, aura_r), aura_r, 1)
            surface.blit(aura_surf, (sx - aura_r, sy - aura_r))
