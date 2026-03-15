"""Campaign map scene - Mount & Blade Warband style overworld.

Features:
- Real-time campaign with pause/speed controls (B1)
- 35 settlements across 8 factions (B4)
- Faction territory borders with colored overlays (B4)
- Campaign fog of war with vision radius (B13)
- Improved HUD with day counter, speed, notifications (C2)
- Interactable settlements with tavern/recruit/rest/garrison (B9/C3)
- Factionless player start as independent lord (B2)
- Army size limits tied to general level (B11)
"""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT,
    CAMPAIGN_TICKS_PER_DAY,
    CAMPAIGN_SPEED_PAUSED, CAMPAIGN_SPEED_1X, CAMPAIGN_SPEED_2X, CAMPAIGN_SPEED_3X,
    CAMPAIGN_MOVE_SPEED,
    CAMPAIGN_VISION_RADIUS, CAMPAIGN_SETTLEMENT_VISION, CAMPAIGN_FOG_ALPHA,
    TEAM_COLORS, TEAM_COLORS_LIGHT,
    WHITE, BLACK, GREY, DARK_GREY, GOLD, YELLOW,
    DARK_GREEN, BROWN, SAND, LIGHT_BLUE,
    INCOME_PER_SETTLEMENT,
    FACTION_JOIN_THRESHOLD, FACTION_LEAVE_PENALTY,
    REST_COST_PER_DAY,
    PERSUASION_RANGE,
    # D2: Seasons
    SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER,
    SEASON_CYCLE_LENGTH, SEASON_SPRING_END, SEASON_SUMMER_END, SEASON_AUTUMN_END,
    SEASON_SUMMER_DESERT_SPEED_BONUS, SEASON_AUTUMN_INCOME_BONUS,
    SEASON_WINTER_MOVE_PENALTY, SEASON_WINTER_MOUNTAIN_ATTRITION,
    SEASON_AUTUMN_MUD_CHANCE, SEASON_WINTER_HARSH_WEATHER_CHANCE,
    # D3: Supply Lines
    SUPPLY_RANGE, SUPPLY_MORALE_LOSS, SUPPLY_DESERTION_CHANCE, SUPPLY_WARNING_RANGE,
    # D5: Tournaments
    TOURNAMENT_INTERVAL, TOURNAMENT_ENTRY_FEE, TOURNAMENT_ROUND_COUNT,
    TOURNAMENT_BASE_REWARD, TOURNAMENT_REP_REWARD, TOURNAMENT_ROUND_REWARDS,
)
from core.camera import Camera
from core.utils import distance, point_in_rect, get_font
from campaign.settlement import Settlement, SettlementType
from campaign.army import (
    Army, create_default_player_army, create_enemy_army,
)
from campaign.settlement_ui import SettlementInteraction
from campaign.ai_controller import ArmyAI, pick_personality, AITask
from campaign.roaming import RoamingManager, ROAMING_TYPES
from campaign.quest import QuestManager
from data.unit_types import ALL_RECRUITABLE, GENERAL_ROSTER
from campaign.faction import FACTION_ROSTER, FACTION_BY_TEAM
from campaign.diplomacy import DiplomacyManager, DiplomacyState
from campaign.generals import GeneralManager


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
        self.show_diplomacy = False
        self.show_quest_log = False
        self.show_army_panel = False
        self.pending_battle = None  # (player_army, enemy_army, terrain_type) tuple

        # B9/C3: Settlement interaction
        self.settlement_interaction = None  # SettlementInteraction instance or None

        # B2: Player faction allegiance (None = independent)
        self.player_faction = None

        # Notification feed (C2)
        self.notifications = []  # list of (text, timer)
        self.NOTIFICATION_DURATION = 300  # 5 seconds at 60fps

        # Faction & diplomacy
        self.factions = FACTION_ROSTER[:]
        self.diplomacy = DiplomacyManager(self.factions)
        # B2: Player starts neutral with all factions (independent lord)
        for f in self.factions:
            self.diplomacy.set_relation(0, f.team, 0)

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

        # B5: AI controllers - maps army id -> ArmyAI
        self.ai_controllers = {}

        # B8: Roaming armies and events manager
        self.roaming_manager = RoamingManager()

        # B3: Quest system
        self.quest_manager = QuestManager()

        # B6/D6: General management (loyalty, betrayal, prisoners)
        self.general_manager = GeneralManager()
        self.show_persuasion = False      # persuasion dialog overlay
        self.persuasion_target = None     # army being persuaded
        self.show_prisoners = False       # prisoner management overlay
        self.prisoner_action_msg = None   # feedback message for prisoner actions
        self.prisoner_action_timer = 0

        # D1: Terrain zones (queryable from decorative terrain data)
        self._terrain_forests = [
            (200, 400, 120), (1000, 200, 80), (700, 800, 100),
            (1500, 900, 90), (1900, 300, 70), (1100, 700, 110),
            (900, 900, 85), (600, 1400, 95), (2800, 1500, 80),
            (3300, 400, 75), (1700, 2200, 90),
        ]
        self._terrain_mountains = [
            (1100, 150, 60), (1800, 600, 50), (300, 900, 45),
            (1600, 100, 55), (3000, 400, 50), (2500, 1400, 45),
            (500, 1800, 40),
        ]
        self._terrain_deserts = [
            (2800, 1900, 200), (3200, 1700, 150), (3000, 2100, 120),
        ]
        self._terrain_water = [
            (1200, 2700, 250), (800, 2500, 150), (1600, 2700, 180),
        ]

        # D5: Tournament state
        self.tournament_towns = {}  # settlement_name -> next_tournament_day
        self.active_tournament = None  # dict with tournament state or None
        self.show_tournament = False

        self._generate_world()
        self._init_ai_controllers()
        self._register_generals()
        self._add_notification("You begin as an independent lord. Visit settlements to recruit and trade!")

    def _add_notification(self, text):
        """Add a notification to the feed."""
        self.notifications.append((text, self.NOTIFICATION_DURATION))

    def _generate_world(self):
        """Generate campaign map with 35 settlements across 8 factions."""
        # B4: Expanded settlement data - 35 settlements
        settlement_data = [
            # B2: Western settlements - neutral/unclaimed (player starts with nothing)
            ("Ironhold", 350, 400, SettlementType.CASTLE, None),
            ("Millbrook", 500, 250, SettlementType.VILLAGE, None),
            ("King's Landing", 550, 600, SettlementType.TOWN, None),
            ("Brightwater", 300, 700, SettlementType.VILLAGE, None),

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
        # D5: Tournament overlay takes top priority
        if self.show_tournament and self.active_tournament:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if self.active_tournament["finished"]:
                        self._close_tournament()
                    else:
                        self._advance_tournament_round()
                elif event.key == pygame.K_ESCAPE:
                    self._close_tournament()
            return None

        # B9: Settlement interaction overlay takes priority
        if self.settlement_interaction:
            result = self.settlement_interaction.handle_event(event)
            if result:
                self._process_settlement_action(result)
            return None

        if self.show_diplomacy:
            return self._handle_diplomacy_event(event)

        if getattr(self, 'show_army_panel', False):
            return self._handle_army_panel_event(event)

        # B6: Persuasion overlay
        if getattr(self, 'show_persuasion', False):
            return self._handle_persuasion_event(event)

        # D6: Prisoner management overlay
        if getattr(self, 'show_prisoners', False):
            return self._handle_prisoner_event(event)

        # D6: Player capture overlay
        if self.general_manager.player_capture.is_captured:
            return self._handle_capture_event(event)

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
            elif event.key == pygame.K_e:
                self._try_enter_settlement()
            elif event.key == pygame.K_r:
                self._try_open_recruitment()
            elif event.key == pygame.K_g:
                self._cycle_general()
            elif event.key == pygame.K_d:
                self.show_diplomacy = True
            elif event.key == pygame.K_q:
                self.show_quest_log = not getattr(self, 'show_quest_log', False)
            elif event.key == pygame.K_a:
                self.show_army_panel = not getattr(self, 'show_army_panel', False)
            elif event.key == pygame.K_p:
                self._try_persuasion()
            elif event.key == pygame.K_j:
                if self.general_manager.player_prisoners:
                    self.show_prisoners = True
                    self.paused = True
                else:
                    self._add_notification("No prisoners held.")
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
        # D6: Can't move while captured
        if self.general_manager.player_capture.is_captured:
            self._add_notification("Cannot move while captured!")
            return
        wx, wy = self.camera.screen_to_world(*pos)
        self.player_army.give_move_order(wx, wy)

    def _try_enter_settlement(self):
        """B9: Try to enter a nearby settlement for interaction."""
        for s in self.settlements:
            if distance(self.player_army.x, self.player_army.y, s.x, s.y) < 60:
                # Can't enter hostile settlements
                if s.owner is not None and self.diplomacy.are_at_war(0, s.owner):
                    self._add_notification(f"Cannot enter {s.name} - at war!")
                    return
                self.settlement_interaction = SettlementInteraction(
                    s, self.player_army, self.diplomacy, self.factions,
                    self.day, self.settlements, self.armies,
                    quest_manager=self.quest_manager,
                    tournament_available=self._is_tournament_available(s))
                self.paused = True
                self._add_notification(f"Entered {s.name}")
                return
        self._add_notification("No settlement nearby. Move closer to enter.")

    def _process_settlement_action(self, action):
        """Handle actions returned from SettlementInteraction."""
        act = action.get("action")
        if act == "leave":
            self.settlement_interaction = None
            self.paused = False
        elif act == "advance_day":
            days = action.get("days", 1)
            for _ in range(days):
                self._process_day()
            self._add_notification(f"Rested for {days} day(s).")
            # Update the settlement_interaction's day reference
            if self.settlement_interaction:
                self.settlement_interaction.day = self.day
        elif act == "enter_tournament":
            # D5: Player wants to enter tournament
            if self.player_army.gold >= TOURNAMENT_ENTRY_FEE:
                self._start_tournament()
            else:
                self._add_notification("Not enough gold for tournament entry fee.")

    def _try_open_recruitment(self):
        # B9: If near a settlement, open settlement interaction instead
        for s in self.settlements:
            if distance(self.player_army.x, self.player_army.y, s.x, s.y) < 60:
                if s.owner is not None and self.diplomacy.are_at_war(0, s.owner):
                    self._add_notification(f"Cannot recruit at {s.name} - at war!")
                    return
                self.settlement_interaction = SettlementInteraction(
                    s, self.player_army, self.diplomacy, self.factions,
                    self.day, self.settlements, self.armies,
                    quest_manager=self.quest_manager,
                    tournament_available=self._is_tournament_available(s))
                self.settlement_interaction.current_tab = "recruit"
                self.paused = True
                return
        self._add_notification("No settlement nearby for recruitment.")

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
                    rel = self.diplomacy.get_relation(0, target.team)
                    if state == DiplomacyState.WAR:
                        if self.diplomacy.propose_peace(0, target.team):
                            self._add_notification(f"Peace with {target.name}!")
                        else:
                            self._add_notification(f"{target.name} rejected peace.")
                    elif state in (DiplomacyState.FRIENDLY,):
                        # B2: Join faction if rep high enough and player is independent
                        if self.player_faction is None and rel >= FACTION_JOIN_THRESHOLD:
                            self._join_faction(target)
                        elif self.diplomacy.propose_alliance(0, target.team):
                            self._add_notification(f"Allied with {target.name}!")
                        else:
                            self._add_notification(f"{target.name} declined alliance.")
                    elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                        self.diplomacy.declare_war(0, target.team)
                        self._add_notification(f"War declared on {target.name}!")
            # B2: Leave faction with 'L' key
            if event.key == pygame.K_l and self.player_faction is not None:
                self._leave_faction()
        return None

    def _join_faction(self, faction):
        """B2: Player joins a faction as a vassal."""
        self.player_faction = faction.team
        # Transfer player settlements to faction
        for s in self.settlements:
            if s.owner == 0:
                s.owner = faction.team
        # Set allied relations
        self.diplomacy.set_relation(0, faction.team, 70)
        # Inherit faction's wars
        for other_f in self.factions:
            if other_f.team != faction.team and self.diplomacy.are_at_war(faction.team, other_f.team):
                self.diplomacy.declare_war(0, other_f.team)
        self._add_notification(f"Joined {faction.name}! You are now a vassal.")
        self._territory_needs_update = True

    def _found_player_faction(self, settlement):
        """B7: Player founds their own faction by capturing a neutral settlement."""
        self.player_faction = 0  # player's own faction (team 0)
        settlement.owner = 0
        self._add_notification(
            f"You have founded your own faction! {settlement.name} is your capital.")
        self._territory_needs_update = True
        # Set relations: all factions are wary of the new power
        for f in self.factions:
            current = self.diplomacy.get_relation(0, f.team)
            if current > -20:
                self.diplomacy.modify_relation(0, f.team, -10)

    def _leave_faction(self):
        """B2: Player leaves their current faction."""
        if self.player_faction is None:
            return
        faction_name = FACTION_BY_TEAM.get(self.player_faction)
        faction_display = faction_name.name if faction_name else "faction"
        self.diplomacy.modify_relation(0, self.player_faction, FACTION_LEAVE_PENALTY)
        self.player_faction = None
        self._add_notification(f"Left {faction_display}. You are independent again.")
        self._territory_needs_update = True

    # ------------------------------------------------------------------
    # D1: Terrain detection for battles
    # ------------------------------------------------------------------

    def _get_terrain_at_position(self, x, y):
        """D1: Return terrain type string at a campaign map position."""
        # Check forests
        for fx, fy, fr in self._terrain_forests:
            if distance(x, y, fx, fy) <= fr:
                return "forest"
        # Check mountains
        for mx, my, mr in self._terrain_mountains:
            if distance(x, y, mx, my) <= mr:
                return "mountain"
        # Check deserts
        for dx, dy, dr in self._terrain_deserts:
            if distance(x, y, dx, dy) <= dr:
                return "desert"
        # Check water/coast
        for wx, wy, wr in self._terrain_water:
            if distance(x, y, wx, wy) <= wr:
                return "coastal"
        return "plains"

    # ------------------------------------------------------------------
    # D2: Season system
    # ------------------------------------------------------------------

    def _get_current_season(self):
        """D2: Return current season based on day counter."""
        day_in_cycle = ((self.day - 1) % SEASON_CYCLE_LENGTH) + 1
        if day_in_cycle <= SEASON_SPRING_END:
            return SEASON_SPRING
        elif day_in_cycle <= SEASON_SUMMER_END:
            return SEASON_SUMMER
        elif day_in_cycle <= SEASON_AUTUMN_END:
            return SEASON_AUTUMN
        else:
            return SEASON_WINTER

    # ------------------------------------------------------------------
    # D3: Supply lines
    # ------------------------------------------------------------------

    def _get_nearest_friendly_settlement_dist(self, army):
        """D3: Return distance to nearest friendly settlement for an army."""
        min_dist = float('inf')
        for s in self.settlements:
            if s.owner == army.team:
                d = distance(army.x, army.y, s.x, s.y)
                if d < min_dist:
                    min_dist = d
            # Allied settlements also count
            elif s.owner is not None and self.diplomacy.are_allied(army.team, s.owner):
                d = distance(army.x, army.y, s.x, s.y)
                if d < min_dist:
                    min_dist = d
        return min_dist

    def _process_supply_lines(self):
        """D3: Apply supply line attrition to armies far from friendly territory."""
        for army in self.armies:
            # Independent player (no faction, no settlements) is exempt from supply attrition
            if army.is_player and self.player_faction is None:
                has_settlements = any(s.owner == army.team for s in self.settlements)
                if not has_settlements:
                    continue
            dist = self._get_nearest_friendly_settlement_dist(army)
            if dist > SUPPLY_RANGE:
                # Morale loss
                if not hasattr(army, 'campaign_morale'):
                    army.campaign_morale = 100
                army.campaign_morale = max(0, army.campaign_morale - SUPPLY_MORALE_LOSS)

                # Desertion chance per squad
                for sq in army.squads:
                    if random.random() < SUPPLY_DESERTION_CHANCE and sq.current_count > 1:
                        sq.current_count -= 1

                if army.is_player:
                    self._add_notification("Supply lines stretched! Troops suffering attrition.")
            else:
                # Slowly recover morale when in supply
                if hasattr(army, 'campaign_morale'):
                    army.campaign_morale = min(100, army.campaign_morale + 1)

            # Clean up destroyed squads from desertion
            army.squads = [sq for sq in army.squads if not sq.is_destroyed]

    # ------------------------------------------------------------------
    # D5: Tournament system
    # ------------------------------------------------------------------

    def _process_tournaments(self):
        """D5: Schedule tournaments at towns periodically."""
        for s in self.settlements:
            if s.settlement_type != SettlementType.TOWN:
                continue
            if s.name not in self.tournament_towns:
                # Schedule first tournament
                self.tournament_towns[s.name] = self.day + random.randint(5, TOURNAMENT_INTERVAL)
            elif self.day >= self.tournament_towns[s.name]:
                # Tournament is available - stays until next cycle
                # Will be rescheduled when player enters or after interval passes
                if self.day > self.tournament_towns[s.name] + TOURNAMENT_INTERVAL:
                    # Tournament expired, schedule next
                    self.tournament_towns[s.name] = self.day + random.randint(5, TOURNAMENT_INTERVAL)

    def _is_tournament_available(self, settlement):
        """D5: Check if a tournament is currently available at this settlement."""
        if settlement.settlement_type != SettlementType.TOWN:
            return False
        if settlement.name not in self.tournament_towns:
            return False
        scheduled = self.tournament_towns[settlement.name]
        return scheduled <= self.day <= scheduled + TOURNAMENT_INTERVAL

    def _start_tournament(self):
        """D5: Start a tournament bracket."""
        self.active_tournament = {
            "round": 0,
            "max_rounds": TOURNAMENT_ROUND_COUNT,
            "gold_won": 0,
            "results": [],  # list of (round_num, won_bool, description)
            "finished": False,
            "victory": False,
        }
        self.show_tournament = True
        self.player_army.gold -= TOURNAMENT_ENTRY_FEE

    def _advance_tournament_round(self):
        """D5: Auto-resolve one round of the tournament."""
        if not self.active_tournament or self.active_tournament["finished"]:
            return

        t = self.active_tournament
        round_num = t["round"]

        # Calculate player fight strength (simplified)
        player_strength = self.player_army.army_strength
        player_level = self.player_army.general_level

        # Opponents get harder each round
        difficulty_mult = 1.0 + round_num * 0.4
        opponent_strength = int(player_strength * (0.5 + random.random() * 0.5) * difficulty_mult)

        opponent_names = [
            "a burly sellsword", "the Iron Fist", "a masked warrior",
            "the Arena Champion", "a foreign swordsman", "the Red Knight",
            "a grizzled veteran", "the Swift Blade", "a barbarian chief",
        ]
        opponent = random.choice(opponent_names)

        # Resolve fight - player skill + luck
        player_roll = player_strength + player_level * 20 + random.randint(0, 100)
        opponent_roll = opponent_strength + random.randint(0, 80)

        won = player_roll > opponent_roll
        round_reward = TOURNAMENT_ROUND_REWARDS[min(round_num, len(TOURNAMENT_ROUND_REWARDS) - 1)]

        if won:
            t["gold_won"] += round_reward
            t["results"].append((round_num + 1, True,
                                 f"Round {round_num + 1}: Defeated {opponent}! (+{round_reward}g)"))
            t["round"] += 1
            if t["round"] >= t["max_rounds"]:
                t["finished"] = True
                t["victory"] = True
                # Award reputation
                self.player_army.gold += t["gold_won"]
                self._add_notification(
                    f"Tournament Victory! Won {t['gold_won']}g!")
        else:
            t["results"].append((round_num + 1, False,
                                 f"Round {round_num + 1}: Defeated by {opponent}."))
            t["finished"] = True
            t["victory"] = False
            # Still get partial gold
            if t["gold_won"] > 0:
                self.player_army.gold += t["gold_won"]
                self._add_notification(
                    f"Eliminated in round {round_num + 1}. Won {t['gold_won']}g.")
            else:
                self._add_notification(f"Eliminated in round {round_num + 1}.")

    def _close_tournament(self):
        """D5: Close tournament UI and reschedule."""
        if self.active_tournament and self.settlement_interaction:
            town_name = self.settlement_interaction.settlement.name
            self.tournament_towns[town_name] = self.day + TOURNAMENT_INTERVAL
        self.active_tournament = None
        self.show_tournament = False

    def _process_day(self):
        """Process end-of-day events (replaces _end_turn)."""
        self.day += 1
        self.turn = self.day  # keep compat

        # D2: Get current season for income modifiers
        season = self._get_current_season()
        income_mult = SEASON_AUTUMN_INCOME_BONUS if season == SEASON_AUTUMN else 1.0

        # Income from settlements (own settlements or faction settlements if member)
        for s in self.settlements:
            if s.owner == 0:
                self.player_army.gold += int(s.income * income_mult)
            elif self.player_faction is not None and s.owner == self.player_faction:
                # Vassal gets reduced income from faction settlements
                self.player_army.gold += int(s.income * income_mult) // 4

        # Pay upkeep (morale penalty and desertion if can't afford)
        upkeep = self.player_army.upkeep
        if self.player_army.gold >= upkeep:
            self.player_army.gold -= upkeep
        else:
            self.player_army.gold -= upkeep
            # Morale penalty for unpaid troops
            deficit_ratio = min(1.0, abs(self.player_army.gold) / max(1, upkeep))
            for sq in self.player_army.squads:
                sq_morale = getattr(sq, 'campaign_morale', 100)
                sq.campaign_morale = max(0, sq_morale - 5 * deficit_ratio)
            if self.player_army.gold < -upkeep * 3:
                self._add_notification("Your troops are unpaid! Risk of desertion!")

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

        # B8: Roaming armies + events
        self.roaming_manager.update(
            self.day, self.armies, self.settlements, self.diplomacy, self)

        # B3: Quest updates
        self.quest_manager.generate_bounty_board(
            self.settlements, self.factions, self.day)
        completed, failed = self.quest_manager.update(
            self.player_army, self.day, self.diplomacy)
        for q in completed:
            self._add_notification(f"Quest Complete: {q.title} (+{q.gold_reward}g)")
        for q in failed:
            self._add_notification(f"Quest Failed: {q.title}")

        # B6: Check for general betrayals
        betrayals = self.general_manager.check_betrayals(
            self.armies, self.ai_controllers, self.diplomacy,
            self._add_notification)
        for army, action in betrayals:
            new_team = self.general_manager.process_betrayal(
                army, action, self.armies, self.ai_controllers,
                self.factions, self.diplomacy)
            # Re-key the AI controller since id may stay the same
            # but update internal refs
            ai = self.ai_controllers.get(id(army))
            if ai:
                ai.army = army

        # D6: Update prisoner timers
        self.general_manager.update_prisoners()

        # D6: Update player capture state
        if self.general_manager.player_capture.is_captured:
            escaped = self.general_manager.update_player_capture(self.player_army)
            if escaped:
                self._add_notification(
                    "You have escaped captivity! Your army is weakened.")

        # D3: Supply line attrition
        self._process_supply_lines()

        # D2: Winter mountain attrition
        if season == SEASON_WINTER:
            for army in self.armies:
                terrain = self._get_terrain_at_position(army.x, army.y)
                if terrain == "mountain":
                    # Lose soldiers to cold
                    for sq in army.squads:
                        if sq.current_count > 1:
                            sq.current_count = max(1, sq.current_count - SEASON_WINTER_MOUNTAIN_ATTRITION)
                    if army.is_player:
                        self._add_notification("Winter in the mountains! Troops suffering from cold.")

        # D5: Tournament scheduling
        self._process_tournaments()

        # Mark fog as needing update
        self._fog_needs_update = True
        self._territory_needs_update = True

    def _init_ai_controllers(self):
        """B5: Attach AI controllers to all non-player armies."""
        for army in self.armies:
            if not army.is_player:
                self.ai_controllers[id(army)] = ArmyAI(army, pick_personality())

    def _register_generals(self):
        """B6: Register all NPC generals with the GeneralManager."""
        for army in self.armies:
            if army.is_player:
                continue
            ai = self.ai_controllers.get(id(army))
            personality = ai.personality if ai else "cautious"
            self.general_manager.register_general(
                army.general_name, army.team, personality, army.general_level)

    def _get_ai(self, army):
        """Get or create AI controller for an army."""
        key = id(army)
        if key not in self.ai_controllers:
            self.ai_controllers[key] = ArmyAI(army, pick_personality())
        return self.ai_controllers[key]

    def _process_ai_movement(self):
        """B5: AI armies use priority-based task system."""
        for army in self.armies:
            if army.is_player:
                continue
            ai = self._get_ai(army)
            ai.update(self.armies, self.settlements, self.diplomacy)

    def _process_settlement_capture(self):
        """Check if armies capture enemy settlements."""
        for s in self.settlements:
            for army in self.armies:
                if distance(army.x, army.y, s.x, s.y) < 40:
                    capture_team = army.team
                    # B2: Player captures go to player faction if they have one
                    if army.is_player and self.player_faction is not None:
                        capture_team = self.player_faction
                    if s.owner != capture_team:
                        can_capture = (s.owner is None or
                                       self._are_hostile(army.team, s.owner))
                        if can_capture and army.army_strength > s.garrison_strength:
                            old_owner = s.owner
                            s.owner = capture_team
                            faction_names = {f.team: f.name for f in self.factions}
                            faction_names[0] = "You"
                            captor = faction_names.get(capture_team, "Unknown")
                            self._add_notification(f"{captor} captured {s.name}!")
                            self._territory_needs_update = True
                            # B7: Player capturing neutral settlement can found faction
                            if army.is_player and old_owner is None and self.player_faction is None:
                                self._found_player_faction(s)

    def _are_hostile(self, team_a, team_b):
        """Check if two teams are hostile (war or roaming vs faction)."""
        if team_a == team_b:
            return False
        # Roaming armies (bandits etc) are hostile to all factions
        roaming_teams = set(ROAMING_TYPES.keys())
        if team_a in roaming_teams and team_b not in roaming_teams:
            return True
        if team_b in roaming_teams and team_a not in roaming_teams:
            return True
        # Two different roaming types fight each other (except mercs)
        from campaign.faction import TEAM_MERCENARY
        if team_a in roaming_teams and team_b in roaming_teams:
            return team_a != TEAM_MERCENARY and team_b != TEAM_MERCENARY
        return self.diplomacy.are_at_war(team_a, team_b)

    def _resolve_ai_battles(self):
        """Auto-resolve battles between AI armies that collide."""
        to_remove = []
        winners = []
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
                        self._are_hostile(a1.team, a2.team) and
                        distance(a1.x, a1.y, a2.x, a2.y) < 30):
                    if a1.army_strength >= a2.army_strength:
                        for sq in a1.squads:
                            loss = int(sq.current_count * random.uniform(0.1, 0.3))
                            sq.current_count = max(1, sq.current_count - loss)
                        to_remove.append(a2)
                        winners.append(a1)
                    else:
                        for sq in a2.squads:
                            loss = int(sq.current_count * random.uniform(0.1, 0.3))
                            sq.current_count = max(1, sq.current_count - loss)
                        to_remove.append(a1)
                        winners.append(a2)
        for army in to_remove:
            if army in self.armies:
                self.armies.remove(army)
                # Clean up AI controller
                self.ai_controllers.pop(id(army), None)
        # B8: Record wins for roaming armies (stronghold escalation)
        for w in winners:
            self.roaming_manager.record_roaming_win(w)

    def _save_game(self):
        from core.save_system import save_campaign
        from core.audio import get_audio
        save_campaign(self)
        get_audio().play("save")
        self._save_notification_timer = 120
        self._add_notification("Game saved!")

    def update(self):
        self.camera.update()

        # D2: Apply seasonal movement penalty
        season = self._get_current_season()
        base_speed = CAMPAIGN_MOVE_SPEED
        if season == SEASON_WINTER:
            effective_speed = base_speed * SEASON_WINTER_MOVE_PENALTY
        elif season == SEASON_SUMMER:
            effective_speed = base_speed
        else:
            effective_speed = base_speed
        # Apply speed to all armies
        for army in self.armies:
            army.speed = effective_speed
            # D2: Desert factions get summer speed bonus
            if season == SEASON_SUMMER and army.team == 3:  # Desert Raiders
                army.speed = base_speed * SEASON_SUMMER_DESERT_SPEED_BONUS

        # Always update player movement (even when paused for responsiveness)
        self.player_army.update()

        # Tick save notification
        if hasattr(self, '_save_notification_timer') and self._save_notification_timer > 0:
            self._save_notification_timer -= 1

        # Update notifications
        self.notifications = [(text, timer - 1) for text, timer in self.notifications if timer > 1]

        # D6: Tick prisoner action message timer
        if getattr(self, 'prisoner_action_timer', 0) > 0:
            self.prisoner_action_timer -= 1
            if self.prisoner_action_timer <= 0:
                self.prisoner_action_msg = None

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
            if not self._are_hostile(0, army.team):
                continue
            # B13: Only trigger if army is visible (not in fog)
            if not self._is_visible(army.x, army.y):
                continue
            if distance(self.player_army.x, self.player_army.y,
                        army.x, army.y) < 25:
                # D1: Detect terrain at battle location
                battle_x = (self.player_army.x + army.x) / 2
                battle_y = (self.player_army.y + army.y) / 2
                terrain_type = self._get_terrain_at_position(battle_x, battle_y)
                self.pending_battle = (self.player_army, army, terrain_type)
                self.paused = True  # Auto-pause on battle contact
                return

    def _is_visible(self, x, y):
        """B13: Check if a world position is visible (not in fog)."""
        # Visible around player army
        if distance(self.player_army.x, self.player_army.y, x, y) <= CAMPAIGN_VISION_RADIUS:
            return True
        # Visible around owned/allied settlements
        for s in self.settlements:
            if s.owner == 0 or (s.owner is not None and self.diplomacy.are_allied(0, s.owner)):
                if distance(s.x, s.y, x, y) <= CAMPAIGN_SETTLEMENT_VISION:
                    return True
        return False

    def get_pending_battle(self):
        battle = self.pending_battle
        self.pending_battle = None
        return battle

    def remove_army(self, army):
        if army in self.armies:
            # B3: Record kill for quest tracking
            self.quest_manager.record_kill(army.team)
            self.armies.remove(army)
            self.ai_controllers.pop(id(army), None)

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

        # B8: Draw strongholds
        for sh in self.roaming_manager.strongholds:
            if self._is_visible(sh.x, sh.y):
                self._draw_stronghold(surface, sh)

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

        # B9: Settlement interaction overlay
        if self.settlement_interaction:
            self.settlement_interaction.draw(surface)
            return

        # Diplomacy overlay
        if self.show_diplomacy:
            self._draw_diplomacy(surface)

        # B3: Quest log overlay
        if getattr(self, 'show_quest_log', False):
            self._draw_quest_log(surface)

        # C4: Army management panel
        if getattr(self, 'show_army_panel', False):
            self._draw_army_panel(surface)

        # B6: Persuasion dialog
        if getattr(self, 'show_persuasion', False):
            self._draw_persuasion(surface)

        # D6: Prisoner management
        if getattr(self, 'show_prisoners', False):
            self._draw_prisoners(surface)

        # D5: Tournament overlay
        if self.show_tournament and self.active_tournament:
            self._draw_tournament(surface)

        # D6: Player capture overlay (drawn last, blocks everything)
        if self.general_manager.player_capture.is_captured:
            self._draw_capture_overlay(surface)

    def _draw_tournament(self, surface):
        """D5: Draw tournament bracket overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        font = get_font(36)
        med = get_font(24)
        small = get_font(20)

        panel_w, panel_h = 500, 400
        px = SCREEN_WIDTH // 2 - panel_w // 2
        py = SCREEN_HEIGHT // 2 - panel_h // 2
        pygame.draw.rect(surface, (30, 30, 40), (px, py, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (px, py, panel_w, panel_h), 2)

        t = self.active_tournament
        title = font.render("TOURNAMENT", True, GOLD)
        surface.blit(title, (px + panel_w // 2 - title.get_width() // 2, py + 15))

        y = py + 60
        # Show results
        for rnd, won, desc in t["results"]:
            color = (100, 200, 100) if won else (200, 100, 100)
            rt = small.render(desc, True, color)
            surface.blit(rt, (px + 20, y))
            y += 25

        y += 10
        if t["finished"]:
            if t["victory"]:
                result_text = med.render(f"CHAMPION! Total winnings: {t['gold_won']}g", True, GOLD)
            else:
                result_text = med.render(f"Eliminated. Winnings: {t['gold_won']}g", True, (200, 150, 100))
            surface.blit(result_text, (px + 20, y))
            y += 35
            close_text = med.render("[ENTER] Leave Tournament", True, WHITE)
            if pygame.time.get_ticks() % 1000 < 700:
                surface.blit(close_text, (px + panel_w // 2 - close_text.get_width() // 2, y))
        else:
            round_text = med.render(f"Round {t['round'] + 1} of {t['max_rounds']}", True, WHITE)
            surface.blit(round_text, (px + 20, y))
            y += 30
            fight_text = med.render("[ENTER] Fight Next Round", True, GOLD)
            if pygame.time.get_ticks() % 1000 < 700:
                surface.blit(fight_text, (px + panel_w // 2 - fight_text.get_width() // 2, y))

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

    def _draw_stronghold(self, surface, stronghold):
        """B8: Draw a roaming army stronghold on the map."""
        from campaign.roaming import StrongholdStage
        sx, sy = self.camera.world_to_screen(stronghold.x, stronghold.y)
        color = TEAM_COLORS.get(stronghold.team, GREY)
        r = self.camera.scale(15)
        if r < 3:
            return
        if stronghold.stage == StrongholdStage.STRONGHOLD:
            # Larger, fortified marker
            r = self.camera.scale(20)
            pygame.draw.rect(surface, color, (sx - r, sy - r, r * 2, r * 2))
            pygame.draw.rect(surface, (200, 200, 200), (sx - r, sy - r, r * 2, r * 2), 2)
        else:
            # Camp marker - triangle
            pts = [(sx, sy - r), (sx - r, sy + r), (sx + r, sy + r)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (200, 200, 200), pts, 1)
        if self.camera.zoom > 0.4:
            font = get_font(max(12, self.camera.scale(13)))
            text = font.render(stronghold.name, True, (220, 180, 180))
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 2))

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
        font = get_font(22)
        small_font = get_font(16)

        # Top bar (C2: improved)
        bar = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 200))
        surface.blit(bar, (0, 0))

        # D2: Day counter with season display
        season = self._get_current_season()
        season_colors = {
            SEASON_SPRING: (100, 200, 100),
            SEASON_SUMMER: (220, 200, 50),
            SEASON_AUTUMN: (200, 140, 50),
            SEASON_WINTER: (150, 200, 255),
        }
        season_color = season_colors.get(season, WHITE)
        day_text = font.render(f"Day {self.day} - {season.capitalize()}", True, season_color)
        surface.blit(day_text, (10, 8))

        # Gold
        gold_text = font.render(f"Gold: {self.player_army.gold}", True, GOLD)
        surface.blit(gold_text, (150, 8))

        # Speed controls (C2)
        speed_x = 260
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

        # Army info with B2 faction status and B11 army limit
        faction_str = "Independent"
        if self.player_faction is not None:
            f_obj = FACTION_BY_TEAM.get(self.player_faction)
            faction_str = f_obj.name if f_obj else f"Team {self.player_faction}"
        army_text = font.render(
            f"{faction_str} | "
            f"Army: {self.player_army.total_soldiers}/{self.player_army.army_size_limit} | "
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
            "[RMB] Move [E] Settlement [R] Recruit [D] Diplomacy "
            "[Q] Quests [A] Army [P] Persuade [J] Prisoners [SPACE] Pause",
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
            pause_text = get_font(36).render("PAUSED", True, (255, 200, 100))
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
        panel_h = 160 if self._is_tournament_available(s) else 140
        panel = pygame.Surface((250, panel_h), pygame.SRCALPHA)
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
            f" {self.diplomacy.get_state(0, s.owner).upper()}"
            if s.owner is not None and s.owner != 0 else "",
            True, (180, 180, 180))
        surface.blit(state_text, (x + 20, y))
        y += 20

        # D5: Tournament availability
        if self._is_tournament_available(s):
            tourney_text = small_font.render("Tournament available!", True, (255, 215, 0))
            surface.blit(tourney_text, (x, y))

    def _draw_diplomacy(self, surface):
        """Draw diplomacy overview panel."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 520, 580
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 40
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = get_font(28)
        small = get_font(20)
        tiny = get_font(16)

        title = font.render("Diplomacy & Relations", True, GOLD)
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
                if self.player_faction is None and rel >= FACTION_JOIN_THRESHOLD:
                    hint = tiny.render(f"  Press [{i+1}] to JOIN this faction!", True, (100, 255, 100))
                else:
                    hint = tiny.render(f"  Press [{i+1}] to propose alliance", True, (150, 150, 150))
            elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                hint = tiny.render(f"  Press [{i+1}] to declare war", True, (150, 150, 150))
            else:
                hint = tiny.render(f"  Allied", True, (100, 200, 255))
            surface.blit(hint, (panel_x + 30, y))
            y += 18

            owned = sum(1 for s in self.settlements if s.owner == faction.team)
            faction_armies = [a for a in self.armies if a.team == faction.team]
            info = tiny.render(
                f"  Settlements: {owned}  |  Armies: {len(faction_armies)}",
                True, (140, 140, 140))
            surface.blit(info, (panel_x + 30, y))
            y += 16

            # B12: Show individual general opinions
            for army in faction_armies[:2]:  # show up to 2 generals
                gen_opinion = self.diplomacy.get_general_opinion(army.general_name)
                gen_state = self.diplomacy.get_general_state(army.general_name)
                ai = self.ai_controllers.get(id(army))
                personality_str = f" ({ai.personality})" if ai else ""
                op_color = (100, 200, 100) if gen_opinion > 0 else (200, 100, 100) if gen_opinion < 0 else (150, 150, 150)
                gt = tiny.render(
                    f"    {army.general_name}{personality_str}: {gen_opinion:+d}",
                    True, op_color)
                surface.blit(gt, (panel_x + 30, y))
                y += 14
            y += 10

        # B2/B7: Show current faction status
        if self.player_faction is not None:
            if self.player_faction == 0:
                player_settlements = sum(1 for s in self.settlements if s.owner == 0)
                status = small.render(
                    f"Your Faction  |  Settlements: {player_settlements}  [L] Dissolve",
                    True, (100, 255, 200))
            else:
                f_obj = FACTION_BY_TEAM.get(self.player_faction)
                f_name = f_obj.name if f_obj else "Unknown"
                status = small.render(f"Vassal of {f_name}  [L] Leave Faction", True, (100, 200, 255))
            surface.blit(status, (panel_x + 15, y + 5))
        else:
            own_settlements = sum(1 for s in self.settlements if s.owner == 0)
            if own_settlements > 0:
                status = small.render("You own settlements! Capture a neutral one to found a faction.", True, (100, 255, 100))
            else:
                status = small.render("You are Independent. Reach +50 rep to join a faction, or capture a settlement.", True, (220, 160, 60))
            surface.blit(status, (panel_x + 15, y + 5))

        footer = tiny.render("[ESC] Close  |  Press number to interact", True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))

    def _draw_quest_log(self, surface):
        """B3: Draw quest log overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 500, 400
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 80
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = get_font(28)
        small = get_font(20)
        tiny = get_font(16)

        title = font.render("Quest Log", True, GOLD)
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

        y = panel_y + 45
        active = self.quest_manager.active_quests
        if not active:
            t = small.render("No active quests. Visit a settlement bounty board!", True, (150, 150, 150))
            surface.blit(t, (panel_x + 20, y))
        else:
            for q in active:
                # Quest title
                qt = small.render(q.title, True, WHITE)
                surface.blit(qt, (panel_x + 20, y))
                y += 20

                # Description
                desc = tiny.render(q.description, True, (160, 160, 160))
                surface.blit(desc, (panel_x + 30, y))
                y += 16

                # Progress
                progress_parts = []
                if q.is_kill_quest:
                    progress_parts.append(f"Kills: {q.kills_done}/{q.kill_count}")
                if q.time_limit > 0:
                    progress_parts.append(f"Days left: {q.days_remaining}")
                progress_parts.append(f"Reward: {q.gold_reward}g")
                prog = tiny.render("  ".join(progress_parts), True, (180, 180, 100))
                surface.blit(prog, (panel_x + 30, y))
                y += 22

        # Bounty board preview
        y = max(y + 10, panel_y + panel_h - 120)
        pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
        y += 5
        bb = small.render(f"Bounty Board ({len(self.quest_manager.bounty_board)} available)", True, (200, 180, 100))
        surface.blit(bb, (panel_x + 20, y))
        y += 22
        for q in self.quest_manager.bounty_board[:3]:
            qt = tiny.render(f"  {q.title} - {q.gold_reward}g", True, (140, 140, 140))
            surface.blit(qt, (panel_x + 20, y))
            y += 16

        footer = tiny.render("[Q] Close  |  Accept quests at settlement bounty boards", True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))

    # ------------------------------------------------------------------
    # B6: Persuasion UI
    # ------------------------------------------------------------------

    def _try_persuasion(self):
        """B6: Try to open persuasion dialog with a nearby non-hostile army."""
        if self.general_manager.player_capture.is_captured:
            self._add_notification("Cannot persuade while captured!")
            return
        for army in self.armies:
            if army.is_player or army.team == 0:
                continue
            # Must not be at war
            if self._are_hostile(0, army.team):
                continue
            if distance(self.player_army.x, self.player_army.y,
                        army.x, army.y) < PERSUASION_RANGE:
                self.persuasion_target = army
                self.show_persuasion = True
                self.paused = True
                return
        self._add_notification("No generals nearby to persuade. Move closer to a non-hostile army.")

    def _handle_persuasion_event(self, event):
        """Handle input on the persuasion dialog."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            self.show_persuasion = False
            self.persuasion_target = None
            self.paused = False
            return None

        target = self.persuasion_target
        if target is None:
            self.show_persuasion = False
            return None

        name = target.general_name
        gm = self.general_manager

        if event.key == pygame.K_1:
            # Bribe
            success, msg = gm.attempt_bribe(name, self.player_army, self.diplomacy)
            self._add_notification(msg)
        elif event.key == pygame.K_2:
            # Convince
            success, msg = gm.attempt_convince(name, self.player_army, self.diplomacy)
            self._add_notification(msg)
        elif event.key == pygame.K_3:
            # Threaten
            success, msg = gm.attempt_threaten(name, self.player_army, self.diplomacy)
            self._add_notification(msg)
        else:
            return None

        # Close after action
        self.show_persuasion = False
        self.persuasion_target = None
        self.paused = False
        return None

    def _draw_persuasion(self, surface):
        """B6: Draw persuasion dialog overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        target = self.persuasion_target
        if target is None:
            return

        panel_w, panel_h = 460, 340
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 100
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = get_font(28)
        small = get_font(20)
        tiny = get_font(16)

        title = font.render("Persuade General", True, GOLD)
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

        y = panel_y + 50
        name = target.general_name
        gm = self.general_manager
        info = gm.generals.get(name, {})
        loyalty = info.get("loyalty", 70)
        personality = info.get("personality", "unknown")
        gen_opinion = self.diplomacy.get_general_opinion(name)
        faction_name = "Unknown"
        for f in self.factions:
            if f.team == target.team:
                faction_name = f.name
                break

        # General info
        name_text = small.render(f"General: {name}", True, WHITE)
        surface.blit(name_text, (panel_x + 20, y))
        y += 22
        faction_text = small.render(f"Faction: {faction_name}", True,
                                     TEAM_COLORS.get(target.team, GREY))
        surface.blit(faction_text, (panel_x + 20, y))
        y += 22
        pers_text = small.render(f"Personality: {personality}", True, (180, 180, 180))
        surface.blit(pers_text, (panel_x + 20, y))
        y += 22
        loyalty_color = (100, 200, 100) if loyalty > 50 else (200, 200, 60) if loyalty > 30 else (200, 80, 80)
        loyalty_text = small.render(f"Loyalty to faction: {loyalty}", True, loyalty_color)
        surface.blit(loyalty_text, (panel_x + 20, y))
        y += 22
        op_color = (100, 200, 100) if gen_opinion > 0 else (200, 100, 100) if gen_opinion < 0 else (150, 150, 150)
        opinion_text = small.render(f"Opinion of you: {gen_opinion:+d}", True, op_color)
        surface.blit(opinion_text, (panel_x + 20, y))
        y += 30

        # Options
        pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
        y += 10

        from core.settings import BRIBE_COST_BASE
        bribe_cost = BRIBE_COST_BASE
        if personality == "greedy":
            bribe_cost = int(bribe_cost * 0.7)
        elif personality == "loyal":
            bribe_cost = int(bribe_cost * 1.5)

        options = [
            (f"[1] Bribe ({bribe_cost} gold)", (255, 215, 0)),
            ("[2] Convince (persuasion check)", (100, 200, 255)),
            ("[3] Threaten (risky on aggressive)", (255, 100, 100)),
        ]
        for text, color in options:
            opt = small.render(text, True, color)
            surface.blit(opt, (panel_x + 30, y))
            y += 28

        footer = tiny.render("[ESC] Cancel  |  Press 1/2/3 to choose", True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))

    # ------------------------------------------------------------------
    # D6: Prisoner management UI
    # ------------------------------------------------------------------

    def _handle_prisoner_event(self, event):
        """Handle input on the prisoner management panel."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_j:
            self.show_prisoners = False
            self.paused = False
            self.prisoner_action_msg = None
            return None

        gm = self.general_manager
        prisoners = gm.player_prisoners

        if not prisoners:
            self.show_prisoners = False
            self.paused = False
            return None

        # Number keys select prisoner (1-indexed)
        if pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            if idx < len(prisoners):
                # Store selected prisoner index for sub-actions
                self._prisoner_selected = idx
                self.prisoner_action_msg = f"Selected {prisoners[idx].general_name}. [R]ansom / [C]recruit / [X]execute"
                self.prisoner_action_timer = 300
            return None

        selected = getattr(self, '_prisoner_selected', None)
        if selected is not None and selected < len(prisoners):
            if event.key == pygame.K_r:
                # Ransom
                gold, msg = gm.ransom_prisoner(selected, self.diplomacy)
                if gold > 0:
                    self.player_army.gold += gold
                self._add_notification(msg)
                self.prisoner_action_msg = msg
                self.prisoner_action_timer = 180
                self._prisoner_selected = None
            elif event.key == pygame.K_c:
                # Recruit
                success, msg, prisoner_data = gm.recruit_prisoner(selected, self.diplomacy)
                self._add_notification(msg)
                self.prisoner_action_msg = msg
                self.prisoner_action_timer = 180
                self._prisoner_selected = None
            elif event.key == pygame.K_x:
                # Execute
                msg = gm.execute_prisoner(selected, self.diplomacy, self.factions)
                self._add_notification(msg)
                self.prisoner_action_msg = msg
                self.prisoner_action_timer = 180
                self._prisoner_selected = None

        if not gm.player_prisoners:
            self.show_prisoners = False
            self.paused = False

        return None

    def _draw_prisoners(self, surface):
        """D6: Draw prisoner management panel."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        gm = self.general_manager
        prisoners = gm.player_prisoners

        panel_w, panel_h = 500, 420
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 80
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = get_font(28)
        small = get_font(20)
        tiny = get_font(16)

        title = font.render("Prisoners", True, GOLD)
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

        y = panel_y + 50
        if not prisoners:
            t = small.render("No prisoners held.", True, (150, 150, 150))
            surface.blit(t, (panel_x + 20, y))
        else:
            selected = getattr(self, '_prisoner_selected', None)
            for i, p in enumerate(prisoners):
                is_selected = (i == selected)
                bg = (50, 50, 70) if is_selected else (35, 35, 50)
                row_rect = (panel_x + 10, y, panel_w - 20, 40)
                pygame.draw.rect(surface, bg, row_rect)
                if is_selected:
                    pygame.draw.rect(surface, GOLD, row_rect, 1)

                faction_name = "Unknown"
                for f in self.factions:
                    if f.team == p.faction_team:
                        faction_name = f.name
                        break

                name_text = small.render(
                    f"[{i+1}] {p.general_name} (Lv{p.general_level})", True, WHITE)
                surface.blit(name_text, (panel_x + 15, y + 2))

                info_text = tiny.render(
                    f"    {faction_name} | {p.personality} | Held {p.days_held} days",
                    True, (160, 160, 160))
                surface.blit(info_text, (panel_x + 15, y + 22))
                y += 44

        # Action message
        if getattr(self, 'prisoner_action_msg', None):
            y += 10
            msg_text = small.render(self.prisoner_action_msg, True, (255, 220, 100))
            surface.blit(msg_text, (panel_x + 15, y))

        footer = tiny.render(
            "[1-9] Select  |  [R]ansom [C]recruit [X]execute  |  [J/ESC] Close",
            True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))

    # ------------------------------------------------------------------
    # D6: Player capture UI
    # ------------------------------------------------------------------

    def _handle_capture_event(self, event):
        """Handle input while player is captured."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_r:
            success, msg = self.general_manager.pay_player_ransom(self.player_army)
            self._add_notification(msg)
        return None

    def _draw_capture_overlay(self, surface):
        """D6: Draw player capture state overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        cap = self.general_manager.player_capture
        font = get_font(40)
        small = get_font(24)
        tiny = get_font(18)

        title = font.render("YOU ARE CAPTURED", True, (220, 60, 60))
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))

        captor_name = "Unknown"
        for f in self.factions:
            if f.team == cap.captor_team:
                captor_name = f.name
                break

        y = 260
        info_lines = [
            f"Held by: {captor_name}",
            f"Days remaining: {cap.days_remaining}",
            f"Ransom cost: {cap.ransom_cost} gold (you have {self.player_army.gold})",
            "",
            "Your army is dispersing while you are held captive.",
            "You will automatically escape when the timer runs out,",
            "but your army will be weakened.",
        ]
        for line in info_lines:
            text = small.render(line, True, WHITE)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 28

        if self.player_army.gold >= cap.ransom_cost:
            opt = small.render("[R] Pay Ransom", True, GOLD)
        else:
            opt = small.render("[R] Pay Ransom (not enough gold)", True, (120, 120, 120))
        surface.blit(opt, (SCREEN_WIDTH // 2 - opt.get_width() // 2, y + 20))

        wait = tiny.render("Or wait for automatic escape...", True, (150, 150, 150))
        surface.blit(wait, (SCREEN_WIDTH // 2 - wait.get_width() // 2, y + 50))

    def _handle_army_panel_event(self, event):
        """C4: Handle army management panel input."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_a:
                self.show_army_panel = False
                return None
            # Number keys to disband squads (requires double-press to confirm)
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(self.player_army.squads):
                    pending = getattr(self, '_disband_pending', None)
                    if pending == idx:
                        # Confirmed - disband
                        if len(self.player_army.squads) > 1:
                            sq = self.player_army.squads[idx]
                            self.player_army.remove_squad(idx)
                            self._add_notification(f"Disbanded {sq.unit_stats.name}.")
                        else:
                            self._add_notification("Cannot disband your last squad!")
                        self._disband_pending = None
                    else:
                        # First press - ask for confirmation
                        sq = self.player_army.squads[idx]
                        self._add_notification(f"Press {idx+1} again to confirm disband {sq.unit_stats.name}")
                        self._disband_pending = idx
            # Move squads up/down with arrow keys (reorder)
            if event.key == pygame.K_UP:
                self._army_panel_selected = max(0,
                    getattr(self, '_army_panel_selected', 0) - 1)
            elif event.key == pygame.K_DOWN:
                self._army_panel_selected = min(
                    len(self.player_army.squads) - 1,
                    getattr(self, '_army_panel_selected', 0) + 1)
        return None

    def _draw_army_panel(self, surface):
        """C4: Draw army management panel."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        panel_w, panel_h = 500, 500
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = 60
        pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        font = get_font(28)
        small = get_font(20)
        tiny = get_font(16)

        title = font.render("Army Management", True, GOLD)
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

        # General info
        y = panel_y + 45
        pa = self.player_army
        gen_info = small.render(
            f"General: {pa.general_name} ({pa.general_stats.name}) Lv{pa.general_level}",
            True, WHITE)
        surface.blit(gen_info, (panel_x + 15, y))
        y += 22

        army_info = small.render(
            f"Army: {pa.total_soldiers}/{pa.army_size_limit} soldiers  |  "
            f"Strength: {pa.army_strength}  |  Upkeep: {pa.upkeep}/day",
            True, (180, 180, 180))
        surface.blit(army_info, (panel_x + 15, y))
        y += 22

        gold_info = small.render(f"Gold: {pa.gold}", True, GOLD)
        surface.blit(gold_info, (panel_x + 15, y))
        y += 28

        # Squad list
        pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
        y += 8

        header = tiny.render(
            f"{'#':<3} {'Unit':<22} {'Count':>8} {'Rank':<12} {'Kills':>6} {'Str':>6}",
            True, (140, 140, 140))
        surface.blit(header, (panel_x + 15, y))
        y += 18

        selected = getattr(self, '_army_panel_selected', 0)
        for i, sq in enumerate(pa.squads):
            is_selected = (i == selected)
            bg_color = (50, 50, 70) if is_selected else (35, 35, 50)
            row_rect = (panel_x + 10, y, panel_w - 20, 22)
            pygame.draw.rect(surface, bg_color, row_rect)
            if is_selected:
                pygame.draw.rect(surface, GOLD, row_rect, 1)

            count_str = f"{sq.current_count}/{sq.max_count}" if sq.is_understrength else str(sq.current_count)
            rank_str = sq.rank_name if sq.battles_survived > 0 else "-"

            line = tiny.render(
                f"[{i+1}] {sq.unit_stats.name:<22} {count_str:>8} {rank_str:<12} {sq.total_kills:>6} {sq.strength:>6}",
                True, WHITE)
            surface.blit(line, (panel_x + 15, y + 3))
            y += 24

        # Stats summary
        y += 10
        pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
        y += 8
        total_kills = sum(sq.total_kills for sq in pa.squads)
        summary = small.render(
            f"Total Squads: {len(pa.squads)}  |  Total Kills: {total_kills}",
            True, WHITE)
        surface.blit(summary, (panel_x + 15, y))

        footer = tiny.render(
            "[A/ESC] Close  |  [1-9] Disband squad  |  Arrows to select",
            True, (150, 150, 150))
        surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                              panel_y + panel_h - 25))
