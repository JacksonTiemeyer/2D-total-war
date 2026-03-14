"""Campaign map scene - Mount & Blade Warband style overworld.

Features:
- Real-time campaign with pause/speed controls (B1)
- 35 settlements across 8 factions (B4)
- Faction territory borders with colored overlays (B4)
- Campaign fog of war with vision radius (B13)
- Improved HUD with day counter, speed, notifications (C2)
"""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT,
    CAMPAIGN_TICKS_PER_DAY,
    CAMPAIGN_SPEED_PAUSED, CAMPAIGN_SPEED_1X, CAMPAIGN_SPEED_2X, CAMPAIGN_SPEED_3X,
    CAMPAIGN_VISION_RADIUS, CAMPAIGN_SETTLEMENT_VISION, CAMPAIGN_FOG_ALPHA,
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

        # Real-time campaign state (B1)
        self.day = 1
        self.day_ticks = 0  # ticks within current day
        self.campaign_speed = CAMPAIGN_SPEED_1X
        self.paused = False

        # Legacy turn counter (for save compat)
        self.turn = 1

        self.player_army = create_default_player_army()
        self.armies = [self.player_army]
        self.settlements = []
        self.selected_settlement = None
        self.show_recruitment = False
        self.show_diplomacy = False
        self.recruitment_settlement = None
        self.pending_battle = None  # (player_army, enemy_army) tuple

        # Notification feed (C2)
        self.notifications = []  # list of (text, timer)
        self.NOTIFICATION_DURATION = 300  # 5 seconds at 60fps

        # Faction & diplomacy
        self.factions = FACTION_ROSTER[:]
        self.diplomacy = DiplomacyManager(self.factions)
        # Start player at war with Iron Empire (team 1)
        self.diplomacy.declare_war(0, 1)

        # Fog of war state (B13)
        self._fog_surface = None
        self._fog_needs_update = True

        # Territory border cache
        self._territory_surface = None
        self._territory_needs_update = True

        # AI tick timer (replaces per-turn AI)
        self._ai_tick_timer = 0
        self._ai_diplomacy_timer = 0
        self._income_timer = 0

        self._generate_world()
        self._add_notification("Your campaign begins. You are at war with the Iron Empire!")

    def _add_notification(self, text):
        """Add a notification to the feed."""
        self.notifications.append((text, self.NOTIFICATION_DURATION))

    def _generate_world(self):
        """Generate campaign map with 35 settlements across 8 factions."""
        # B4: Expanded settlement data - 35 settlements
        settlement_data = [
            # Player (team 0) - 4 settlements, western region
            ("Ironhold", 350, 400, SettlementType.CASTLE, 0),
            ("Millbrook", 500, 250, SettlementType.VILLAGE, 0),
            ("King's Landing", 550, 600, SettlementType.TOWN, 0),
            ("Brightwater", 300, 700, SettlementType.VILLAGE, 0),

            # Iron Empire (team 1) - 5 settlements, east-central
            ("Thornkeep", 2200, 700, SettlementType.CASTLE, 1),
            ("Ashvale", 2400, 500, SettlementType.VILLAGE, 1),
            ("Blackspire", 2600, 800, SettlementType.TOWN, 1),
            ("Dragonrest", 2500, 1100, SettlementType.CASTLE, 1),
            ("Iron Bastion", 2300, 350, SettlementType.TOWN, 1),

            # Forest Alliance (team 2) - 4 settlements, central forests
            ("Greenfield", 1100, 800, SettlementType.TOWN, 2),
            ("Willowmere", 900, 1000, SettlementType.VILLAGE, 2),
            ("Stormwatch", 1300, 1000, SettlementType.CASTLE, 2),
            ("Mosshollow", 1000, 600, SettlementType.VILLAGE, 2),

            # Desert Raiders (team 3) - 4 settlements, southeast
            ("Dusthaven", 2800, 1800, SettlementType.TOWN, 3),
            ("Shadowfen", 3000, 2000, SettlementType.VILLAGE, 3),
            ("Sandspire", 3200, 1600, SettlementType.CASTLE, 3),
            ("Oasis Hold", 2600, 2000, SettlementType.VILLAGE, 3),

            # Northern Holds (team 4) - 4 settlements, north
            ("Frosthaven", 1600, 200, SettlementType.CASTLE, 4),
            ("Icewatch", 1800, 350, SettlementType.TOWN, 4),
            ("Snowpeak", 1400, 350, SettlementType.VILLAGE, 4),
            ("Winterhold", 2000, 200, SettlementType.VILLAGE, 4),

            # Maritime Republic (team 5) - 4 settlements, south coast
            ("Portmere", 1200, 2400, SettlementType.TOWN, 5),
            ("Tidecrest", 1500, 2600, SettlementType.CASTLE, 5),
            ("Saltmoor", 900, 2200, SettlementType.VILLAGE, 5),
            ("Harbor Gate", 1700, 2400, SettlementType.TOWN, 5),

            # Steppe Horde (team 6) - 4 settlements, far east
            ("Khan's Camp", 3400, 800, SettlementType.CASTLE, 6),
            ("Windrun", 3200, 600, SettlementType.VILLAGE, 6),
            ("Hoofmark", 3500, 1100, SettlementType.TOWN, 6),
            ("Eagle's Nest", 3600, 500, SettlementType.VILLAGE, 6),

            # Holy Order (team 7) - 3 settlements, central-south
            ("Temple Mount", 1800, 1600, SettlementType.CASTLE, 7),
            ("Pilgrim's Rest", 2000, 1800, SettlementType.TOWN, 7),
            ("Shrine of Dawn", 1600, 1800, SettlementType.VILLAGE, 7),

            # Free Cities (team 8) - 3 settlements, scattered
            ("Tradegate", 800, 1600, SettlementType.TOWN, 8),
            ("Coinmarket", 1400, 1400, SettlementType.TOWN, 8),
            ("Freeport", 600, 1200, SettlementType.VILLAGE, 8),
        ]
        for name, x, y, stype, owner in settlement_data:
            self.settlements.append(Settlement(name, x, y, owner, stype))

        # B4: Armies for all factions (3-5 per faction)
        # Iron Empire armies (team 1)
        for name, x, y in [("Lord Varro's Host", 2100, 600),
                            ("The Iron Band", 2400, 400),
                            ("Baron Thorne's Guard", 2600, 700),
                            ("Imperial Vanguard", 2300, 1000)]:
            army = create_enemy_army(name, 1, x, y, random.randint(2, 3))
            self.armies.append(army)

        # Forest Alliance armies (team 2)
        for name, x, y in [("Ser Aldric's Company", 1000, 750),
                            ("The Green Wardens", 1200, 950),
                            ("Deepwood Rangers", 900, 850)]:
            army = create_enemy_army(name, 2, x, y, random.randint(1, 2))
            self.armies.append(army)

        # Desert Raiders armies (team 3)
        for name, x, y in [("The Red Wolves", 2900, 1900),
                            ("Sand Vipers", 3100, 1700),
                            ("Dune Stalkers", 2700, 1850)]:
            army = create_enemy_army(name, 3, x, y, random.randint(1, 3))
            self.armies.append(army)

        # Northern Holds armies (team 4)
        for name, x, y in [("Jarl Bjorn's Hird", 1600, 300),
                            ("The Frost Guard", 1900, 250),
                            ("Mountain Watch", 1500, 200)]:
            army = create_enemy_army(name, 4, x, y, random.randint(1, 2))
            self.armies.append(army)

        # Maritime Republic armies (team 5)
        for name, x, y in [("Admiral's Fleet", 1300, 2500),
                            ("Corsair Patrol", 1100, 2300),
                            ("Harbor Guard", 1600, 2500)]:
            army = create_enemy_army(name, 5, x, y, random.randint(1, 2))
            self.armies.append(army)

        # Steppe Horde armies (team 6)
        for name, x, y in [("Khan's Riders", 3300, 700),
                            ("Wind Wolves", 3400, 1000),
                            ("Storm Lancers", 3500, 600)]:
            army = create_enemy_army(name, 6, x, y, random.randint(2, 3))
            self.armies.append(army)

        # Holy Order armies (team 7)
        for name, x, y in [("Templar Guard", 1800, 1700),
                            ("Crusader Host", 1900, 1500)]:
            army = create_enemy_army(name, 7, x, y, random.randint(1, 2))
            self.armies.append(army)

        # Free Cities armies (team 8)
        for name, x, y in [("Mercenary Company", 800, 1500),
                            ("Trade Guard", 1400, 1300)]:
            army = create_enemy_army(name, 8, x, y, random.randint(1, 2))
            self.armies.append(army)

    def handle_event(self, event):
        if self.show_recruitment:
            return self._handle_recruitment_event(event)
        if self.show_diplomacy:
            return self._handle_diplomacy_event(event)

        self.camera.handle_event(event)

        if event.type == pygame.KEYDOWN:
            # B1: Real-time controls
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
                self._add_notification("PAUSED" if self.paused else "Resumed")
            elif event.key == pygame.K_1:
                self.campaign_speed = CAMPAIGN_SPEED_1X
                self.paused = False
                self._add_notification("Speed: 1x")
            elif event.key == pygame.K_2:
                self.campaign_speed = CAMPAIGN_SPEED_2X
                self.paused = False
                self._add_notification("Speed: 2x")
            elif event.key == pygame.K_3:
                self.campaign_speed = CAMPAIGN_SPEED_3X
                self.paused = False
                self._add_notification("Speed: 4x")
            elif event.key == pygame.K_r:
                self._try_open_recruitment()
            elif event.key == pygame.K_g:
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

        # Check HUD buttons first (top bar speed controls)
        if pos[1] < 36:
            self._handle_top_bar_click(pos)
            return

        # Check bottom bar buttons
        if pos[1] > SCREEN_HEIGHT - 40:
            self._handle_bottom_bar_click(pos)
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

    def _handle_top_bar_click(self, pos):
        """Handle clicks on the top bar (speed controls)."""
        # Pause button area: x=200-240
        if 200 <= pos[0] <= 240:
            self.paused = not self.paused
            return
        # Speed buttons: 1x at 245, 2x at 280, 4x at 315
        if 245 <= pos[0] <= 275:
            self.campaign_speed = CAMPAIGN_SPEED_1X
            self.paused = False
        elif 280 <= pos[0] <= 310:
            self.campaign_speed = CAMPAIGN_SPEED_2X
            self.paused = False
        elif 315 <= pos[0] <= 345:
            self.campaign_speed = CAMPAIGN_SPEED_3X
            self.paused = False

    def _handle_bottom_bar_click(self, pos):
        """Handle clicks on the bottom bar."""
        # Recruit button
        if SCREEN_WIDTH - 170 < pos[0] < SCREEN_WIDTH - 50:
            self._try_open_recruitment()

    def _handle_right_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)
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
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                self._recruit_unit(idx)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        current = self.player_army.general_stats
        idx = GENERAL_ROSTER.index(current) if current in GENERAL_ROSTER else 0
        idx = (idx + 1) % len(GENERAL_ROSTER)
        self.player_army.general_stats = GENERAL_ROSTER[idx]

    def _handle_diplomacy_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_diplomacy = False
                return None
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                non_player = [f for f in self.factions if not f.is_player]
                if idx < len(non_player):
                    target = non_player[idx]
                    state = self.diplomacy.get_state(0, target.team)
                    if state == DiplomacyState.WAR:
                        if self.diplomacy.propose_peace(0, target.team):
                            self._add_notification(f"Peace with {target.name}!")
                        else:
                            self._add_notification(f"{target.name} rejected peace.")
                    elif state in (DiplomacyState.FRIENDLY,):
                        if self.diplomacy.propose_alliance(0, target.team):
                            self._add_notification(f"Allied with {target.name}!")
                        else:
                            self._add_notification(f"{target.name} declined alliance.")
                    elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                        self.diplomacy.declare_war(0, target.team)
                        self._add_notification(f"War declared on {target.name}!")
        return None

    def _process_day(self):
        """Process end-of-day events (replaces _end_turn)."""
        self.day += 1
        self.turn = self.day  # keep compat

        # Income from settlements
        for s in self.settlements:
            if s.owner == 0:
                self.player_army.gold += s.income

        # Pay upkeep
        self.player_army.gold -= self.player_army.upkeep

        # Refresh recruitment pools periodically (every 3 days)
        if self.day % 3 == 0:
            for s in self.settlements:
                s.refresh_recruits()

        # AI diplomacy (every 2 days)
        if self.day % 2 == 0:
            for f in self.factions:
                if not f.is_player:
                    self.diplomacy.ai_diplomacy_tick(f, self.factions)

        # AI army battles (auto-resolve)
        self._resolve_ai_battles()

        # Capture settlements
        self._process_settlement_capture()

        # Mark fog as needing update
        self._fog_needs_update = True
        self._territory_needs_update = True

    def _process_ai_movement(self):
        """Move AI armies each tick (real-time B1)."""
        for army in self.armies:
            if army.is_player:
                continue

            # Give new orders periodically if not moving
            if not army.moving:
                enemies = [a for a in self.armies
                           if a.team != army.team and
                           self.diplomacy.are_at_war(army.team, a.team)]
                # Find nearby friendly settlements to patrol
                own_settlements = [s for s in self.settlements if s.owner == army.team]

                if enemies and random.random() < 0.3:
                    nearest = min(enemies, key=lambda e: distance(army.x, army.y, e.x, e.y))
                    army.give_move_order(
                        nearest.x + random.randint(-80, 80),
                        nearest.y + random.randint(-80, 80),
                    )
                elif own_settlements and random.random() < 0.5:
                    target = random.choice(own_settlements)
                    army.give_move_order(
                        target.x + random.randint(-100, 100),
                        target.y + random.randint(-100, 100),
                    )
                else:
                    army.give_move_order(
                        army.x + random.randint(-150, 150),
                        army.y + random.randint(-150, 150),
                    )

            army.update()

    def _process_settlement_capture(self):
        """Check if armies capture enemy settlements."""
        for s in self.settlements:
            for army in self.armies:
                if distance(army.x, army.y, s.x, s.y) < 40:
                    if s.owner != army.team:
                        if self.diplomacy.are_at_war(army.team, s.owner if s.owner is not None else -1):
                            if army.army_strength > s.garrison_strength:
                                old_owner = s.owner
                                s.owner = army.team
                                faction_names = {f.team: f.name for f in self.factions}
                                captor = faction_names.get(army.team, "Unknown")
                                self._add_notification(f"{captor} captured {s.name}!")
                                self._territory_needs_update = True

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
                    if a1.army_strength >= a2.army_strength:
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
                faction_names = {f.team: f.name for f in self.factions}
                winner_team = [a for a in self.armies if a not in to_remove and
                               distance(a.x, a.y, army.x, army.y) < 40]
                self.armies.remove(army)

    def _save_game(self):
        from core.save_system import save_campaign
        from core.audio import get_audio
        save_campaign(self)
        get_audio().play("save")
        self._save_notification_timer = 120
        self._add_notification("Game saved!")

    def update(self):
        self.camera.update()

        # Always update player movement (even when paused for responsiveness)
        self.player_army.update()

        # Tick save notification
        if hasattr(self, '_save_notification_timer') and self._save_notification_timer > 0:
            self._save_notification_timer -= 1

        # Update notifications
        self.notifications = [(text, timer - 1) for text, timer in self.notifications if timer > 1]

        # Real-time campaign tick (B1)
        if not self.paused:
            speed = self.campaign_speed
            for _ in range(speed):
                self.day_ticks += 1

                # Process AI movement every few ticks
                if self.day_ticks % 10 == 0:
                    self._process_ai_movement()

                # End of day
                if self.day_ticks >= CAMPAIGN_TICKS_PER_DAY:
                    self.day_ticks = 0
                    self._process_day()

        # Fog needs update when player moves
        if self.player_army.moving:
            self._fog_needs_update = True

        # Check for collisions with enemy armies -> trigger battle
        for army in self.armies:
            if army.is_player or army.team == 0:
                continue
            if not self.diplomacy.are_at_war(0, army.team):
                continue
            # B13: Only trigger if army is visible (not in fog)
            if not self._is_visible(army.x, army.y):
                continue
            if distance(self.player_army.x, self.player_army.y,
                        army.x, army.y) < 25:
                self.pending_battle = (self.player_army, army)
                self.paused = True  # Auto-pause on battle contact
                return

    def _is_visible(self, x, y):
        """B13: Check if a world position is visible (not in fog)."""
        # Visible around player army
        if distance(self.player_army.x, self.player_army.y, x, y) <= CAMPAIGN_VISION_RADIUS:
            return True
        # Visible around owned/allied settlements
        for s in self.settlements:
            if s.owner == 0 or self.diplomacy.are_allied(0, s.owner if s.owner is not None else -1):
                if distance(s.x, s.y, x, y) <= CAMPAIGN_SETTLEMENT_VISION:
                    return True
        return False

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

        # B4: Territory borders (drawn under terrain)
        self._draw_territory_borders(surface)

        # Terrain decorations
        self._draw_terrain(surface)

        # Roads between settlements
        for i, s1 in enumerate(self.settlements):
            for s2 in self.settlements[i + 1:]:
                if distance(s1.x, s1.y, s2.x, s2.y) < 500:
                    p1 = self.camera.world_to_screen(s1.x, s1.y)
                    p2 = self.camera.world_to_screen(s2.x, s2.y)
                    pygame.draw.line(surface, (150, 135, 100), p1, p2, max(1, self.camera.scale(2)))

        # Settlements
        for s in self.settlements:
            s.draw(surface, self.camera)

        # Armies (B13: only draw visible ones)
        for army in self.armies:
            if army.is_player:
                army.draw(surface, self.camera)
            elif self._is_visible(army.x, army.y):
                army.draw(surface, self.camera)

        # B13: Fog of war overlay
        self._draw_fog_of_war(surface)

        # HUD (drawn on top of fog)
        self._draw_hud(surface)

        # Recruitment overlay
        if self.show_recruitment:
            self._draw_recruitment(surface)

        # Diplomacy overlay
        if self.show_diplomacy:
            self._draw_diplomacy(surface)

    def _draw_territory_borders(self, surface):
        """B4: Draw faction territory as colored regions around settlements."""
        # Use a simple approach: draw colored circles/polygons around each faction's settlements
        territory_alpha = 30
        for s in self.settlements:
            if s.owner is None:
                continue
            color = TEAM_COLORS.get(s.owner, GREY)
            sx, sy = self.camera.world_to_screen(s.x, s.y)

            # Territory radius depends on settlement type
            if s.settlement_type == SettlementType.CASTLE:
                radius = self.camera.scale(180)
            elif s.settlement_type == SettlementType.TOWN:
                radius = self.camera.scale(150)
            else:
                radius = self.camera.scale(100)

            if radius < 5:
                continue

            # Draw semi-transparent territory circle
            territory_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            territory_color = (*color, territory_alpha)
            pygame.draw.circle(territory_surf, territory_color, (radius, radius), radius)
            # Border
            border_color = (*color, territory_alpha + 40)
            pygame.draw.circle(territory_surf, border_color, (radius, radius), radius, max(1, int(radius * 0.05)))
            surface.blit(territory_surf, (sx - radius, sy - radius))

    def _draw_terrain(self, surface):
        """Draw decorative terrain features."""
        # Forests (expanded for larger map)
        forests = [
            (200, 400, 120), (1000, 200, 80), (700, 800, 100),
            (1500, 900, 90), (1900, 300, 70), (1100, 700, 110),
            (900, 900, 85), (600, 1400, 95), (2800, 1500, 80),
            (3300, 400, 75), (1700, 2200, 90),
        ]
        for fx, fy, fr in forests:
            sx, sy = self.camera.world_to_screen(fx, fy)
            r = self.camera.scale(fr)
            if r < 3:
                continue
            forest_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(forest_surf, (60, 100, 40, 80), (r, r), r)
            surface.blit(forest_surf, (sx - r, sy - r))

        # Mountains (expanded)
        mountains = [
            (1100, 150, 60), (1800, 600, 50), (300, 900, 45),
            (1600, 100, 55), (3000, 400, 50), (2500, 1400, 45),
            (500, 1800, 40),
        ]
        for mx, my, mr in mountains:
            sx, sy = self.camera.world_to_screen(mx, my)
            r = self.camera.scale(mr)
            if r < 3:
                continue
            pts = [(sx, sy - r), (sx - r, sy + r // 2), (sx + r, sy + r // 2)]
            pygame.draw.polygon(surface, (120, 110, 90), pts)
            pygame.draw.polygon(surface, (160, 150, 120), pts, 2)
            cap = [(sx, sy - r), (sx - r // 3, sy - r // 3), (sx + r // 3, sy - r // 3)]
            pygame.draw.polygon(surface, WHITE, cap)

        # Deserts (southeast)
        deserts = [(2800, 1900, 200), (3200, 1700, 150), (3000, 2100, 120)]
        for dx, dy, dr in deserts:
            sx, sy = self.camera.world_to_screen(dx, dy)
            r = self.camera.scale(dr)
            if r < 3:
                continue
            desert_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(desert_surf, (210, 190, 140, 60), (r, r), r)
            surface.blit(desert_surf, (sx - r, sy - r))

        # Water/coast (south)
        for wx, wy, wr in [(1200, 2700, 250), (800, 2500, 150), (1600, 2700, 180)]:
            sx, sy = self.camera.world_to_screen(wx, wy)
            r = self.camera.scale(wr)
            if r < 3:
                continue
            water_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(water_surf, (60, 100, 160, 50), (r, r), r)
            surface.blit(water_surf, (sx - r, sy - r))

    def _draw_fog_of_war(self, surface):
        """B13: Draw fog of war overlay - darken areas outside vision range."""
        # Create fog surface at reduced resolution for performance
        fog_scale = 4  # 1 fog pixel = 4 screen pixels
        fog_w = SCREEN_WIDTH // fog_scale
        fog_h = SCREEN_HEIGHT // fog_scale

        fog = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA)
        fog.fill((20, 15, 10, CAMPAIGN_FOG_ALPHA))

        # Cut out visible areas (draw transparent circles)
        # Player army vision
        px, py = self.camera.world_to_screen(self.player_army.x, self.player_army.y)
        pr = self.camera.scale(CAMPAIGN_VISION_RADIUS) // fog_scale
        if pr > 0:
            pygame.draw.circle(fog, (0, 0, 0, 0), (px // fog_scale, py // fog_scale), pr)

        # Owned/allied settlement vision
        for s in self.settlements:
            if s.owner == 0 or (s.owner is not None and
                                self.diplomacy.are_allied(0, s.owner)):
                sx, sy = self.camera.world_to_screen(s.x, s.y)
                sr = self.camera.scale(CAMPAIGN_SETTLEMENT_VISION) // fog_scale
                if sr > 0:
                    pygame.draw.circle(fog, (0, 0, 0, 0), (sx // fog_scale, sy // fog_scale), sr)

        # Scale up and blit
        fog_scaled = pygame.transform.scale(fog, (SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(fog_scaled, (0, 0))

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 22)
        small_font = pygame.font.SysFont(None, 16)

        # Top bar (C2: improved)
        bar = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 200))
        surface.blit(bar, (0, 0))

        # Day counter (C2: replaces turn counter)
        day_text = font.render(f"Day {self.day}", True, WHITE)
        surface.blit(day_text, (10, 8))

        # Gold
        gold_text = font.render(f"Gold: {self.player_army.gold}", True, GOLD)
        surface.blit(gold_text, (90, 8))

        # Speed controls (C2)
        speed_x = 200
        # Pause button
        pause_color = (200, 80, 80) if self.paused else (80, 80, 80)
        pygame.draw.rect(surface, pause_color, (speed_x, 4, 35, 28))
        pygame.draw.rect(surface, WHITE, (speed_x, 4, 35, 28), 1)
        pause_label = small_font.render("||" if not self.paused else ">>", True, WHITE)
        surface.blit(pause_label, (speed_x + 10, 10))
        speed_x += 40

        # Speed buttons
        for i, (label, spd) in enumerate([("1x", CAMPAIGN_SPEED_1X),
                                           ("2x", CAMPAIGN_SPEED_2X),
                                           ("4x", CAMPAIGN_SPEED_3X)]):
            btn_color = (60, 120, 60) if self.campaign_speed == spd and not self.paused else (60, 60, 60)
            pygame.draw.rect(surface, btn_color, (speed_x, 4, 30, 28))
            pygame.draw.rect(surface, WHITE, (speed_x, 4, 30, 28), 1)
            spd_text = small_font.render(label, True, WHITE)
            surface.blit(spd_text, (speed_x + 6, 10))
            speed_x += 35

        # Army info
        army_text = font.render(
            f"Army: {self.player_army.total_soldiers} | "
            f"Str: {self.player_army.army_strength} | "
            f"Upkeep: {self.player_army.upkeep}/day",
            True, WHITE)
        surface.blit(army_text, (speed_x + 20, 8))

        # Day progress bar
        progress = self.day_ticks / CAMPAIGN_TICKS_PER_DAY
        bar_x = SCREEN_WIDTH - 160
        bar_w = 100
        pygame.draw.rect(surface, DARK_GREY, (bar_x, 14, bar_w, 8))
        pygame.draw.rect(surface, (180, 160, 80), (bar_x, 14, int(bar_w * progress), 8))
        time_label = small_font.render("Day", True, (180, 180, 180))
        surface.blit(time_label, (bar_x + bar_w + 5, 12))

        # Bottom bar
        bottom = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        bottom.fill((0, 0, 0, 200))
        surface.blit(bottom, (0, SCREEN_HEIGHT - 40))

        # Controls
        ctrl_text = small_font.render(
            "[RMB] Move  [R] Recruit  [G] General  [D] Diplomacy  "
            "[SPACE] Pause  [1/2/3] Speed  [Ctrl+S] Save",
            True, (180, 180, 180))
        surface.blit(ctrl_text, (10, SCREEN_HEIGHT - 30))

        # Recruit button
        btn_rect2 = (SCREEN_WIDTH - 170, SCREEN_HEIGHT - 36, 120, 32)
        pygame.draw.rect(surface, (60, 60, 120), btn_rect2)
        pygame.draw.rect(surface, WHITE, btn_rect2, 1)
        btn_text2 = font.render("Recruit [R]", True, WHITE)
        surface.blit(btn_text2, (btn_rect2[0] + 12, btn_rect2[1] + 7))

        # Save notification
        if hasattr(self, '_save_notification_timer') and self._save_notification_timer > 0:
            save_text = font.render("Game Saved!", True, (100, 255, 100))
            surface.blit(save_text, (SCREEN_WIDTH // 2 - save_text.get_width() // 2, 45))

        # Paused indicator (C2)
        if self.paused:
            pause_text = pygame.font.SysFont(None, 36).render("PAUSED", True, (255, 200, 100))
            surface.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, 45))

        # Notification feed (C2)
        if self.notifications:
            notif_y = 75 if self.paused else 45
            for text, timer in self.notifications[-4:]:  # show last 4
                alpha = min(255, timer * 3)
                notif_surf = small_font.render(text, True, (220, 220, 200))
                notif_alpha_surf = pygame.Surface(notif_surf.get_size(), pygame.SRCALPHA)
                notif_alpha_surf.fill((0, 0, 0, 0))
                notif_alpha_surf.blit(notif_surf, (0, 0))
                notif_alpha_surf.set_alpha(alpha)
                surface.blit(notif_alpha_surf, (10, notif_y))
                notif_y += 18

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
        panel = pygame.Surface((250, 140), pygame.SRCALPHA)
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
        income_text = small_font.render(f"Income: {s.income}/day", True, GOLD)
        surface.blit(income_text, (x, y))
        y += 18
        garrison_text = small_font.render(f"Garrison: {s.garrison_strength}", True, WHITE)
        surface.blit(garrison_text, (x, y))
        y += 18
        # Show faction color swatch
        team_color = TEAM_COLORS.get(s.owner, GREY)
        pygame.draw.rect(surface, team_color, (x, y, 15, 15))
        pygame.draw.rect(surface, WHITE, (x, y, 15, 15), 1)
        state_text = small_font.render(
            f" {self.diplomacy.get_state(0, s.owner if s.owner is not None else -1).upper()}"
            if s.owner != 0 and s.owner is not None else "",
            True, (180, 180, 180))
        surface.blit(state_text, (x + 20, y))

    def _draw_recruitment(self, surface):
        if not self.recruitment_settlement:
            return
        s = self.recruitment_settlement

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 420, 500
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 100
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = pygame.font.SysFont(None, 24)
        small = pygame.font.SysFont(None, 18)

        title = font.render(f"Recruit at {s.name}", True, GOLD)
        surface.blit(title, (panel_x + 10, panel_y + 10))

        gold = font.render(f"Gold: {self.player_army.gold}", True, GOLD)
        surface.blit(gold, (panel_x + 10, panel_y + 35))

        # Close button
        pygame.draw.rect(surface, (150, 50, 50), (panel_x + panel_w - 35, panel_y + 5, 30, 25))
        close = small.render("X", True, WHITE)
        surface.blit(close, (panel_x + panel_w - 25, panel_y + 8))

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
            pygame.draw.rect(surface, (120, 40, 40), (panel_x + 340, y, 50, 18))
            disband = small.render("Drop", True, WHITE)
            surface.blit(disband, (panel_x + 345, y + 1))
            y += 25

        footer = small.render("[ESC] Close  |  Click unit to recruit  |  Click 'Drop' to disband",
                              True, (150, 150, 150))
        surface.blit(footer, (panel_x + 10, panel_y + panel_h - 25))

    def _draw_diplomacy(self, surface):
        """Draw diplomacy overview panel."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 500, 450
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 80
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

            team_color = TEAM_COLORS.get(faction.team, GREY)

            # Color swatch
            pygame.draw.rect(surface, team_color, (panel_x + 15, y + 2, 12, 12))

            name_text = small.render(f"[{i+1}] {faction.name}", True, team_color)
            surface.blit(name_text, (panel_x + 32, y))

            state_text = small.render(f"{state.upper()} ({rel:+d})", True, color)
            surface.blit(state_text, (panel_x + 250, y))

            pers = tiny.render(f"({faction.personality})", True, (120, 120, 120))
            surface.blit(pers, (panel_x + 400, y + 2))

            y += 20

            if state == DiplomacyState.WAR:
                hint = tiny.render(f"  Press [{i+1}] to propose peace", True, (150, 150, 150))
            elif state == DiplomacyState.FRIENDLY:
                hint = tiny.render(f"  Press [{i+1}] to propose alliance", True, (150, 150, 150))
            elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                hint = tiny.render(f"  Press [{i+1}] to declare war", True, (150, 150, 150))
            else:
                hint = tiny.render(f"  Allied", True, (100, 200, 255))
            surface.blit(hint, (panel_x + 30, y))
            y += 18

            owned = sum(1 for s in self.settlements if s.owner == faction.team)
            armies_count = sum(1 for a in self.armies if a.team == faction.team)
            info = tiny.render(
                f"  Settlements: {owned}  |  Armies: {armies_count}",
                True, (140, 140, 140))
            surface.blit(info, (panel_x + 30, y))
            y += 26

        footer = tiny.render("[ESC] Close  |  Press number to interact", True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))
