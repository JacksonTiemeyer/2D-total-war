"""Battle scene - handles the real-time tactical combat."""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT,
    TEAM_COLORS, TEAM_COLORS_LIGHT, GREEN, DARK_GREEN, SAND, BROWN,
    BLACK, WHITE, GREY, GOLD, YELLOW,
)
from core.camera import Camera
from core.utils import distance, point_in_rect
from battle.squad import Squad, SquadState
from battle.general import General, DuelState


class BattleResult:
    ONGOING = "ongoing"
    PLAYER_WIN = "player_win"
    PLAYER_LOSS = "player_loss"


class BattleScene:
    def __init__(self, player_army, enemy_army):
        self.camera = Camera(BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT)
        self.camera.center_on(BATTLE_MAP_WIDTH / 2, BATTLE_MAP_HEIGHT / 2)

        self.player_squads = []
        self.enemy_squads = []
        self.player_generals = []
        self.enemy_generals = []
        self.all_squads = []
        self.all_generals = []

        self.result = BattleResult.ONGOING
        self.selected_squads = []
        self.selected_general = None
        self.selecting = False
        self.select_start = (0, 0)
        self.select_end = (0, 0)
        self.paused = False
        self.battle_timer = 0
        self.speed_multiplier = 1

        # Terrain features (simple rectangles for now)
        self.terrain = []
        self._generate_terrain()

        # Deploy armies
        self._deploy_armies(player_army, enemy_army)

    def _generate_terrain(self):
        """Generate some basic terrain features."""
        # A few hills and forests
        self.terrain.append({
            "type": "hill",
            "rect": (800, 600, 400, 200),
            "color": (80, 140, 60),
        })
        self.terrain.append({
            "type": "forest",
            "rect": (1800, 400, 300, 350),
            "color": (30, 90, 20),
        })
        self.terrain.append({
            "type": "hill",
            "rect": (1200, 1200, 350, 180),
            "color": (80, 140, 60),
        })
        self.terrain.append({
            "type": "forest",
            "rect": (500, 1100, 250, 300),
            "color": (30, 90, 20),
        })

    def _deploy_armies(self, player_army, enemy_army):
        """Position armies on opposite sides of the battlefield."""
        # Player deploys on the left side
        start_x = 300
        start_y = BATTLE_MAP_HEIGHT // 2 - 300
        spacing_y = 80

        for i, (unit_stats, count_unused) in enumerate(player_army.get("squads", [])):
            y = start_y + i * spacing_y
            squad = Squad(unit_stats, 0, start_x, y, facing_angle=0)
            self.player_squads.append(squad)

        # Player general
        gen_data = player_army.get("general")
        if gen_data:
            gen = General(gen_data["name"], gen_data["stats"], 0,
                          start_x - 50, BATTLE_MAP_HEIGHT // 2)
            self.player_generals.append(gen)

        # Enemy deploys on the right side
        start_x = BATTLE_MAP_WIDTH - 300
        start_y = BATTLE_MAP_HEIGHT // 2 - 300
        for i, (unit_stats, count_unused) in enumerate(enemy_army.get("squads", [])):
            y = start_y + i * spacing_y
            squad = Squad(unit_stats, 1, start_x, y, facing_angle=math.pi)
            self.enemy_squads.append(squad)

        gen_data = enemy_army.get("general")
        if gen_data:
            gen = General(gen_data["name"], gen_data["stats"], 1,
                          start_x + 50, BATTLE_MAP_HEIGHT // 2)
            self.enemy_generals.append(gen)

        self.all_squads = self.player_squads + self.enemy_squads
        self.all_generals = self.player_generals + self.enemy_generals

    def handle_event(self, event):
        self.camera.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_1:
                self.speed_multiplier = 1
            elif event.key == pygame.K_2:
                self.speed_multiplier = 2
            elif event.key == pygame.K_3:
                self.speed_multiplier = 4
            elif event.key == pygame.K_f:
                # Toggle fire at will for selected ranged squads
                for sq in self.selected_squads:
                    if sq.is_ranged:
                        sq.fire_at_will = not sq.fire_at_will

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                self._handle_left_click(event.pos)
            elif event.button == 3:  # Right click
                self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.selecting:
                self._finish_box_select(event.pos)

        if event.type == pygame.MOUSEMOTION and self.selecting:
            self.select_end = event.pos

    def _handle_left_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT

        if not shift:
            # Deselect all
            for sq in self.player_squads:
                sq.selected = False
            for g in self.player_generals:
                g.selected = False
            self.selected_squads = []
            self.selected_general = None

        # Check if clicking a general
        for g in self.player_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                g.selected = True
                self.selected_general = g
                return

        # Check if clicking a squad
        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                sq.selected = True
                if sq not in self.selected_squads:
                    self.selected_squads.append(sq)
                return

        # Start box select
        self.selecting = True
        self.select_start = pos
        self.select_end = pos

    def _finish_box_select(self, pos):
        self.selecting = False
        sx1, sy1 = self.camera.screen_to_world(*self.select_start)
        sx2, sy2 = self.camera.screen_to_world(*pos)
        min_x = min(sx1, sx2)
        min_y = min(sy1, sy2)
        max_x = max(sx1, sx2)
        max_y = max(sy1, sy2)

        # Only select if box is big enough (not just a click)
        if abs(pos[0] - self.select_start[0]) < 5:
            return

        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            cx, cy = sq.center
            if min_x <= cx <= max_x and min_y <= cy <= max_y:
                sq.selected = True
                if sq not in self.selected_squads:
                    self.selected_squads.append(sq)

        for g in self.player_generals:
            if not g.alive:
                continue
            if min_x <= g.x <= max_x and min_y <= g.y <= max_y:
                g.selected = True
                self.selected_general = g

    def _handle_right_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)

        # Check if right-clicking an enemy squad (attack order)
        target_squad = None
        for sq in self.enemy_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                target_squad = sq
                break

        # Check if right-clicking an enemy general (duel challenge)
        target_general = None
        for g in self.enemy_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                target_general = g
                break

        # Issue duel challenge
        if target_general and self.selected_general:
            self.selected_general.challenge_duel(target_general)
            return

        # Issue orders to selected squads
        if self.selected_squads:
            if target_squad:
                for sq in self.selected_squads:
                    sq.give_attack_order(target_squad)
            else:
                # Move order - spread squads out
                count = len(self.selected_squads)
                for i, sq in enumerate(self.selected_squads):
                    offset_y = (i - count / 2.0) * 60
                    sq.give_move_order(wx, wy + offset_y)

        # Move general
        if self.selected_general and not target_general:
            self.selected_general.give_move_order(wx, wy)

    def update(self):
        if self.paused:
            return

        for _ in range(self.speed_multiplier):
            self._tick()

        self.camera.update()
        self.battle_timer += 1

    def _tick(self):
        # Update squads
        for sq in self.all_squads:
            sq.update(self.all_squads)

        # Update generals
        for g in self.player_generals:
            g.update(self.player_squads, self.enemy_squads)
        for g in self.enemy_generals:
            g.update(self.enemy_squads, self.player_squads)

        # Simple enemy AI
        self._enemy_ai()

        # Check general deaths
        for g in self.all_generals:
            if not g.alive:
                if g.team == 0:
                    g.on_death(self.player_squads)
                else:
                    g.on_death(self.enemy_squads)
                self.all_generals.remove(g)

        # Clean up destroyed squads from selections
        self.selected_squads = [s for s in self.selected_squads if not s.is_destroyed]

        # Check victory/defeat
        player_alive = any(not sq.is_destroyed for sq in self.player_squads)
        enemy_alive = any(not sq.is_destroyed for sq in self.enemy_squads)
        if not enemy_alive and player_alive:
            self.result = BattleResult.PLAYER_WIN
        elif not player_alive and enemy_alive:
            self.result = BattleResult.PLAYER_LOSS
        elif not player_alive and not enemy_alive:
            self.result = BattleResult.PLAYER_LOSS  # mutual destruction = loss

    def _enemy_ai(self):
        """Simple AI: attack nearest player squad."""
        for sq in self.enemy_squads:
            if sq.is_destroyed or sq.state in (SquadState.ROUTED, SquadState.BROKEN):
                continue
            if sq.state != SquadState.IDLE:
                continue
            # Find nearest player squad
            best = None
            best_dist = float("inf")
            for psq in self.player_squads:
                if psq.is_destroyed:
                    continue
                d = distance(sq.x, sq.y, psq.x, psq.y)
                if d < best_dist:
                    best_dist = d
                    best = psq
            if best:
                sq.give_attack_order(best)

        # Enemy generals: challenge player generals or attack
        for g in self.enemy_generals:
            if not g.alive or g.duel_state == DuelState.ACTIVE:
                continue
            for pg in self.player_generals:
                if pg.alive and pg.duel_state == DuelState.NONE:
                    d = distance(g.x, g.y, pg.x, pg.y)
                    if d < 200:
                        g.challenge_duel(pg)
                        break
            else:
                # Move toward battle center
                if self.player_squads:
                    targets = [sq for sq in self.player_squads if not sq.is_destroyed]
                    if targets:
                        t = random.choice(targets)
                        g.give_move_order(t.x, t.y)

    def draw(self, surface):
        # Background
        surface.fill((90, 140, 60))

        # Grid (subtle)
        grid_size = 100
        for x in range(0, BATTLE_MAP_WIDTH, grid_size):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, BATTLE_MAP_HEIGHT)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)
        for y in range(0, BATTLE_MAP_HEIGHT, grid_size):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(BATTLE_MAP_WIDTH, y)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)

        # Terrain
        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            screen_pos = self.camera.world_to_screen(rx, ry)
            w = self.camera.scale(rw)
            h = self.camera.scale(rh)
            pygame.draw.rect(surface, t["color"], (*screen_pos, w, h))
            # Label
            if self.camera.zoom > 0.4:
                font = pygame.font.SysFont(None, 16)
                text = font.render(t["type"].title(), True, (200, 200, 200))
                surface.blit(text, (screen_pos[0] + 5, screen_pos[1] + 5))

        # Draw squads
        for sq in self.all_squads:
            if not sq.is_destroyed:
                sq.draw(surface, self.camera)

        # Draw generals
        for g in self.all_generals:
            g.draw(surface, self.camera)

        # Box select
        if self.selecting:
            sx = min(self.select_start[0], self.select_end[0])
            sy = min(self.select_start[1], self.select_end[1])
            sw = abs(self.select_end[0] - self.select_start[0])
            sh = abs(self.select_end[1] - self.select_start[1])
            select_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            select_surf.fill((100, 200, 100, 40))
            surface.blit(select_surf, (sx, sy))
            pygame.draw.rect(surface, (100, 200, 100), (sx, sy, sw, sh), 1)

        # HUD
        self._draw_hud(surface)

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 20)
        small_font = pygame.font.SysFont(None, 16)

        # Top bar
        bar_surf = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 160))
        surface.blit(bar_surf, (0, 0))

        # Battle timer
        minutes = self.battle_timer // (60 * 60)
        seconds = (self.battle_timer // 60) % 60
        timer_text = font.render(f"Battle: {minutes:02d}:{seconds:02d}", True, WHITE)
        surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 8))

        # Speed indicator
        speed_text = font.render(f"Speed: {self.speed_multiplier}x", True, YELLOW)
        surface.blit(speed_text, (SCREEN_WIDTH // 2 + 100, 8))

        # Pause indicator
        if self.paused:
            pause_text = font.render("PAUSED", True, YELLOW)
            surface.blit(pause_text, (SCREEN_WIDTH // 2 - 150, 8))

        # Army counts
        p_alive = sum(sq.alive_count for sq in self.player_squads)
        e_alive = sum(sq.alive_count for sq in self.enemy_squads)
        p_text = font.render(f"Your Army: {p_alive}", True, TEAM_COLORS_LIGHT[0])
        e_text = font.render(f"Enemy Army: {e_alive}", True, TEAM_COLORS_LIGHT[1])
        surface.blit(p_text, (10, 8))
        surface.blit(e_text, (SCREEN_WIDTH - e_text.get_width() - 10, 8))

        # Selected unit info panel
        if self.selected_squads:
            self._draw_selection_panel(surface, font, small_font)
        elif self.selected_general:
            self._draw_general_panel(surface, font, small_font)

        # Controls help
        help_y = SCREEN_HEIGHT - 24
        help_text = small_font.render(
            "[SPACE] Pause  [1/2/3] Speed  [F] Toggle Fire  [LMB] Select  [RMB] Order  [MMB] Pan  [Scroll] Zoom",
            True, (180, 180, 180))
        surface.blit(help_text, (10, help_y))

        # Victory/defeat banner
        if self.result != BattleResult.ONGOING:
            self._draw_result_banner(surface)

    def _draw_selection_panel(self, surface, font, small_font):
        panel_h = 80 + len(self.selected_squads) * 20
        panel_surf = pygame.Surface((280, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - panel_h - 30))

        y = SCREEN_HEIGHT - panel_h - 25
        header = font.render("Selected Units:", True, WHITE)
        surface.blit(header, (10, y))
        y += 22
        for sq in self.selected_squads:
            state_str = sq.state.upper()
            info = f"{sq.unit_stats.name}: {sq.alive_count}/{sq.initial_count} [{state_str}] Morale:{int(sq.morale)}%"
            text = small_font.render(info, True, TEAM_COLORS_LIGHT[sq.team])
            surface.blit(text, (15, y))
            y += 18

    def _draw_general_panel(self, surface, font, small_font):
        g = self.selected_general
        panel_surf = pygame.Surface((280, 100), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - 130))

        y = SCREEN_HEIGHT - 125
        header = font.render(f"{g.name} ({g.general_type})", True, GOLD)
        surface.blit(header, (10, y))
        y += 22
        hp = small_font.render(f"HP: {int(g.health)}/{int(g.max_health)}", True, WHITE)
        surface.blit(hp, (15, y))
        y += 18
        stats = small_font.render(
            f"ATK:{g.melee_attack} DEF:{g.melee_defense} Kills:{g.kills} Duels Won:{g.duels_won}",
            True, WHITE)
        surface.blit(stats, (15, y))
        y += 18
        if g.duel_state == DuelState.ACTIVE:
            duel_text = small_font.render(
                f"DUELING {g.duel_opponent.name}! Score: {g.duel_score}-{g.duel_opponent.duel_score}",
                True, GOLD)
            surface.blit(duel_text, (15, y))

    def _draw_result_banner(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))

        big_font = pygame.font.SysFont(None, 72)
        if self.result == BattleResult.PLAYER_WIN:
            text = big_font.render("VICTORY!", True, GOLD)
        else:
            text = big_font.render("DEFEAT!", True, (200, 50, 50))
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2,
                            SCREEN_HEIGHT // 2 - 50))

        font = pygame.font.SysFont(None, 28)
        sub = font.render("Press ENTER to continue", True, WHITE)
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                           SCREEN_HEIGHT // 2 + 30))
