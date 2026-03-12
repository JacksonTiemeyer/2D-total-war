"""Siege battle scene - special battle for attacking castles.

Extends BattleScene with walls, a gate, arrow towers, and ladders.
Defenders deploy on/behind walls; attackers must breach the gate or
scale walls with ladders.
"""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT,
    WHITE, GREY, GOLD, BLACK, BROWN, DARK_GREY,
)
from core.utils import distance
from battle.battle_scene import BattleScene, BattleResult
from battle.squad import SquadState


# ── Siege structures ────────────────────────────────────────────────────

class Gate:
    """A destructible gate in the wall."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.max_hp = 500
        self.hp = self.max_hp
        self.destroyed = False

    @property
    def rect(self):
        return (self.x, self.y, self.width, self.height)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.destroyed = True

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        w = camera.scale(self.width)
        h = camera.scale(self.height)
        if self.destroyed:
            # Rubble
            color = (100, 80, 60)
            pygame.draw.rect(surface, color, (sx, sy, w, h))
        else:
            color = (120, 80, 40)
            pygame.draw.rect(surface, color, (sx, sy, w, h))
            pygame.draw.rect(surface, (80, 50, 20), (sx, sy, w, h), 2)
            # HP bar
            bar_w = w
            bar_h = max(2, camera.scale(4))
            bar_y = sy - bar_h - 2
            pygame.draw.rect(surface, (40, 40, 40), (sx, bar_y, bar_w, bar_h))
            hp_w = int(bar_w * self.hp / self.max_hp)
            pygame.draw.rect(surface, (200, 100, 50), (sx, bar_y, hp_w, bar_h))

        if camera.zoom > 0.4:
            font = pygame.font.SysFont(None, max(12, camera.scale(14)))
            label = "GATE (Destroyed)" if self.destroyed else f"GATE ({self.hp}/{self.max_hp})"
            text = font.render(label, True, WHITE)
            surface.blit(text, (sx + w // 2 - text.get_width() // 2, sy - 18))


class WallSegment:
    """A section of castle wall that blocks movement."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def rect(self):
        return (self.x, self.y, self.width, self.height)

    def contains(self, px, py):
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        w = camera.scale(self.width)
        h = camera.scale(self.height)
        pygame.draw.rect(surface, (90, 90, 90), (sx, sy, w, h))
        pygame.draw.rect(surface, (60, 60, 60), (sx, sy, w, h), 2)
        # Battlements
        bsize = max(3, camera.scale(8))
        for bx in range(int(sx), int(sx + w), int(bsize * 2)):
            pygame.draw.rect(surface, (110, 110, 110),
                             (bx, int(sy - bsize), int(bsize), int(bsize)))


class Tower:
    """An arrow tower that auto-fires at nearby enemies."""

    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.range = 250
        self.damage = 8
        self.cooldown = 0
        self.cooldown_max = 45  # frames between shots
        self.radius = 20

    def update(self, enemy_squads):
        if self.cooldown > 0:
            self.cooldown -= 1
            return

        # Find nearest enemy in range
        best_target = None
        best_dist = self.range
        for sq in enemy_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                d = distance(self.x, self.y, s.x, s.y)
                if d < best_dist:
                    best_dist = d
                    best_target = (sq, s)

        if best_target:
            sq, s = best_target
            s.take_damage(self.damage, armor_penetration=20)
            if not s.alive:
                sq.on_casualty()
            self.cooldown = self.cooldown_max

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        r = camera.scale(self.radius)
        pygame.draw.rect(surface, (100, 100, 100),
                         (sx - r, sy - r, r * 2, r * 2))
        pygame.draw.rect(surface, (70, 70, 70),
                         (sx - r, sy - r, r * 2, r * 2), 2)
        # Tower top
        pygame.draw.rect(surface, (120, 120, 120),
                         (sx - r - 2, sy - r - 4, r * 2 + 4, 4))

        if camera.zoom > 0.4:
            font = pygame.font.SysFont(None, max(12, camera.scale(12)))
            text = font.render("Tower", True, WHITE)
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 2))


# ── Siege Scene ─────────────────────────────────────────────────────────

