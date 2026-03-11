"""Squad - a group of soldiers that moves and fights as a unit."""

import math
import random
import pygame
from core.settings import (
    SOLDIER_SPACING, MELEE_RANGE, SOLDIER_RADIUS,
    MORALE_BREAK_THRESHOLD, MORALE_ROUT_THRESHOLD,
    MORALE_RECOVERY_RATE, MORALE_DAMAGE_LOSS, MORALE_CASUALTY_LOSS,
    CHARGE_BONUS_DISTANCE, TEAM_COLORS, TEAM_COLORS_LIGHT,
)
from core.utils import distance, angle_between, normalize, clamp
from battle.soldier import Soldier


class SquadState:
    IDLE = "idle"
    MOVING = "moving"
    CHARGING = "charging"
    FIGHTING = "fighting"
    FIRING = "firing"
    BROKEN = "broken"
    ROUTED = "routed"


class Squad:
    def __init__(self, unit_stats, team, x, y, facing_angle=0.0):
        self.unit_stats = unit_stats
        self.team = team
        self.x = x
        self.y = y
        self.facing_angle = facing_angle
        self.target_x = x
        self.target_y = y
        self.state = SquadState.IDLE
        self.morale = 100.0
        self.selected = False
        self.target_squad = None
        self.is_cavalry = unit_stats.speed >= 3.5
        self.is_ranged = unit_stats.ranged_attack > 0 and unit_stats.range_distance > 0
        self.is_spear = "spear" in unit_stats.name.lower()
        self.fire_at_will = True
        self.charging = False
        self.charge_timer = 0

        # Create soldiers in formation
        self.soldiers = []
        self._create_formation(unit_stats)

        # Track for morale
        self.initial_count = len(self.soldiers)
        self.kills = 0

    def _create_formation(self, stats):
        count = stats.squad_size
        cols = max(1, int(math.sqrt(count * 2)))  # wider than deep
        rows = math.ceil(count / cols)
        for i in range(count):
            row = i // cols
            col = i % cols
            # Center the formation
            ox = (col - cols / 2.0 + 0.5) * SOLDIER_SPACING
            oy = (row - rows / 2.0 + 0.5) * SOLDIER_SPACING
            sx = self.x + ox
            sy = self.y + oy
            soldier = Soldier(sx, sy, stats, self.team)
            soldier.formation_x = ox
            soldier.formation_y = oy
            self.soldiers.append(soldier)

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers if s.alive]

    @property
    def alive_count(self):
        return sum(1 for s in self.soldiers if s.alive)

    @property
    def is_destroyed(self):
        return self.alive_count == 0

    @property
    def center(self):
        alive = self.alive_soldiers
        if not alive:
            return (self.x, self.y)
        cx = sum(s.x for s in alive) / len(alive)
        cy = sum(s.y for s in alive) / len(alive)
        return (cx, cy)

    def give_move_order(self, tx, ty):
        self.target_x = tx
        self.target_y = ty
        self.target_squad = None
        self.state = SquadState.MOVING
        self.facing_angle = angle_between(self.x, self.y, tx, ty)

    def give_attack_order(self, target_squad):
        self.target_squad = target_squad
        tx, ty = target_squad.center
        self.target_x = tx
        self.target_y = ty
        dist = distance(self.x, self.y, tx, ty)
        if self.is_ranged and dist <= self.unit_stats.range_distance:
            self.state = SquadState.FIRING
        else:
            self.state = SquadState.CHARGING
            self.charging = True
            self.charge_timer = 0

    def update(self, all_squads):
        if self.is_destroyed:
            return

        # Update individual soldiers
        for s in self.alive_soldiers:
            s.update()

        # Morale recovery when idle
        if self.state == SquadState.IDLE and self.morale < 100:
            self.morale = min(100, self.morale + MORALE_RECOVERY_RATE)

        # Handle routing
        if self.state == SquadState.ROUTED:
            self._do_rout()
            return
        if self.morale <= MORALE_ROUT_THRESHOLD:
            self.state = SquadState.ROUTED
            return
        if self.morale <= MORALE_BREAK_THRESHOLD and self.state != SquadState.BROKEN:
            self.state = SquadState.BROKEN
            # Broken units retreat
            self.target_x = self.x + math.cos(self.facing_angle + math.pi) * 200
            self.target_y = self.y + math.sin(self.facing_angle + math.pi) * 200

        if self.state == SquadState.BROKEN:
            self._do_movement(speed_mult=0.8)
            if self.morale > MORALE_BREAK_THRESHOLD + 10:
                self.state = SquadState.IDLE
            return

        # Auto-target if we lost our target
        if self.target_squad and self.target_squad.is_destroyed:
            self.target_squad = None
            self.state = SquadState.IDLE

        # Fire at will - auto acquire targets for ranged
        if self.is_ranged and self.fire_at_will and self.state == SquadState.IDLE:
            self._auto_acquire_ranged_target(all_squads)

        if self.state == SquadState.MOVING:
            self._do_movement()
        elif self.state == SquadState.CHARGING:
            self._do_charge()
        elif self.state == SquadState.FIRING:
            self._do_ranged(all_squads)
        elif self.state == SquadState.FIGHTING:
            self._do_melee()

        # Update squad position to center of living soldiers
        cx, cy = self.center
        self.x, self.y = cx, cy

    def _do_movement(self, speed_mult=1.0):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 5:
            self.state = SquadState.IDLE
            return
        nx, ny = normalize(dx, dy)
        speed = self.unit_stats.speed * speed_mult
        for s in self.alive_soldiers:
            goal_x = self.target_x + s.formation_x
            goal_y = self.target_y + s.formation_y
            sdx = goal_x - s.x
            sdy = goal_y - s.y
            snx, sny = normalize(sdx, sdy)
            s.x += snx * speed
            s.y += sny * speed

    def _do_charge(self):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            self.charging = False
            return
        tx, ty = self.target_squad.center
        dist = distance(self.x, self.y, tx, ty)
        if dist < MELEE_RANGE * 2:
            self.state = SquadState.FIGHTING
            self.charge_timer = 30  # bonus frames
            return
        self.target_x = tx
        self.target_y = ty
        self.facing_angle = angle_between(self.x, self.y, tx, ty)
        speed_mult = 1.5 if self.is_cavalry else 1.2
        self._do_movement(speed_mult=speed_mult)

    def _do_melee(self):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            self.charging = False
            return
        is_charge = self.charge_timer > 0
        if self.charge_timer > 0:
            self.charge_timer -= 1
        for s in self.alive_soldiers:
            if s.attack_cooldown > 0:
                continue
            # Find nearest enemy soldier
            best = None
            best_dist = MELEE_RANGE * 3
            for es in self.target_squad.alive_soldiers:
                d = distance(s.x, s.y, es.x, es.y)
                if d < best_dist:
                    best_dist = d
                    best = es
            if best:
                if best_dist <= MELEE_RANGE:
                    dmg = s.attack(best, is_charging=is_charge)
                    if dmg > 0 and not best.alive:
                        self.kills += 1
                        self.target_squad.on_casualty()
                else:
                    # Move toward enemy
                    nx, ny = normalize(best.x - s.x, best.y - s.y)
                    s.x += nx * self.unit_stats.speed
                    s.y += ny * self.unit_stats.speed

    def _do_ranged(self, all_squads):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            return
        tx, ty = self.target_squad.center
        dist = distance(self.x, self.y, tx, ty)
        if dist > self.unit_stats.range_distance * 1.1:
            # Move closer
            self.target_x = tx
            self.target_y = ty
            self._do_movement()
            return
        if dist < MELEE_RANGE * 3:
            # Too close, switch to melee
            self.state = SquadState.FIGHTING
            return
        # Fire
        self.facing_angle = angle_between(self.x, self.y, tx, ty)
        for s in self.alive_soldiers:
            if s.attack_cooldown > 0:
                continue
            targets = self.target_squad.alive_soldiers
            if targets:
                target = random.choice(targets)
                dmg = s.ranged_attack(target)
                if dmg > 0 and not target.alive:
                    self.kills += 1
                    self.target_squad.on_casualty()

    def _auto_acquire_ranged_target(self, all_squads):
        best = None
        best_dist = self.unit_stats.range_distance
        for sq in all_squads:
            if sq.team == self.team or sq.is_destroyed:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < best_dist:
                best_dist = d
                best = sq
        if best:
            self.target_squad = best
            self.state = SquadState.FIRING

    def _do_rout(self):
        # Run away from center of battlefield
        angle = self.facing_angle + math.pi
        speed = self.unit_stats.speed * 1.5
        for s in self.alive_soldiers:
            s.x += math.cos(angle) * speed + random.uniform(-0.5, 0.5)
            s.y += math.sin(angle) * speed + random.uniform(-0.5, 0.5)

    def on_casualty(self):
        ratio = self.alive_count / max(1, self.initial_count)
        self.morale -= MORALE_CASUALTY_LOSS + (1 - ratio) * 3

    def apply_morale_modifier(self, amount):
        self.morale = clamp(self.morale + amount, 0, 100)

    def get_bounding_box(self):
        alive = self.alive_soldiers
        if not alive:
            return (self.x, self.y, 1, 1)
        min_x = min(s.x for s in alive)
        min_y = min(s.y for s in alive)
        max_x = max(s.x for s in alive)
        max_y = max(s.y for s in alive)
        padding = SOLDIER_SPACING
        return (min_x - padding, min_y - padding,
                max_x - min_x + padding * 2, max_y - min_y + padding * 2)

    def draw(self, surface, camera):
        color = TEAM_COLORS[self.team]
        light_color = TEAM_COLORS_LIGHT[self.team]

        for s in self.alive_soldiers:
            sx, sy = camera.world_to_screen(s.x, s.y)
            r = camera.scale(SOLDIER_RADIUS)
            # Health-based color (fade to dark as damaged)
            hp_ratio = s.health / s.max_health
            c = tuple(int(ch * (0.4 + 0.6 * hp_ratio)) for ch in color)
            pygame.draw.circle(surface, c, (sx, sy), r)

        # Selection highlight
        if self.selected:
            bbox = self.get_bounding_box()
            screen_pos = camera.world_to_screen(bbox[0], bbox[1])
            w = camera.scale(bbox[2])
            h = camera.scale(bbox[3])
            pygame.draw.rect(surface, light_color, (*screen_pos, w, h), 2)

        # Morale bar above squad
        cx, cy = self.center
        scx, scy = camera.world_to_screen(cx, cy)
        bar_w = camera.scale(40)
        bar_h = max(2, camera.scale(4))
        bar_x = scx - bar_w // 2
        bar_y = scy - camera.scale(25)
        # Background
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
        # Morale fill
        morale_w = int(bar_w * self.morale / 100)
        morale_color = (50, 200, 50) if self.morale > 50 else (
            (220, 200, 50) if self.morale > 25 else (200, 50, 50))
        pygame.draw.rect(surface, morale_color, (bar_x, bar_y, morale_w, bar_h))

        # Squad name and count
        if camera.zoom > 0.5:
            font = pygame.font.SysFont(None, max(12, camera.scale(14)))
            label = f"{self.unit_stats.name} ({self.alive_count})"
            if self.state == SquadState.ROUTED:
                label += " ROUTED!"
            elif self.state == SquadState.BROKEN:
                label += " WAVERING"
            text = font.render(label, True, light_color)
            surface.blit(text, (scx - text.get_width() // 2, bar_y - bar_h - 12))

        # Range circle for ranged units (when selected)
        if self.selected and self.is_ranged:
            r = camera.scale(self.unit_stats.range_distance)
            range_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(range_surf, (*light_color, 40), (r, r), r)
            pygame.draw.circle(range_surf, (*light_color, 80), (r, r), r, 1)
            surface.blit(range_surf, (scx - r, scy - r))
