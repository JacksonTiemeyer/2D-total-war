"""Battle scene - handles the real-time tactical combat."""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT,
    TEAM_COLORS, TEAM_COLORS_LIGHT, GREEN, DARK_GREEN, SAND, BROWN,
    BLACK, WHITE, GREY, GOLD, YELLOW, ORANGE,
    EXHAUSTION_MAX,
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

        # Terrain features
        self.terrain = []
        self._generate_terrain()

        # Deploy armies
        self._deploy_armies(player_army, enemy_army)

        # Wire up generals' enemy general references (for Challenge ability)
        for g in self.player_generals:
            g._all_enemy_generals = self.enemy_generals
        for g in self.enemy_generals:
            g._all_enemy_generals = self.player_generals

    def _generate_terrain(self):
        self.terrain.append({"type": "hill", "rect": (800, 600, 400, 200), "color": (80, 140, 60)})
        self.terrain.append({"type": "forest", "rect": (1800, 400, 300, 350), "color": (30, 90, 20)})
        self.terrain.append({"type": "hill", "rect": (1200, 1200, 350, 180), "color": (80, 140, 60)})
        self.terrain.append({"type": "forest", "rect": (500, 1100, 250, 300), "color": (30, 90, 20)})

    def _deploy_armies(self, player_army, enemy_army):
        start_x = 300
        start_y = BATTLE_MAP_HEIGHT // 2 - 300
        spacing_y = 80

        for i, (unit_stats, count_unused) in enumerate(player_army.get("squads", [])):
            y = start_y + i * spacing_y
            squad = Squad(unit_stats, 0, start_x, y, facing_angle=0)
            self.player_squads.append(squad)

        gen_data = player_army.get("general")
        if gen_data:
            gen = General(gen_data["name"], gen_data["stats"], 0,
                          start_x - 50, BATTLE_MAP_HEIGHT // 2)
            self.player_generals.append(gen)

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
                for sq in self.selected_squads:
                    if sq.is_ranged:
                        sq.fire_at_will = not sq.fire_at_will
            # Ability hotkeys: Q, W, E, R
            elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r):
                self._handle_ability_key(event.key)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.selecting:
                self._finish_box_select(event.pos)

        if event.type == pygame.MOUSEMOTION and self.selecting:
            self.select_end = event.pos

    def _handle_ability_key(self, key):
        """Activate general ability via Q/W/E/R hotkeys."""
        if not self.selected_general:
            return
        g = self.selected_general
        key_map = {pygame.K_q: 0, pygame.K_w: 1, pygame.K_e: 2, pygame.K_r: 3}
        index = key_map.get(key, -1)
        if index < 0:
            return
        friendly = self.player_squads if g.team == 0 else self.enemy_squads
        enemy = self.enemy_squads if g.team == 0 else self.player_squads
        g.activate_ability(index, friendly, enemy)

    def _handle_left_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT

        if not shift:
            for sq in self.player_squads:
                sq.selected = False
            for g in self.player_generals:
                g.selected = False
            self.selected_squads = []
            self.selected_general = None

        for g in self.player_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                g.selected = True
                self.selected_general = g
                return

        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                sq.selected = True
                if sq not in self.selected_squads:
                    self.selected_squads.append(sq)
                return

        self.selecting = True
        self.select_start = pos
        self.select_end = pos

    def _finish_box_select(self, pos):
        self.selecting = False
        sx1, sy1 = self.camera.screen_to_world(*self.select_start)
        sx2, sy2 = self.camera.screen_to_world(*pos)
        min_x, min_y = min(sx1, sx2), min(sy1, sy2)
        max_x, max_y = max(sx1, sx2), max(sy1, sy2)

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

        target_squad = None
        for sq in self.enemy_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                target_squad = sq
                break

        target_general = None
        for g in self.enemy_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                target_general = g
                break

        if target_general and self.selected_general:
            self.selected_general.challenge_duel(target_general)
            return

        if self.selected_squads:
            if target_squad:
                for sq in self.selected_squads:
                    sq.give_attack_order(target_squad)
            else:
                count = len(self.selected_squads)
                for i, sq in enumerate(self.selected_squads):
                    offset_y = (i - count / 2.0) * 60
                    sq.give_move_order(wx, wy + offset_y)

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
        for sq in self.all_squads:
            sq.update(self.all_squads)

        for g in self.player_generals:
            g.update(self.player_squads, self.enemy_squads)
        for g in self.enemy_generals:
            g.update(self.enemy_squads, self.player_squads)

        self._enemy_ai()

        # Track kills for XP
        for g in self.all_generals:
            if g.alive and g.kills > 0:
                # XP per kill
                new_kills = g.kills
                if not hasattr(g, '_prev_kills'):
                    g._prev_kills = 0
                gained = new_kills - g._prev_kills
                if gained > 0:
                    g.gain_xp(gained)
                    g._prev_kills = new_kills

        # Check general deaths
        dead_generals = [g for g in self.all_generals if not g.alive]
        for g in dead_generals:
            if g.team == 0:
                g.on_death(self.player_squads)
            else:
                g.on_death(self.enemy_squads)
            self.all_generals.remove(g)

        self.selected_squads = [s for s in self.selected_squads if not s.is_destroyed]

        player_alive = any(not sq.is_destroyed for sq in self.player_squads)
        enemy_alive = any(not sq.is_destroyed for sq in self.enemy_squads)
        if not enemy_alive and player_alive:
            self.result = BattleResult.PLAYER_WIN
        elif not player_alive and enemy_alive:
            self.result = BattleResult.PLAYER_LOSS
        elif not player_alive and not enemy_alive:
            self.result = BattleResult.PLAYER_LOSS

    def _enemy_ai(self):
        for sq in self.enemy_squads:
            if sq.is_destroyed or sq.state in (SquadState.ROUTED, SquadState.BROKEN):
                continue
            if sq.state != SquadState.IDLE:
                continue
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

        for g in self.enemy_generals:
            if not g.alive or g.duel_state == DuelState.ACTIVE:
                continue
            # Enemy generals auto-use abilities
            if g.available_abilities and random.random() < 0.02:
                ready = [i for i, a in enumerate(g.available_abilities) if a.ready]
                if ready:
                    idx = random.choice(ready)
                    g.activate_ability(idx, self.enemy_squads, self.player_squads)

            for pg in self.player_generals:
                if pg.alive and pg.duel_state == DuelState.NONE:
                    d = distance(g.x, g.y, pg.x, pg.y)
                    if d < 200:
                        g.challenge_duel(pg)
                        break
            else:
                if self.player_squads:
                    targets = [sq for sq in self.player_squads if not sq.is_destroyed]
                    if targets:
                        t = random.choice(targets)
                        g.give_move_order(t.x, t.y)

    def draw(self, surface):
        surface.fill((90, 140, 60))

        grid_size = 100
        for x in range(0, BATTLE_MAP_WIDTH, grid_size):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, BATTLE_MAP_HEIGHT)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)
        for y in range(0, BATTLE_MAP_HEIGHT, grid_size):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(BATTLE_MAP_WIDTH, y)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)

        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            screen_pos = self.camera.world_to_screen(rx, ry)
            w = self.camera.scale(rw)
            h = self.camera.scale(rh)
            pygame.draw.rect(surface, t["color"], (*screen_pos, w, h))
            if self.camera.zoom > 0.4:
                font = pygame.font.SysFont(None, 16)
                text = font.render(t["type"].title(), True, (200, 200, 200))
                surface.blit(text, (screen_pos[0] + 5, screen_pos[1] + 5))

        for sq in self.all_squads:
            if not sq.is_destroyed:
                sq.draw(surface, self.camera)

        for g in self.all_generals:
            g.draw(surface, self.camera)

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

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 20)
        small_font = pygame.font.SysFont(None, 16)

        # Top bar
        bar_surf = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 160))
        surface.blit(bar_surf, (0, 0))

        minutes = self.battle_timer // (60 * 60)
        seconds = (self.battle_timer // 60) % 60
        timer_text = font.render(f"Battle: {minutes:02d}:{seconds:02d}", True, WHITE)
        surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 8))

        speed_text = font.render(f"Speed: {self.speed_multiplier}x", True, YELLOW)
        surface.blit(speed_text, (SCREEN_WIDTH // 2 + 100, 8))

        if self.paused:
            pause_text = font.render("PAUSED", True, YELLOW)
            surface.blit(pause_text, (SCREEN_WIDTH // 2 - 150, 8))

        p_alive = sum(sq.alive_count for sq in self.player_squads)
        e_alive = sum(sq.alive_count for sq in self.enemy_squads)
        p_text = font.render(f"Your Army: {p_alive}", True, TEAM_COLORS_LIGHT[0])
        e_text = font.render(f"Enemy Army: {e_alive}", True, TEAM_COLORS_LIGHT[1])
        surface.blit(p_text, (10, 8))
        surface.blit(e_text, (SCREEN_WIDTH - e_text.get_width() - 10, 8))

        if self.selected_squads:
            self._draw_selection_panel(surface, font, small_font)
        elif self.selected_general:
            self._draw_general_panel(surface, font, small_font)

        help_y = SCREEN_HEIGHT - 24
        help_text = small_font.render(
            "[SPACE] Pause  [1/2/3] Speed  [F] Fire  [Q/W/E/R] Abilities  "
            "[LMB] Select  [RMB] Order  [MMB] Pan  [Scroll] Zoom",
            True, (180, 180, 180))
        surface.blit(help_text, (10, help_y))

        if self.result != BattleResult.ONGOING:
            self._draw_result_banner(surface)

    def _draw_selection_panel(self, surface, font, small_font):
        panel_h = 80 + len(self.selected_squads) * 35
        panel_surf = pygame.Surface((340, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - panel_h - 30))

        y = SCREEN_HEIGHT - panel_h - 25
        header = font.render("Selected Units:", True, WHITE)
        surface.blit(header, (10, y))
        y += 22
        for sq in self.selected_squads:
            state_str = sq.state.upper()
            info = (f"{sq.unit_stats.name}: {sq.alive_count}/{sq.initial_count} "
                    f"[{state_str}] Morale:{int(sq.morale)}%")
            text = small_font.render(info, True, TEAM_COLORS_LIGHT[sq.team])
            surface.blit(text, (15, y))
            y += 16
            # Second line: exhaustion + weapon stats
            ws = sq.unit_stats.weapon_strength
            ap = sq.unit_stats.armor_penetration
            extra = f"  {sq.exhaustion_display} | WS:{ws} AP:{ap}%"
            if sq.unit_stats.ranged_strength > 0:
                extra += f" RS:{sq.unit_stats.ranged_strength} RAP:{sq.unit_stats.ranged_armor_penetration}%"
            if sq.is_braced:
                extra += " [BRACED]"
            text2 = small_font.render(extra, True, (160, 160, 160))
            surface.blit(text2, (15, y))
            y += 19

    def _draw_general_panel(self, surface, font, small_font):
        g = self.selected_general
        num_abilities = len(g.available_abilities)
        panel_h = 120 + num_abilities * 22
        panel_surf = pygame.Surface((340, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - panel_h - 30))

        y = SCREEN_HEIGHT - panel_h - 25
        header = font.render(f"{g.name} ({g.general_type}) Lv{g.level}", True, GOLD)
        surface.blit(header, (10, y))
        y += 22
        hp = small_font.render(f"HP: {int(g.health)}/{int(g.max_health)}  XP to next: {g.xp_to_next}", True, WHITE)
        surface.blit(hp, (15, y))
        y += 18
        stats = small_font.render(
            f"ATK:{g.melee_attack} DEF:{g.melee_defense} WS:{g.unit_stats.weapon_strength} "
            f"AP:{g.unit_stats.armor_penetration}%",
            True, WHITE)
        surface.blit(stats, (15, y))
        y += 18
        kills_text = small_font.render(
            f"Kills:{g.kills} Duels Won:{g.duels_won}", True, WHITE)
        surface.blit(kills_text, (15, y))
        y += 18

        if g.duel_state == DuelState.ACTIVE:
            duel_text = small_font.render(
                f"DUELING {g.duel_opponent.name}! Score: {g.duel_score}-{g.duel_opponent.duel_score}",
                True, GOLD)
            surface.blit(duel_text, (15, y))
            y += 18

        # Abilities
        y += 4
        keys = ["Q", "W", "E", "R"]
        for i, ability in enumerate(g.available_abilities):
            if i >= 4:
                break
            cd_text = ""
            if not ability.ready:
                cd_secs = ability.cooldown // 60
                cd_text = f" ({cd_secs}s)"
            color = WHITE if ability.ready else (100, 100, 100)
            text = small_font.render(
                f"[{keys[i]}] {ability.name}{cd_text} - {ability.description[:40]}",
                True, color)
            surface.blit(text, (15, y))
            y += 20

        # Show locked abilities
        for i, ability in enumerate(g.abilities):
            if ability.level_required > g.level:
                text = small_font.render(
                    f"  Lv{ability.level_required}: {ability.name} (Locked)",
                    True, (80, 80, 80))
                surface.blit(text, (15, y))
                y += 18

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
