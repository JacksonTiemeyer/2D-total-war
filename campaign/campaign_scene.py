"""Campaign map scene - Mount & Blade Warband style overworld."""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT,
    TEAM_COLORS, TEAM_COLORS_LIGHT,
    WHITE, BLACK, GREY, DARK_GREY, GOLD, YELLOW,
    DARK_GREEN, BROWN, SAND, LIGHT_BLUE,
    INCOME_PER_SETTLEMENT,
)
from core.camera import Camera
from core.utils import distance, point_in_rect
from campaign.settlement import Settlement, SettlementType
from campaign.army import (
    Army, create_default_player_army, create_enemy_army,
)
from data.unit_types import ALL_RECRUITABLE, GENERAL_ROSTER
from campaign.faction import FACTION_ROSTER
from campaign.diplomacy import DiplomacyManager, DiplomacyState


class CampaignScene:
    def __init__(self):
        self.camera = Camera(CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT)
        self.camera.center_on(CAMPAIGN_MAP_WIDTH / 2, CAMPAIGN_MAP_HEIGHT / 2)

        self.turn = 1
        self.player_army = create_default_player_army()
        self.armies = [self.player_army]
        self.settlements = []
        self.selected_settlement = None
        self.show_recruitment = False
        self.show_diplomacy = False
        self.recruitment_settlement = None
        self.pending_battle = None  # (player_army, enemy_army) tuple

        # Faction & diplomacy
        self.factions = FACTION_ROSTER[:]
        self.diplomacy = DiplomacyManager(self.factions)
        # Start player at war with Iron Empire (team 1)
        self.diplomacy.declare_war(0, 1)

        self._generate_world()

    def _generate_world(self):
        """Generate a Warband-style campaign map with settlements and enemies."""
        # Settlements
        settlement_data = [
            # Player (team 0)
            ("Ironhold", 300, 300, SettlementType.CASTLE, 0),
            ("Millbrook", 600, 200, SettlementType.VILLAGE, 0),
            ("King's Landing", 500, 600, SettlementType.TOWN, 0),
            ("Brightwater", 400, 1100, SettlementType.TOWN, 0),
            # Iron Empire (team 1)
            ("Thornkeep", 1600, 600, SettlementType.CASTLE, 1),
            ("Ashvale", 1800, 400, SettlementType.VILLAGE, 1),
            ("Blackspire", 2000, 700, SettlementType.TOWN, 1),
            ("Dragonrest", 1900, 1100, SettlementType.CASTLE, 1),
            # Forest Alliance (team 2)
            ("Greenfield", 900, 700, SettlementType.TOWN, 2),
            ("Willowmere", 800, 1000, SettlementType.VILLAGE, 2),
            ("Stormwatch", 1200, 900, SettlementType.CASTLE, 2),
            # Contested / Desert Raiders (team 3)
            ("Dusthaven", 1400, 300, SettlementType.TOWN, 3),
            ("Shadowfen", 1600, 1000, SettlementType.VILLAGE, 3),
            # Neutral
            ("Redwall", 1100, 400, SettlementType.CASTLE, None),
            ("Crossroads", 1000, 600, SettlementType.VILLAGE, None),
        ]
        for name, x, y, stype, owner in settlement_data:
            self.settlements.append(Settlement(name, x, y, owner, stype))

        # Iron Empire armies (team 1)
        for name, x, y in [("Lord Varro's Host", 1500, 500),
                            ("The Iron Band", 1800, 300),
                            ("Baron Thorne's Guard", 2000, 500)]:
            army = create_enemy_army(name, 1, x, y, random.randint(2, 3))
            self.armies.append(army)

        # Forest Alliance armies (team 2)
        for name, x, y in [("Ser Aldric's Company", 900, 800),
                            ("The Green Wardens", 1100, 950)]:
            army = create_enemy_army(name, 2, x, y, random.randint(1, 2))
            self.armies.append(army)

        # Desert Raiders armies (team 3)
        for name, x, y in [("The Red Wolves", 1400, 350),
                            ("Sand Vipers", 1550, 1050)]:
            army = create_enemy_army(name, 3, x, y, random.randint(1, 3))
            self.armies.append(army)

    def handle_event(self, event):
        if self.show_recruitment:
            return self._handle_recruitment_event(event)
        if self.show_diplomacy:
            return self._handle_diplomacy_event(event)

        self.camera.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._end_turn()
            elif event.key == pygame.K_r:
                # Open recruitment if near a friendly settlement
                self._try_open_recruitment()
            elif event.key == pygame.K_g:
                # Cycle general type
                self._cycle_general()
            elif event.key == pygame.K_d:
                self.show_diplomacy = True
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self._save_game()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                self._handle_right_click(event.pos)

        return None  # no scene transition

    def _handle_left_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)

        # Check HUD buttons first (bottom area)
        if pos[1] > SCREEN_HEIGHT - 40:
            # End turn button area
            if pos[0] > SCREEN_WIDTH - 120:
                self._end_turn()
                return
            # Recruit button
            if SCREEN_WIDTH - 250 < pos[0] < SCREEN_WIDTH - 130:
                self._try_open_recruitment()
                return

        # Deselect
        self.selected_settlement = None
        self.player_army.selected = False

        # Check settlements
        for s in self.settlements:
            s.selected = False
            if distance(wx, wy, s.x, s.y) < 30:
                s.selected = True
                self.selected_settlement = s
                return

        # Check player army
        if distance(wx, wy, self.player_army.x, self.player_army.y) < 20:
            self.player_army.selected = True

    def _handle_right_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)

        # Move player army
        self.player_army.give_move_order(wx, wy)

    def _try_open_recruitment(self):
        for s in self.settlements:
            if s.owner == 0 and distance(
                    self.player_army.x, self.player_army.y, s.x, s.y) < 60:
                self.show_recruitment = True
                self.recruitment_settlement = s
                return

    def _handle_recruitment_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_recruitment = False
                return None
            # Number keys to recruit
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                self._recruit_unit(idx)
            # D + number to disband
            if event.key == pygame.K_d:
                pass  # handled with mouse below

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check recruitment buttons
            mx, my = event.pos
            panel_x = SCREEN_WIDTH // 2 - 200
            panel_y = 100

            # Available recruits
            for i, unit in enumerate(self.recruitment_settlement.available_recruits):
                btn_y = panel_y + 60 + i * 35
                if point_in_rect(mx, my, panel_x + 10, btn_y, 380, 30):
                    self._recruit_unit(i)
                    return None

            # Disband buttons (current army)
            disband_y = panel_y + 60 + len(self.recruitment_settlement.available_recruits) * 35 + 50
            for i in range(len(self.player_army.squads)):
                btn_y = disband_y + i * 25
                if point_in_rect(mx, my, panel_x + 340, btn_y, 50, 20):
                    self.player_army.remove_squad(i)
                    return None

            # Close button
            if point_in_rect(mx, my, panel_x + 350, panel_y, 30, 30):
                self.show_recruitment = False

        return None

    def _recruit_unit(self, index):
        if not self.recruitment_settlement:
            return
        recruits = self.recruitment_settlement.available_recruits
        if index >= len(recruits):
            return
        unit = recruits[index]
        if self.player_army.gold >= unit.cost:
            self.player_army.gold -= unit.cost
            self.player_army.add_squad(unit)
            recruits.pop(index)

    def _cycle_general(self):
        """Cycle through general types."""
        current = self.player_army.general_stats
        idx = GENERAL_ROSTER.index(current) if current in GENERAL_ROSTER else 0
        idx = (idx + 1) % len(GENERAL_ROSTER)
        self.player_army.general_stats = GENERAL_ROSTER[idx]

    def _handle_diplomacy_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_diplomacy = False
                return None
            # Number keys to interact with factions
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                non_player = [f for f in self.factions if not f.is_player]
                if idx < len(non_player):
                    target = non_player[idx]
                    state = self.diplomacy.get_state(0, target.team)
                    if state == DiplomacyState.WAR:
                        # Try peace
                        if self.diplomacy.propose_peace(0, target.team):
                            pass  # peace accepted
                    elif state in (DiplomacyState.FRIENDLY,):
                        # Try alliance
                        self.diplomacy.propose_alliance(0, target.team)
                    elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                        # Declare war
                        self.diplomacy.declare_war(0, target.team)
        return None

    def _end_turn(self):
        self.turn += 1

        # Income from settlements
        for s in self.settlements:
            if s.owner == 0:
                self.player_army.gold += s.income

        # Pay upkeep
        self.player_army.gold -= self.player_army.upkeep

        # Refresh recruitment pools
        for s in self.settlements:
            s.refresh_recruits()

        # AI diplomacy
        for f in self.factions:
            if not f.is_player:
                self.diplomacy.ai_diplomacy_tick(f, self.factions)

        # Move enemy armies (faction-aware AI)
        for army in self.armies:
            if army.is_player:
                continue
            # Find enemies of this army's faction
            enemies = [a for a in self.armies
                       if a.team != army.team and
                       self.diplomacy.are_at_war(army.team, a.team)]
            if enemies and random.random() < 0.6:
                # Move toward nearest enemy
                nearest = min(enemies, key=lambda e: distance(army.x, army.y, e.x, e.y))
                army.give_move_order(
                    nearest.x + random.randint(-50, 50),
                    nearest.y + random.randint(-50, 50),
                )
            else:
                # Patrol
                army.give_move_order(
                    army.x + random.randint(-100, 100),
                    army.y + random.randint(-100, 100),
                )

        # Move all armies
        for _ in range(30):
            for army in self.armies:
                army.update()

        # AI army battles (auto-resolve)
        self._resolve_ai_battles()

        # Capture unowned/enemy settlements when nearby
        for s in self.settlements:
            for army in self.armies:
                if distance(army.x, army.y, s.x, s.y) < 40:
                    if s.owner != army.team:
                        if self.diplomacy.are_at_war(army.team, s.owner if s.owner is not None else -1):
                            if army.army_strength > s.garrison_strength:
                                s.owner = army.team

    def _resolve_ai_battles(self):
        """Auto-resolve battles between AI armies that collide."""
        to_remove = []
        checked = set()
        for a1 in self.armies:
            if a1.is_player or a1 in to_remove:
                continue
            for a2 in self.armies:
                if a2.is_player or a2 is a1 or a2 in to_remove:
                    continue
                pair = (id(a1), id(a2))
                if pair in checked or (id(a2), id(a1)) in checked:
                    continue
                checked.add(pair)
                if (a1.team != a2.team and
                        self.diplomacy.are_at_war(a1.team, a2.team) and
                        distance(a1.x, a1.y, a2.x, a2.y) < 30):
                    # Auto-resolve: stronger army wins, both take losses
                    if a1.army_strength >= a2.army_strength:
                        # a1 wins - lose 20-40% soldiers
                        for sq in a1.squads:
                            loss = int(sq.current_count * random.uniform(0.1, 0.3))
                            sq.current_count = max(1, sq.current_count - loss)
                        to_remove.append(a2)
                    else:
                        for sq in a2.squads:
                            loss = int(sq.current_count * random.uniform(0.1, 0.3))
                            sq.current_count = max(1, sq.current_count - loss)
                        to_remove.append(a1)
        for army in to_remove:
            if army in self.armies:
                self.armies.remove(army)

    def _save_game(self):
        from core.save_system import save_campaign
        from core.audio import get_audio
        save_campaign(self)
        get_audio().play("save")
        self._save_notification_timer = 120  # show "Saved!" for 2 seconds

    def update(self):
        self.camera.update()
        self.player_army.update()
        # Tick save notification
        if hasattr(self, '_save_notification_timer') and self._save_notification_timer > 0:
            self._save_notification_timer -= 1

        # Check for collisions with enemy armies -> trigger battle (only if at war)
        for army in self.armies:
            if army.is_player or army.team == 0:
                continue
            if not self.diplomacy.are_at_war(0, army.team):
                continue
            if distance(self.player_army.x, self.player_army.y,
                        army.x, army.y) < 25:
                self.pending_battle = (self.player_army, army)
                return

    def get_pending_battle(self):
        battle = self.pending_battle
        self.pending_battle = None
        return battle

    def remove_army(self, army):
        if army in self.armies:
            self.armies.remove(army)

    def draw(self, surface):
        # Background - parchment style
        surface.fill((180, 165, 130))

        # Map border
        tl = self.camera.world_to_screen(0, 0)
        br = self.camera.world_to_screen(CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT)
        pygame.draw.rect(surface, (140, 125, 90),
                         (tl[0], tl[1], br[0] - tl[0], br[1] - tl[1]), 3)

        # Terrain decorations
        self._draw_terrain(surface)

        # Roads between settlements (simple lines)
        for i, s1 in enumerate(self.settlements):
            for s2 in self.settlements[i + 1:]:
                if distance(s1.x, s1.y, s2.x, s2.y) < 500:
                    p1 = self.camera.world_to_screen(s1.x, s1.y)
                    p2 = self.camera.world_to_screen(s2.x, s2.y)
                    pygame.draw.line(surface, (150, 135, 100), p1, p2, max(1, self.camera.scale(2)))

        # Settlements
        for s in self.settlements:
            s.draw(surface, self.camera)

        # Armies
        for army in self.armies:
            army.draw(surface, self.camera)

        # HUD
        self._draw_hud(surface)

        # Recruitment overlay
        if self.show_recruitment:
            self._draw_recruitment(surface)

        # Diplomacy overlay
        if self.show_diplomacy:
            self._draw_diplomacy(surface)

    def _draw_terrain(self, surface):
        """Draw decorative terrain features."""
        # Some green patches (forests)
        forests = [(200, 400, 120), (1000, 200, 80), (700, 800, 100),
                   (1500, 900, 90), (1900, 300, 70)]
        for fx, fy, fr in forests:
            sx, sy = self.camera.world_to_screen(fx, fy)
            r = self.camera.scale(fr)
            forest_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(forest_surf, (60, 100, 40, 80), (r, r), r)
            surface.blit(forest_surf, (sx - r, sy - r))

        # Mountains
        mountains = [(1100, 150, 60), (1800, 600, 50), (300, 900, 45)]
        for mx, my, mr in mountains:
            sx, sy = self.camera.world_to_screen(mx, my)
            r = self.camera.scale(mr)
            # Triangle
            pts = [(sx, sy - r), (sx - r, sy + r // 2), (sx + r, sy + r // 2)]
            pygame.draw.polygon(surface, (120, 110, 90), pts)
            pygame.draw.polygon(surface, (160, 150, 120), pts, 2)
            # Snow cap
            cap = [(sx, sy - r), (sx - r // 3, sy - r // 3), (sx + r // 3, sy - r // 3)]
            pygame.draw.polygon(surface, WHITE, cap)

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 22)
        small_font = pygame.font.SysFont(None, 16)

        # Top bar
        bar = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 180))
        surface.blit(bar, (0, 0))

        # Turn counter
        turn_text = font.render(f"Turn {self.turn}", True, WHITE)
        surface.blit(turn_text, (SCREEN_WIDTH // 2 - turn_text.get_width() // 2, 8))

        # Gold
        gold_text = font.render(f"Gold: {self.player_army.gold}", True, GOLD)
        surface.blit(gold_text, (10, 8))

        # Army info
        army_text = font.render(
            f"Army: {self.player_army.total_soldiers} soldiers | "
            f"Strength: {self.player_army.army_strength} | "
            f"Upkeep: {self.player_army.upkeep}/turn",
            True, WHITE)
        surface.blit(army_text, (150, 8))

        # Bottom bar
        bottom = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        bottom.fill((0, 0, 0, 180))
        surface.blit(bottom, (0, SCREEN_HEIGHT - 40))

        # Controls
        ctrl_text = small_font.render(
            "[RMB] Move  [R] Recruit  [G] General  [D] Diplomacy  [Ctrl+S] Save  [ENTER] End Turn",
            True, (180, 180, 180))
        surface.blit(ctrl_text, (10, SCREEN_HEIGHT - 30))

        # Save notification
        if hasattr(self, '_save_notification_timer') and self._save_notification_timer > 0:
            save_text = font.render("Game Saved!", True, (100, 255, 100))
            surface.blit(save_text, (SCREEN_WIDTH // 2 - save_text.get_width() // 2, 45))

        # End turn button
        btn_rect = (SCREEN_WIDTH - 120, SCREEN_HEIGHT - 36, 110, 32)
        pygame.draw.rect(surface, (60, 120, 60), btn_rect)
        pygame.draw.rect(surface, WHITE, btn_rect, 1)
        btn_text = font.render("End Turn", True, WHITE)
        surface.blit(btn_text, (btn_rect[0] + 20, btn_rect[1] + 7))

        # Recruit button
        btn_rect2 = (SCREEN_WIDTH - 250, SCREEN_HEIGHT - 36, 120, 32)
        pygame.draw.rect(surface, (60, 60, 120), btn_rect2)
        pygame.draw.rect(surface, WHITE, btn_rect2, 1)
        btn_text2 = font.render("Recruit [R]", True, WHITE)
        surface.blit(btn_text2, (btn_rect2[0] + 12, btn_rect2[1] + 7))

        # Selected settlement info
        if self.selected_settlement:
            self._draw_settlement_info(surface, font, small_font)

        # Selected army info
        if self.player_army.selected:
            panel = pygame.Surface((280, 300), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 180))
            surface.blit(panel, (SCREEN_WIDTH - 290, 45))
            self.player_army.draw_info_panel(
                surface, SCREEN_WIDTH - 280, 50, font, small_font)

    def _draw_settlement_info(self, surface, font, small_font):
        s = self.selected_settlement
        panel = pygame.Surface((250, 120), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        surface.blit(panel, (SCREEN_WIDTH - 260, 45))

        x, y = SCREEN_WIDTH - 250, 50
        name_text = font.render(f"{s.name} ({s.settlement_type.title()})", True, WHITE)
        surface.blit(name_text, (x, y))
        y += 22
        faction_names = {f.team: f.name for f in self.factions}
        owner = faction_names.get(s.owner, "Neutral") if s.owner is not None else "Neutral"
        if s.owner == 0:
            owner = "Yours"
        owner_text = small_font.render(f"Owner: {owner}", True, WHITE)
        surface.blit(owner_text, (x, y))
        y += 18
        income_text = small_font.render(f"Income: {s.income}/turn", True, GOLD)
        surface.blit(income_text, (x, y))
        y += 18
        garrison_text = small_font.render(f"Garrison: {s.garrison_strength}", True, WHITE)
        surface.blit(garrison_text, (x, y))

    def _draw_recruitment(self, surface):
        if not self.recruitment_settlement:
            return
        s = self.recruitment_settlement

        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = 420, 500
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 100
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = pygame.font.SysFont(None, 24)
        small = pygame.font.SysFont(None, 18)

        # Title
        title = font.render(f"Recruit at {s.name}", True, GOLD)
        surface.blit(title, (panel_x + 10, panel_y + 10))

        # Gold
        gold = font.render(f"Gold: {self.player_army.gold}", True, GOLD)
        surface.blit(gold, (panel_x + 10, panel_y + 35))

        # Close button
        pygame.draw.rect(surface, (150, 50, 50), (panel_x + panel_w - 35, panel_y + 5, 30, 25))
        close = small.render("X", True, WHITE)
        surface.blit(close, (panel_x + panel_w - 25, panel_y + 8))

        # Available recruits
        y = panel_y + 60
        header = small.render("Available Recruits (click to hire):", True, WHITE)
        surface.blit(header, (panel_x + 10, y))
        y += 22

        for i, unit in enumerate(s.available_recruits):
            can_afford = self.player_army.gold >= unit.cost
            color = WHITE if can_afford else (120, 120, 120)
            btn_color = (50, 80, 50) if can_afford else (50, 50, 50)
            pygame.draw.rect(surface, btn_color, (panel_x + 10, y, 380, 28))
            pygame.draw.rect(surface, GREY, (panel_x + 10, y, 380, 28), 1)
            text = small.render(
                f"[{i+1}] {unit.name} ({unit.squad_size} soldiers) - {unit.cost}g | "
                f"ATK:{unit.melee_attack} DEF:{unit.melee_defense}"
                f"{' RNG:'+str(unit.ranged_attack) if unit.ranged_attack else ''}",
                True, color)
            surface.blit(text, (panel_x + 15, y + 5))
            y += 35

        # Current army
        y += 15
        header2 = small.render("Your Army:", True, WHITE)
        surface.blit(header2, (panel_x + 10, y))
        y += 22

        for i, csq in enumerate(self.player_army.squads):
            stats = csq.unit_stats
            count_str = f"{csq.current_count}/{csq.max_count}" if csq.is_understrength else str(csq.current_count)
            text = small.render(f"  {stats.name} ({count_str}) - Upkeep: {stats.upkeep}",
                                True, WHITE)
            surface.blit(text, (panel_x + 10, y))
            # Disband button
            pygame.draw.rect(surface, (120, 40, 40), (panel_x + 340, y, 50, 18))
            disband = small.render("Drop", True, WHITE)
            surface.blit(disband, (panel_x + 345, y + 1))
            y += 25

        # Footer
        footer = small.render("[ESC] Close  |  Click unit to recruit  |  Click 'Drop' to disband",
                              True, (150, 150, 150))
        surface.blit(footer, (panel_x + 10, panel_y + panel_h - 25))

    def _draw_diplomacy(self, surface):
        """Draw diplomacy overview panel."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 500, 400
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 100
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = pygame.font.SysFont(None, 28)
        small = pygame.font.SysFont(None, 20)
        tiny = pygame.font.SysFont(None, 16)

        title = font.render("Diplomacy", True, GOLD)
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

        y = panel_y + 50
        non_player = [f for f in self.factions if not f.is_player]

        state_colors = {
            DiplomacyState.WAR: (220, 50, 50),
            DiplomacyState.HOSTILE: (200, 130, 50),
            DiplomacyState.NEUTRAL: (180, 180, 180),
            DiplomacyState.FRIENDLY: (100, 200, 100),
            DiplomacyState.ALLIED: (50, 150, 255),
        }

        for i, faction in enumerate(non_player):
            rel = self.diplomacy.get_relation(0, faction.team)
            state = self.diplomacy.get_state(0, faction.team)
            color = state_colors.get(state, WHITE)

            # Faction name and relation
            team_color = TEAM_COLORS.get(faction.team, GREY)
            name_text = small.render(f"[{i+1}] {faction.name}", True, team_color)
            surface.blit(name_text, (panel_x + 20, y))

            # State
            state_text = small.render(f"{state.upper()} ({rel:+d})", True, color)
            surface.blit(state_text, (panel_x + 250, y))

            # Personality
            pers = tiny.render(f"({faction.personality})", True, (120, 120, 120))
            surface.blit(pers, (panel_x + 400, y + 2))

            y += 22

            # Action hint
            if state == DiplomacyState.WAR:
                hint = tiny.render(f"  Press [{i+1}] to propose peace", True, (150, 150, 150))
            elif state == DiplomacyState.FRIENDLY:
                hint = tiny.render(f"  Press [{i+1}] to propose alliance", True, (150, 150, 150))
            elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                hint = tiny.render(f"  Press [{i+1}] to declare war", True, (150, 150, 150))
            else:
                hint = tiny.render(f"  Allied", True, (100, 200, 255))
            surface.blit(hint, (panel_x + 30, y))
            y += 22

            # Settlements owned
            owned = sum(1 for s in self.settlements if s.owner == faction.team)
            armies_count = sum(1 for a in self.armies if a.team == faction.team)
            info = tiny.render(
                f"  Settlements: {owned}  |  Armies: {armies_count}",
                True, (140, 140, 140))
            surface.blit(info, (panel_x + 30, y))
            y += 30

        # Footer
        footer = tiny.render("[ESC] Close  |  Press number to interact", True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))