class SiegeScene(BattleScene):
    """Battle scene with castle walls, gate, and towers."""

    def __init__(self, player_army, enemy_army, player_is_attacker=True):
        self.player_is_attacker = player_is_attacker
        self.walls = []
        self.gate = None
        self.towers = []
        super().__init__(player_army, enemy_army)

    def _generate_terrain(self):
        """Override: generate siege-specific terrain with walls."""
        # Wall runs vertically through the middle of the map
        wall_x = BATTLE_MAP_WIDTH // 2
        gate_y = BATTLE_MAP_HEIGHT // 2 - 40
        wall_thickness = 30
        gate_height = 80

        # Wall segments (with gap for gate)
        self.walls.append(WallSegment(
            wall_x, 50, wall_thickness, gate_y - 50))
        self.walls.append(WallSegment(
            wall_x, gate_y + gate_height, wall_thickness,
            BATTLE_MAP_HEIGHT - gate_y - gate_height - 50))

        # Gate
        self.gate = Gate(wall_x, gate_y, wall_thickness, gate_height)

        # Towers at wall ends and near gate
        defender_team = 1 if self.player_is_attacker else 0
        self.towers.append(Tower(wall_x + 15, 80, defender_team))
        self.towers.append(Tower(wall_x + 15, gate_y - 30, defender_team))
        self.towers.append(Tower(wall_x + 15, gate_y + gate_height + 30, defender_team))
        self.towers.append(Tower(wall_x + 15, BATTLE_MAP_HEIGHT - 80, defender_team))

        # Minimal terrain behind walls for defenders
        self.terrain.append({
            "type": "hill",
            "rect": (wall_x + 100, BATTLE_MAP_HEIGHT // 2 - 100, 200, 200),
            "color": (80, 140, 60),
        })

    def _deploy_armies(self, player_army, enemy_army):
        """Override: attackers on left, defenders on right behind walls."""
        from battle.squad import Squad, Formation

        wall_x = BATTLE_MAP_WIDTH // 2
        spacing_y = 80

        # Attackers on left side
        atk_x = 200
        atk_start_y = BATTLE_MAP_HEIGHT // 2 - 300
        atk_data = player_army if self.player_is_attacker else enemy_army
        atk_team = 0 if self.player_is_attacker else 1
        atk_list = self.player_squads if self.player_is_attacker else self.enemy_squads

        for i, squad_entry in enumerate(atk_data.get("squads", [])):
            unit_stats, soldier_count = squad_entry[0], squad_entry[1]
            vet_data = squad_entry[2] if len(squad_entry) > 2 else None
            y = atk_start_y + i * spacing_y
            squad = Squad(unit_stats, atk_team, atk_x, y, facing_angle=0,
                          soldier_count=soldier_count if soldier_count != 1 else None,
                          vet_data=vet_data)
            atk_list.append(squad)

        # Defenders behind walls on right side
        def_x = wall_x + 150
        def_start_y = BATTLE_MAP_HEIGHT // 2 - 200
        def_data = enemy_army if self.player_is_attacker else player_army
        def_team = 1 if self.player_is_attacker else 0
        def_list = self.enemy_squads if self.player_is_attacker else self.player_squads

        for i, squad_entry in enumerate(def_data.get("squads", [])):
            unit_stats, soldier_count = squad_entry[0], squad_entry[1]
            vet_data = squad_entry[2] if len(squad_entry) > 2 else None
            y = def_start_y + i * spacing_y
            squad = Squad(unit_stats, def_team, def_x, y,
                          facing_angle=3.14159,
                          soldier_count=soldier_count if soldier_count != 1 else None,
                          vet_data=vet_data)
            def_list.append(squad)

        # Generals
        from battle.general import General
        atk_gen = atk_data.get("general")
        if atk_gen:
            gen = General(atk_gen["name"], atk_gen["stats"], atk_team,
                          atk_x - 50, BATTLE_MAP_HEIGHT // 2)
            if "xp" in atk_gen:
                gen.xp = atk_gen["xp"]
                gen.level = atk_gen["level"]
            if self.player_is_attacker:
                self.player_generals.append(gen)
            else:
                self.enemy_generals.append(gen)

        def_gen = def_data.get("general")
        if def_gen:
            gen = General(def_gen["name"], def_gen["stats"], def_team,
                          def_x + 50, BATTLE_MAP_HEIGHT // 2)
            if "xp" in def_gen:
                gen.xp = def_gen["xp"]
                gen.level = def_gen["level"]
            if self.player_is_attacker:
                self.enemy_generals.append(gen)
            else:
                self.player_generals.append(gen)

        self.all_squads = self.player_squads + self.enemy_squads
        self.all_generals = self.player_generals + self.enemy_generals

    def _tick(self):
        """Override: add wall collision, gate damage, and tower firing."""
        super()._tick()

        # Towers fire at enemies
        attacker_team = 0 if self.player_is_attacker else 1
        for tower in self.towers:
            targets = self.player_squads if tower.team != 0 else self.enemy_squads
            tower.update(targets)

        # Gate takes damage from nearby attacking melee units
        if self.gate and not self.gate.destroyed:
            for sq in (self.player_squads if self.player_is_attacker
                       else self.enemy_squads):
                if sq.is_destroyed or sq.state != SquadState.FIGHTING:
                    continue
                cx, cy = sq.center
                gx, gy = self.gate.x, self.gate.y + self.gate.height // 2
                if distance(cx, cy, gx, gy) < 80:
                    # Attacking the gate
                    dps = sq.alive_count * 0.3
                    self.gate.take_damage(dps)

        # Wall collision: push soldiers out of wall segments
        for sq in self.all_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                for wall in self.walls:
                    if wall.contains(s.x, s.y):
                        # Push soldier to nearest side
                        left_dist = abs(s.x - wall.x)
                        right_dist = abs(s.x - (wall.x + wall.width))
                        if left_dist < right_dist:
                            s.x = wall.x - 2
                        else:
                            s.x = wall.x + wall.width + 2

        # Gate collision (only if not destroyed)
        if self.gate and not self.gate.destroyed:
            for sq in self.all_squads:
                if sq.is_destroyed:
                    continue
                for s in sq.alive_soldiers:
                    gx, gy, gw, gh = self.gate.rect
                    if gx <= s.x <= gx + gw and gy <= s.y <= gy + gh:
                        left_dist = abs(s.x - gx)
                        right_dist = abs(s.x - (gx + gw))
                        if left_dist < right_dist:
                            s.x = gx - 2
                        else:
                            s.x = gx + gw + 2

    def draw(self, surface):
        """Override: draw walls, gate, towers on top of base battle scene."""
        surface.fill((90, 140, 60))

        # Grid
        grid_size = 100
        for x in range(0, BATTLE_MAP_WIDTH, grid_size):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, BATTLE_MAP_HEIGHT)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)
        for y in range(0, BATTLE_MAP_HEIGHT, grid_size):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(BATTLE_MAP_WIDTH, y)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)

        # Terrain patches
        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            screen_pos = self.camera.world_to_screen(rx, ry)
            w = self.camera.scale(rw)
            h = self.camera.scale(rh)
            pygame.draw.rect(surface, t["color"], (*screen_pos, w, h))

        # Walls
        for wall in self.walls:
            wall.draw(surface, self.camera)

        # Gate
        if self.gate:
            self.gate.draw(surface, self.camera)

        # Towers
        for tower in self.towers:
            tower.draw(surface, self.camera)

        # Fog overlay
        if self.fog_enabled:
            self._draw_fog(surface)

        # Squads and generals
        for sq in self.all_squads:
            if not sq.is_destroyed:
                fog_hidden = (sq.team != 0 and not sq.visible and self.fog_enabled)
                sq.draw(surface, self.camera, fog_hidden=fog_hidden)

        for g in self.all_generals:
            fog_hidden = (g.team != 0 and not g.visible and self.fog_enabled)
            g.draw(surface, self.camera, fog_hidden=fog_hidden)

        # Selection box
        if self.selecting:
            sx = min(self.select_start[0], self.select_end[0])
            sy = min(self.select_start[1], self.select_end[1])
            sw = abs(self.select_end[0] - self.select_start[0])
            sh = abs(self.select_end[1] - self.select_start[1])
            if sw > 0 and sh > 0:
                select_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                select_surf.fill((100, 200, 100, 40))
                surface.blit(select_surf, (sx, sy))
                pygame.draw.rect(surface, (100, 200, 100), (sx, sy, sw, sh), 1)

        self._draw_hud(surface)

        # Siege info overlay
        self._draw_siege_info(surface)

    def _draw_siege_info(self, surface):
        """Draw siege-specific info: gate HP, tower status."""
        font = pygame.font.SysFont(None, 18)
        y = 40
        if self.gate:
            label = "SIEGE BATTLE"
            text = font.render(label, True, GOLD)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 18
            if not self.gate.destroyed:
                gate_text = font.render(
                    f"Gate HP: {int(self.gate.hp)}/{self.gate.max_hp}",
                    True, (200, 150, 100))
            else:
                gate_text = font.render("Gate BREACHED!", True, (255, 100, 100))
            surface.blit(gate_text,
                         (SCREEN_WIDTH // 2 - gate_text.get_width() // 2, y))
