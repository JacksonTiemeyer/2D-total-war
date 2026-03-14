"""General/Hero system with Three Kingdoms-style dueling and abilities."""

import math
import random
import pygame
from core.settings import (
    GENERAL_RADIUS, GENERAL_HEALTH_MULTIPLIER,
    DUEL_RANGE, DUEL_CIRCLE_RADIUS, DUEL_DURATION_MAX,
    MELEE_RANGE, MORALE_GENERAL_AURA, MORALE_GENERAL_DEATH_PENALTY,
    TEAM_COLORS, GOLD, WHITE, BLACK, YELLOW, ORANGE,
)
from core.utils import distance, angle_between, normalize, clamp
from battle.soldier import Soldier
from battle.abilities import (
    get_abilities_for_type, level_from_xp, xp_for_level,
)


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
        self.attached_squad = None

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
        self.duel_clashes = []
        self.duel_score = 0

        # Type and aura
        self.general_type = unit_stats.name  # Commander, Champion, Strategist
        self.aura_radius = 150 if self.general_type == "Commander" else 100
        self.morale_aura = MORALE_GENERAL_AURA
        if self.general_type == "Commander":
            self.morale_aura *= 1.5

        # Stats tracking
        self.kills = 0
        self.duels_won = 0

        # Leveling
        self.xp = 0
        self.level = 1

        # Abilities
        self.abilities = get_abilities_for_type(self.general_type)

        # Buff flags (set by abilities)
        self._bloodlust_active = False
        self._sapping_fire = False
        self._scout_active = False
        self._all_enemy_generals = []  # set by battle scene
        self.visible = True  # fog of war

    @property
    def available_abilities(self):
        """Return abilities unlocked at current level."""
        return [a for a in self.abilities if a.level_required <= self.level]

    @property
    def xp_to_next(self):
        next_level = self.level + 1
        return max(0, xp_for_level(next_level) - self.xp)

    def gain_xp(self, amount):
        self.xp += amount
        new_level = level_from_xp(self.xp)
        if new_level > self.level:
            self.level = new_level

    def activate_ability(self, index, friendly_squads, enemy_squads):
        """Activate ability by index (0-based among available abilities)."""
        avail = self.available_abilities
        if index >= len(avail):
            return False
        return avail[index].activate(self, friendly_squads, enemy_squads)

    def give_move_order(self, tx, ty):
        self.target_x = tx
        self.target_y = ty

    def challenge_duel(self, other_general):
        """Initiate a duel challenge (Three Kingdoms style)."""
        if not other_general.alive or not self.alive:
            return False
        if self.duel_state != DuelState.NONE or other_general.duel_state != DuelState.NONE:
            return False
        dist_val = distance(self.x, self.y, other_general.x, other_general.y)
        if dist_val > DUEL_RANGE * 3:
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

        # Tick all abilities
        for a in self.abilities:
            a.tick()

        # Clear timed buff flags
        bloodlust_ability = next(
            (a for a in self.abilities if a.name == "Bloodlust"), None)
        if bloodlust_ability and hasattr(bloodlust_ability, 'active_timer'):
            if bloodlust_ability.active_timer <= 0:
                self._bloodlust_active = False

        sapping = next(
            (a for a in self.abilities if a.name == "Sapping Fire"), None)
        if sapping and hasattr(sapping, 'active_timer'):
            if sapping.active_timer <= 0:
                self._sapping_fire = False

        scout = next(
            (a for a in self.abilities if a.name == "Scout Report"), None)
        if scout and hasattr(scout, 'active_timer'):
            if scout.active_timer <= 0:
                self._scout_active = False

        # Duel takes priority
        if self.duel_state == DuelState.ACTIVE:
            self._update_duel()
            return

        # Movement
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist_val = math.sqrt(dx * dx + dy * dy)
        if dist_val > 5:
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
            # XP awarded post-battle, not during battle
            return

        opp = self.duel_opponent
        self.duel_timer += 1

        d = distance(self.x, self.y, opp.x, opp.y)
        if d > DUEL_RANGE:
            nx, ny = normalize(opp.x - self.x, opp.y - self.y)
            self.x += nx * self.speed * 0.8
            self.y += ny * self.speed * 0.8

        if self.duel_timer % 40 == 0 and self.attack_cooldown == 0:
            self._duel_clash(opp)

        if self.duel_timer >= DUEL_DURATION_MAX:
            if self.duel_score > opp.duel_score:
                opp.take_damage(self.melee_attack * 3)
            elif opp.duel_score > self.duel_score:
                self.take_damage(opp.melee_attack * 3)
            else:
                # Tie: both take reduced damage
                self.take_damage(opp.melee_attack)
                opp.take_damage(self.melee_attack)
            self._end_duel()

    def _duel_clash(self, opponent):
        """A single clash exchange in a duel."""
        my_attack = self.melee_attack
        opp_attack = opponent.melee_attack

        # Bloodlust buff
        if self._bloodlust_active:
            my_attack *= 1.5
        if opponent._bloodlust_active:
            opp_attack *= 1.5

        my_roll = my_attack * random.uniform(0.6, 1.4)
        opp_roll = opp_attack * random.uniform(0.6, 1.4)

        # Champion type gets duel bonus
        if self.general_type == "Champion":
            my_roll *= 1.3
        if opponent.general_type == "Champion":
            opp_roll *= 1.3

        if my_roll > opp_roll:
            # Use weapon strength for damage
            damage = max(5, self.unit_stats.weapon_strength *
                         random.uniform(0.8, 1.2) -
                         opponent.melee_defense * 0.3)
            opponent.take_damage(damage)
            self.duel_score += 1
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            self.duel_clashes.append((mid_x, mid_y, 15))
        else:
            damage = max(5, opponent.unit_stats.weapon_strength *
                         random.uniform(0.8, 1.2) -
                         self.melee_defense * 0.3)
            self.take_damage(damage)
            opponent.duel_score += 1
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            opponent.duel_clashes.append((mid_x, mid_y, 15))

        self.attack_cooldown = 20

        if not opponent.alive:
            self.duel_state = DuelState.WON
            self.duels_won += 1
            self.kills += 1
            # XP awarded post-battle, not during battle
            opponent.duel_state = DuelState.LOST
        elif not self.alive:
            opponent.duel_state = DuelState.WON
            opponent.duels_won += 1
            opponent.kills += 1
            # A6: XP awarded post-battle only, not during battle
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

    def draw(self, surface, camera, fog_hidden=False):
        if not self.alive or fog_hidden:
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

        # Bloodlust glow
        if self._bloodlust_active:
            glow_r = camera.scale(GENERAL_RADIUS + 6)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 50, 30, 80), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # General body - circle with outer ring + gold accent
        inner_r = max(1, int(r))
        outer_r = max(2, int(r + 3))
        pygame.draw.circle(surface, GOLD, (int(sx), int(sy)), outer_r, 2)
        pygame.draw.circle(surface, color, (int(sx), int(sy)), inner_r)

        # Level indicator (small number)
        if camera.zoom > 0.4:
            lvl_font = pygame.font.SysFont(None, max(10, camera.scale(11)))
            lvl_text = lvl_font.render(str(self.level), True, WHITE)
            surface.blit(lvl_text, (sx - lvl_text.get_width() // 2,
                                     sy - lvl_text.get_height() // 2))

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

        # XP bar (thin, below health)
        xp_y = bar_y + bar_h + 1
        xp_h = max(1, camera.scale(2))
        pygame.draw.rect(surface, (30, 30, 30), (bar_x, xp_y, bar_w, xp_h))
        next_threshold = xp_for_level(self.level + 1)
        prev_threshold = xp_for_level(self.level)
        range_xp = max(1, next_threshold - prev_threshold)
        progress = (self.xp - prev_threshold) / range_xp
        xp_w = int(bar_w * min(1.0, progress))
        pygame.draw.rect(surface, (100, 180, 255), (bar_x, xp_y, xp_w, xp_h))

        # Name label
        if camera.zoom > 0.4:
            font = pygame.font.SysFont(None, max(14, camera.scale(16)))
            label = f"{self.name} ({self.general_type}) Lv{self.level}"
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
