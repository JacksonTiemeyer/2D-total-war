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
from campaign.runtime import consume_pending_battle, queue_pending_battle, update_campaign
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
    Army, create_default_player_army, create_racial_player_army, create_enemy_army,
)
from campaign.settlement_ui import SettlementInteraction
from campaign.ai_controller import ArmyAI, pick_personality, AITask
from campaign.roaming import RoamingManager, ROAMING_TYPES
from campaign.quest import QuestManager
from data.unit_types import ALL_RECRUITABLE, GENERAL_ROSTER
from campaign.faction import FACTION_ROSTER, FACTION_BY_TEAM
from campaign.diplomacy import DiplomacyManager, DiplomacyState
from campaign.generals import GeneralManager
from campaign.player import PlayerCharacter, get_tier_for_level
from campaign.companion import CompanionManager, generate_tavern_companions
import campaign.ui as campaign_ui
import campaign.map_rendering as map_rendering
import campaign.input_handlers as input_handlers


class CampaignScene:
    def __init__(self, player_character=None):
        self.camera = Camera(CAMPAIGN_MAP_WIDTH, CAMPAIGN_MAP_HEIGHT)
        self.camera.center_on(CAMPAIGN_MAP_WIDTH / 2, CAMPAIGN_MAP_HEIGHT / 2)

        # Real-time campaign state (B1)
        self.day = 1
        self.day_ticks = 0  # ticks within current day
        self.campaign_speed = CAMPAIGN_SPEED_1X
        self.paused = False

        # Legacy turn counter (for save compat)
        self.turn = 1

        # Phase 3: Player character integration
        self.player_character = player_character
        if player_character:
            self.player_army = create_racial_player_army(player_character)
            # Set starting position based on race
            start_pos = self._get_race_start_position(player_character.race)
            self.player_army.x, self.player_army.y = start_pos
            self.player_army.target_x = self.player_army.x
            self.player_army.target_y = self.player_army.y
            # Apply starting trait bonuses
            if player_character.trait == "veteran_campaigner":
                self.player_army.general_level = 3
            self.camera.center_on(self.player_army.x, self.player_army.y)
        else:
            self.player_army = create_default_player_army()

        self.armies = [self.player_army]
        self.settlements = []
        self.selected_settlement = None
        self.show_diplomacy = False
        self.show_quest_log = False
        self.show_army_panel = False
        self._diplomacy_scroll = 0  # scroll offset for diplomacy panel
        self.pending_battle = None  # PendingBattle handoff contract
        self._siege_settlement = None  # settlement being besieged
        self._selected_army = None     # clicked NPC army for info display
        self._pending_map_interaction = None
        self._last_click_time = 0
        self._last_click_signature = None

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
        self.trade_warning = None

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

        # Companion system
        self.companion_manager = CompanionManager()
        self.show_companions = False
        self.show_tavern = False
        self._tavern_companions = []
        self._tavern_settlement = None
        self.prisoner_action_msg = None   # feedback message for prisoner actions
        self.prisoner_action_timer = 0

        # D1: Terrain zones — expanded for 6000x4500 map
        self._terrain_forests = [
            # Northwest - Wood Elf territory
            (400, 600, 180), (700, 400, 150), (500, 900, 140),
            (900, 700, 120), (300, 1100, 100), (1100, 500, 110),
            (600, 1300, 90), (800, 1100, 130),
            # Central scattered
            (2200, 1800, 100), (2800, 2200, 80), (1800, 2500, 90),
            # Eastern
            (4200, 1200, 100), (4500, 800, 80),
        ]
        self._terrain_mountains = [
            # Northeast - Dwarf territory
            (4200, 400, 120), (4500, 600, 100), (4800, 300, 90),
            (4000, 200, 80), (4600, 500, 110), (4300, 800, 70),
            # Central ridge
            (2800, 1000, 60), (3000, 600, 50),
            # Wild Mountains - Troll/Ogre
            (3500, 2800, 100), (3800, 3000, 90), (3200, 3200, 80),
            # Far North peaks
            (2000, 200, 70), (2500, 150, 60),
        ]
        self._terrain_deserts = [
            # Southeast - Orc Wastes
            (4500, 3200, 250), (5000, 3500, 200), (4800, 3800, 180),
            (4200, 3600, 150), (5200, 3000, 120),
        ]
        self._terrain_water = [
            # Southwest coast - Sea Elf
            (400, 3500, 300), (800, 3800, 250), (200, 4000, 200),
            (1200, 4000, 200), (600, 4200, 180),
            # Central lake
            (2800, 2800, 150),
        ]

        # D5: Tournament state
        self.tournament_towns = {}  # settlement_name -> next_tournament_day
        self.active_tournament = None  # dict with tournament state or None
        self.show_tournament = False

        self._generate_world()
        self._init_ai_controllers()
        self._register_generals()
        self._update_trade_connectivity_warning()
        self._add_notification("You begin as an independent lord. Visit settlements to recruit and trade!")

    def _add_notification(self, text):
        """Add a notification to the feed."""
        self.notifications.append((text, self.NOTIFICATION_DURATION))

    def _get_race_start_position(self, race_id):
        """Return (x, y) starting position for a given race on the 6000x4500 map."""
        positions = {
            "human": (2400, 1600),       # Central Plains
            "high_elf": (4600, 1300),    # Eastern Highlands
            "wood_elf": (600, 800),      # Northwest Forests
            "sea_elf": (600, 3600),      # Southwest Coast
            "snow_elf": (2200, 400),     # Far North Tundra
            "dark_elf": (1400, 3800),    # Underground South
            "dwarf": (4400, 500),        # Northeast Mountains
            "orc": (4800, 3500),         # Southeast Wastes
            "undead": (3400, 2700),      # Cursed Lands
            "troll_ogre": (3600, 3100),  # Wild Mountains
            "beastfolk": (2200, 3600),   # Southern Steppes
        }
        return positions.get(race_id, (3000, 2250))  # center fallback

    def _generate_world(self):
        """Generate campaign map with 70+ settlements across 13 racial factions."""
        # Phase 3: 70+ settlements on 6000x4500 map
        settlement_data = [
            # ── Neutral/Unclaimed (contested border regions) ──
            ("Crossroads Inn", 2800, 1800, SettlementType.VILLAGE, None),
            ("Trader's Rest", 2400, 2200, SettlementType.VILLAGE, None),
            ("Ruined Outpost", 3200, 1400, SettlementType.VILLAGE, None),
            ("Borderwatch", 2000, 1200, SettlementType.VILLAGE, None),
            ("Pilgrim's Ford", 1800, 2800, SettlementType.VILLAGE, None),

            # ── Human Kingdoms (team 1) — Central Plains ──  12 settlements
            ("King's Landing", 2600, 1600, SettlementType.CASTLE, 1),
            ("Ironhold", 2400, 1400, SettlementType.CASTLE, 1),
            ("Goldenhall", 2800, 1200, SettlementType.CASTLE, 1),
            ("Millbrook", 2200, 1600, SettlementType.TOWN, 1),
            ("Ashvale", 2600, 1200, SettlementType.TOWN, 1),
            ("Brightwater", 3000, 1600, SettlementType.TOWN, 1),
            ("Thornfield", 2400, 1800, SettlementType.TOWN, 1),
            ("Haywick", 2200, 1200, SettlementType.VILLAGE, 1),
            ("Oxbridge", 2800, 1400, SettlementType.VILLAGE, 1),
            ("Millhaven", 2600, 2000, SettlementType.VILLAGE, 1),
            ("Barley Cross", 3000, 1800, SettlementType.VILLAGE, 1),
            ("Shepherd's Gate", 2000, 1600, SettlementType.VILLAGE, 1),

            # ── High Elf Dominion (team 2) — Eastern Highlands ──  7 settlements
            ("Arcane Spire", 4800, 1400, SettlementType.CASTLE, 2),
            ("Crystal Citadel", 5000, 1200, SettlementType.CASTLE, 2),
            ("Starfall", 4600, 1200, SettlementType.TOWN, 2),
            ("Moonhaven", 5200, 1400, SettlementType.TOWN, 2),
            ("Silver Grove", 4400, 1400, SettlementType.VILLAGE, 2),
            ("Aetherium", 5000, 1000, SettlementType.VILLAGE, 2),
            ("Luminara", 4600, 1600, SettlementType.VILLAGE, 2),

            # ── Wood Elf Enclave (team 3) — Northwest Forests ──  6 settlements
            ("Deepwood Hold", 600, 700, SettlementType.CASTLE, 3),
            ("Oakenheart", 400, 1000, SettlementType.TOWN, 3),
            ("Greenfield", 800, 500, SettlementType.TOWN, 3),
            ("Willowmere", 600, 1200, SettlementType.VILLAGE, 3),
            ("Mosshollow", 900, 800, SettlementType.VILLAGE, 3),
            ("Fernvale", 300, 600, SettlementType.VILLAGE, 3),

            # ── Sea Elf Corsairs (team 4) — Southwest Coast ──  6 settlements
            ("Tidecrest", 600, 3600, SettlementType.CASTLE, 4),
            ("Portmere", 400, 3200, SettlementType.TOWN, 4),
            ("Coral Haven", 800, 4000, SettlementType.TOWN, 4),
            ("Storm Harbor", 1000, 3800, SettlementType.TOWN, 4),
            ("Saltmere", 200, 3800, SettlementType.VILLAGE, 4),
            ("Shell Cove", 600, 4200, SettlementType.VILLAGE, 4),

            # ── Snow Elf Khanate (team 5) — Far North Tundra ──  6 settlements
            ("Frosthaven", 2200, 300, SettlementType.CASTLE, 5),
            ("Winterhold", 1800, 200, SettlementType.CASTLE, 5),
            ("Icewatch", 2600, 400, SettlementType.TOWN, 5),
            ("Snowpeak", 2000, 500, SettlementType.VILLAGE, 5),
            ("Glacial Shrine", 2400, 200, SettlementType.VILLAGE, 5),
            ("Tundra Camp", 1600, 400, SettlementType.VILLAGE, 5),

            # ── Dark Elf Cabal (team 6) — Underground/South ──  6 settlements
            ("Naggarond", 1400, 3800, SettlementType.CASTLE, 6),
            ("Shadow Gate", 1600, 4000, SettlementType.CASTLE, 6),
            ("Darkhaven", 1200, 3600, SettlementType.TOWN, 6),
            ("Venom Pit", 1800, 3800, SettlementType.TOWN, 6),
            ("Slave Market", 1400, 4200, SettlementType.VILLAGE, 6),
            ("Web Cavern", 1000, 4000, SettlementType.VILLAGE, 6),

            # ── Dwarf Holds (team 7) — Northeast Mountains ──  7 settlements
            ("Karaz-a-Karak", 4400, 400, SettlementType.CASTLE, 7),
            ("Iron Peak", 4600, 600, SettlementType.CASTLE, 7),
            ("Barak Varr", 4200, 600, SettlementType.CASTLE, 7),
            ("Hammer's Fall", 4800, 400, SettlementType.TOWN, 7),
            ("Anvil Deep", 4400, 800, SettlementType.TOWN, 7),
            ("Gold Mine", 4000, 400, SettlementType.VILLAGE, 7),
            ("Grudge Keep", 4600, 200, SettlementType.VILLAGE, 7),

            # ── Orc Waaagh! (team 8) — Southeast Wastes ──  7 settlements
            ("Skullcrush Fort", 4800, 3400, SettlementType.CASTLE, 8),
            ("Red Toof Camp", 5000, 3600, SettlementType.TOWN, 8),
            ("Gork's Pit", 4600, 3600, SettlementType.TOWN, 8),
            ("Waaagh Camp", 5200, 3200, SettlementType.VILLAGE, 8),
            ("Bone Pile", 4400, 3800, SettlementType.VILLAGE, 8),
            ("Mushroom Cave", 5000, 3200, SettlementType.VILLAGE, 8),
            ("Rusty Spear", 4800, 4000, SettlementType.VILLAGE, 8),

            # ── Undead Legion (team 9) — Cursed Lands (scattered) ──  6 settlements
            ("Drakenhof", 3400, 2600, SettlementType.CASTLE, 9),
            ("Bone Citadel", 3200, 3000, SettlementType.CASTLE, 9),
            ("Corpse Garden", 3600, 2800, SettlementType.TOWN, 9),
            ("Wight Barrow", 3000, 2800, SettlementType.VILLAGE, 9),
            ("Plague Moor", 3400, 3200, SettlementType.VILLAGE, 9),
            ("Tomb of Kings", 3800, 2600, SettlementType.VILLAGE, 9),

            # ── Troll & Ogre Tribes (team 10) — Wild Mountains ──  4 settlements
            ("Gianthold", 3600, 3000, SettlementType.CASTLE, 10),
            ("Ogre Camp", 3400, 3400, SettlementType.TOWN, 10),
            ("Troll Den", 3800, 3200, SettlementType.VILLAGE, 10),
            ("Stone Circle", 3200, 3600, SettlementType.VILLAGE, 10),

            # ── Beastfolk Warherds (team 11) — Southern Steppes ──  3 settlements
            ("Herdstone", 2200, 3600, SettlementType.TOWN, 11),
            ("Beast Hollow", 2400, 3800, SettlementType.VILLAGE, 11),
            ("Bloodground", 2000, 3400, SettlementType.VILLAGE, 11),
        ]
        for name, x, y, stype, owner in settlement_data:
            self.settlements.append(Settlement(name, x, y, owner, stype))

        # ── Racial Armies (3-5 per faction) ──

        # Human Kingdoms (team 1)
        for name, x, y in [("King's Guard", 2500, 1500),
                            ("Lord Varro's Host", 2700, 1300),
                            ("Baron Thorne's Guard", 2300, 1700),
                            ("Imperial Vanguard", 2900, 1500)]:
            self.armies.append(create_enemy_army(name, 1, x, y, random.randint(2, 3)))

        # High Elf Dominion (team 2)
        for name, x, y in [("Phoenix Guard", 4700, 1300),
                            ("Silver Host", 5100, 1300),
                            ("Arcane Wardens", 4500, 1500)]:
            self.armies.append(create_enemy_army(name, 2, x, y, random.randint(2, 3)))

        # Wood Elf Enclave (team 3)
        for name, x, y in [("Glade Wardens", 700, 600),
                            ("Shadow Patrol", 500, 900),
                            ("Forest Sentinels", 800, 1100)]:
            self.armies.append(create_enemy_army(name, 3, x, y, random.randint(1, 2)))

        # Sea Elf Corsairs (team 4)
        for name, x, y in [("Corsair Fleet", 500, 3500),
                            ("Tide Warriors", 700, 3900),
                            ("Storm Raiders", 900, 3700)]:
            self.armies.append(create_enemy_army(name, 4, x, y, random.randint(1, 2)))

        # Snow Elf Khanate (team 5)
        for name, x, y in [("Frost Guard", 2100, 400),
                            ("Ice Riders", 2500, 300),
                            ("Tundra Patrol", 1900, 300)]:
            self.armies.append(create_enemy_army(name, 5, x, y, random.randint(1, 2)))

        # Dark Elf Cabal (team 6)
        for name, x, y in [("Shadow Host", 1300, 3700),
                            ("Witch King's Guard", 1500, 3900),
                            ("Dark Raiders", 1700, 3700)]:
            self.armies.append(create_enemy_army(name, 6, x, y, random.randint(2, 3)))

        # Dwarf Holds (team 7)
        for name, x, y in [("Ironbreaker Regiment", 4300, 500),
                            ("Thunderer Brigade", 4500, 700),
                            ("Slayer Expedition", 4700, 500),
                            ("Engineer Corps", 4100, 500)]:
            self.armies.append(create_enemy_army(name, 7, x, y, random.randint(1, 2)))

        # Orc Waaagh! (team 8)
        for name, x, y in [("Grimgor's Boyz", 4700, 3500),
                            ("Da Red Toof", 5100, 3500),
                            ("Skull Smashers", 4500, 3700),
                            ("Wolf Rider Pack", 4900, 3300)]:
            self.armies.append(create_enemy_army(name, 8, x, y, random.randint(2, 3)))

        # Undead Legion (team 9)
        for name, x, y in [("Skeleton Horde", 3300, 2700),
                            ("Grave March", 3500, 2900),
                            ("Wight Host", 3100, 2900)]:
            self.armies.append(create_enemy_army(name, 9, x, y, random.randint(2, 3)))

        # Troll & Ogre Tribes (team 10)
        for name, x, y in [("Ogre Warband", 3500, 3100),
                            ("Troll Horde", 3700, 3300)]:
            self.armies.append(create_enemy_army(name, 10, x, y, random.randint(1, 2)))

        # Beastfolk Warherds (team 11)
        for name, x, y in [("Minotaur Warband", 2300, 3700),
                            ("Beastherd", 2100, 3500)]:
            self.armies.append(create_enemy_army(name, 11, x, y, random.randint(1, 2)))

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

        # Companion panel overlay
        if self.show_companions:
            return self._handle_companion_event(event)

        # Tavern panel overlay
        if self.show_tavern:
            return self._handle_tavern_event(event)

        # D6: Player capture overlay
        if self.general_manager.player_capture.is_captured:
            return self._handle_capture_event(event)

        self.camera.handle_event(event)

        if event.type == pygame.KEYDOWN:
            # B1: Real-time controls
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
                if self.paused:
                    # Cancel any in-progress move so the army doesn't
                    # continue (or auto-resume) after unpausing.
                    self.player_army.moving = False
                    self.player_army.target_x = self.player_army.x
                    self.player_army.target_y = self.player_army.y
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
                    # Stop movement while prisoner overlay is active.
                    self.player_army.moving = False
                    self.player_army.target_x = self.player_army.x
                    self.player_army.target_y = self.player_army.y
                else:
                    self._add_notification("No prisoners held.")
            elif event.key == pygame.K_n:
                self.show_companions = not self.show_companions
            elif event.key == pygame.K_t:
                # Check if near a friendly settlement for tavern
                for s in self.settlements:
                    if s.owner == self.player_army.team or s.owner is None:
                        if distance(self.player_army.x, self.player_army.y, s.x, s.y) < 60:
                            self._tavern_settlement = s
                            self._tavern_companions = generate_tavern_companions(
                                s.name, self.day,
                                self.player_character.level if self.player_character else 1)
                            self.show_tavern = True
                            break
                else:
                    self._add_notification("No friendly settlement nearby for tavern.")
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self._save_game()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                self._handle_right_click(event.pos)

        return None  # no scene transition

    def _handle_left_click(self, pos):
        input_handlers.handle_left_click(self, pos)

    def _is_double_click(self, click_signature):
        """Return True when the same map target is clicked twice quickly."""
        return input_handlers.is_double_click(self, click_signature)

    def _handle_top_bar_click(self, pos):
        """Handle clicks on the top bar (speed controls)."""
        input_handlers.handle_top_bar_click(self, pos)

    def _handle_bottom_bar_click(self, pos):
        """Handle clicks on the bottom bar."""
        input_handlers.handle_bottom_bar_click(self, pos)

    def _handle_right_click(self, pos):
        input_handlers.handle_right_click(self, pos)

    def _interact_with_settlement(self, settlement):
        """Smart settlement interaction for double-clicks."""
        if distance(self.player_army.x, self.player_army.y, settlement.x, settlement.y) < 60:
            self._try_enter_settlement(settlement)
        else:
            self._queue_map_interaction("settlement", settlement, settlement.x, settlement.y)

    def _interact_with_army(self, army):
        """Smart general interaction for double-clicks."""
        if self._are_hostile(0, army.team):
            if distance(self.player_army.x, self.player_army.y, army.x, army.y) < 25:
                battle_x = (self.player_army.x + army.x) / 2
                battle_y = (self.player_army.y + army.y) / 2
                terrain_type = self._get_terrain_at_position(battle_x, battle_y)
                queue_pending_battle(self, army, terrain_type)
                self.paused = True
            else:
                self._queue_map_interaction("army", army, army.x, army.y)
            return

        if distance(self.player_army.x, self.player_army.y, army.x, army.y) < PERSUASION_RANGE:
            self.persuasion_target = army
            self.show_persuasion = True
            self.paused = True
        else:
            self._queue_map_interaction("army", army, army.x, army.y)

    def _queue_map_interaction(self, target_type, target, x, y):
        """Move the player army toward a target, then interact on arrival."""
        self._pending_map_interaction = {"type": target_type, "target": target}
        self.player_army.give_move_order(x, y)
        label = target.name if target_type == "settlement" else target.general_name
        self._add_notification(f"Moving to {label}...")

    def _update_pending_map_interaction(self):
        """Resolve queued double-click interactions once the player arrives."""
        if self.paused or not self._pending_map_interaction:
            return

        interaction = self._pending_map_interaction
        target = interaction["target"]
        if interaction["type"] == "settlement":
            if target not in self.settlements:
                self._pending_map_interaction = None
                return
            if distance(self.player_army.x, self.player_army.y, target.x, target.y) < 60:
                self._pending_map_interaction = None
                self._try_enter_settlement(target)
        else:
            if target not in self.armies or target.is_player:
                self._pending_map_interaction = None
                return
            if (not self._are_hostile(0, target.team) and
                    distance(self.player_army.x, self.player_army.y, target.x, target.y) < PERSUASION_RANGE):
                self._pending_map_interaction = None
                self._interact_with_army(target)
                return
            if self.player_army.moving:
                self.player_army.target_x = target.x
                self.player_army.target_y = target.y
            elif self._are_hostile(0, target.team):
                self.player_army.give_move_order(target.x, target.y)
            else:
                self.player_army.give_move_order(target.x, target.y)

    def _try_enter_settlement(self, target_settlement=None):
        """B9: Try to enter a nearby settlement for interaction, or siege if hostile."""
        settlements = [target_settlement] if target_settlement else self.settlements
        for s in settlements:
            if s is None:
                continue
            if distance(self.player_army.x, self.player_army.y, s.x, s.y) < 60:
                # Hostile settlement -> trigger siege battle
                if s.owner is not None and self.diplomacy.are_at_war(0, s.owner):
                    terrain_type = self._get_terrain_at_position(s.x, s.y)
                    # Create a garrison army for the siege
                    garrison = self._create_garrison_army(s)
                    queue_pending_battle(self, garrison, terrain_type)
                    self._siege_settlement = s  # track which settlement we're sieging
                    self.paused = True
                    self._add_notification(f"Laying siege to {s.name}!")
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

    def _create_garrison_army(self, settlement):
        """Create a temporary garrison army for siege battles."""
        garrison_size = settlement.garrison_strength
        team = settlement.owner if settlement.owner is not None else 1
        # Build a garrison army based on the settlement's faction
        garrison = create_enemy_army(
            f"{settlement.name} Garrison", team,
            settlement.x, settlement.y,
            difficulty=max(1, garrison_size // 40))
        return garrison

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
        return input_handlers.handle_diplomacy_event(self, event)

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
        self._update_trade_connectivity_warning()

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
        self._update_trade_connectivity_warning()

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

        # Pay upkeep weekly instead of daily.
        if self.day % 7 == 0:
            upkeep = self.player_army.upkeep
            if self.player_army.gold >= upkeep:
                self.player_army.gold -= upkeep
            else:
                self.player_army.gold -= upkeep
                deficit_ratio = min(1.0, abs(self.player_army.gold) / max(1, upkeep))
                for sq in self.player_army.squads:
                    sq_morale = getattr(sq, 'campaign_morale', 100)
                    sq.campaign_morale = max(0, sq_morale - 5 * deficit_ratio)
                if self.player_army.gold < -upkeep * 3:
                    self._add_notification("Your troops are unpaid for the week! Risk of desertion!")

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
            self.settlements, self.factions, self.day,
            armies=self.armies, roaming_manager=self.roaming_manager, scene=self)
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

        # Companion daily tick
        self.companion_manager.tick_day()
        departed = self.companion_manager.check_departures()
        for name in departed:
            self._add_notification(f"Companion {name} has left your service!")

        # Mark fog as needing update
        self._fog_needs_update = True
        self._territory_needs_update = True
        self._update_trade_connectivity_warning()

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
            if getattr(w, "current_status", "") == "Hunting marauders":
                w.current_status = f"Victorious near {w.current_location}"
            self.roaming_manager.record_roaming_win(w)

    def _save_game(self):
        from core.save_system import save_campaign
        from core.audio import get_audio
        save_campaign(self)
        get_audio().play("save")
        self._save_notification_timer = 120
        self._add_notification("Game saved!")

    def update(self):
        update_campaign(self)

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

    def _update_trade_connectivity_warning(self):
        """Warn when faction relations partition the trade network."""
        active_teams = sorted({s.owner for s in self.settlements if s.owner is not None and s.owner > 0})
        if len(active_teams) < 2:
            self.trade_warning = None
            return

        graph = {team: set() for team in active_teams}
        for i, team_a in enumerate(active_teams):
            for team_b in active_teams[i + 1:]:
                if self.diplomacy.get_state(team_a, team_b) != DiplomacyState.WAR:
                    graph[team_a].add(team_b)
                    graph[team_b].add(team_a)

        visited = set()
        stack = [active_teams[0]]
        while stack:
            team = stack.pop()
            if team in visited:
                continue
            visited.add(team)
            stack.extend(graph[team] - visited)

        if len(visited) == len(active_teams):
            self.trade_warning = None
            return

        disconnected = [f.name for f in self.factions
                        if f.team in active_teams and f.team not in visited]
        self.trade_warning = "Trade network fragmented: " + ", ".join(disconnected)

    def get_pending_battle(self):
        return consume_pending_battle(self)

    def remove_army(self, army, player_caused=False):
        if army in self.armies:
            if player_caused:
                self.quest_manager.record_kill(army)
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

        # Roads/trade routes between faction settlements
        self._draw_roads(surface)

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
                # Draw selection ring for selected NPC army
                if getattr(self, '_selected_army', None) is army:
                    sx, sy = self.camera.world_to_screen(army.x, army.y)
                    r = self.camera.scale(18)
                    pygame.draw.circle(surface, GOLD, (int(sx), int(sy)), int(r), 2)

        # Draw interaction indicators near player army
        self._draw_interaction_indicators(surface)

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

        # Companion panel
        if self.show_companions:
            self._draw_companion_panel(surface)

        # Tavern panel
        if self.show_tavern:
            self._draw_tavern_panel(surface)

        # D5: Tournament overlay
        if self.show_tournament and self.active_tournament:
            self._draw_tournament(surface)

        # D6: Player capture overlay (drawn last, blocks everything)
        if self.general_manager.player_capture.is_captured:
            self._draw_capture_overlay(surface)

    def _draw_tournament(self, surface):
        """D5: Draw tournament bracket overlay."""
        campaign_ui.draw_tournament(self, surface)

    def _draw_territory_borders(self, surface):
        """B4: Draw faction territory as colored regions around settlements."""
        map_rendering.draw_territory_borders(self, surface)

    def _draw_stronghold(self, surface, stronghold):
        """B8: Draw a roaming army stronghold on the map."""
        map_rendering.draw_stronghold(self, surface, stronghold)

    def _draw_roads(self, surface):
        """Draw roads connecting settlements of the same faction."""
        map_rendering.draw_roads(self, surface)

    def _draw_interaction_indicators(self, surface):
        """Draw interaction hint icons near interactable objects close to player."""
        map_rendering.draw_interaction_indicators(self, surface)

    def _draw_terrain(self, surface):
        """Draw decorative terrain features."""
        map_rendering.draw_terrain(self, surface)

    def _draw_fog_of_war(self, surface):
        """B13: Draw fog of war overlay - darken areas outside vision range."""
        map_rendering.draw_fog_of_war(self, surface)

    def _draw_hud(self, surface):
        campaign_ui.draw_hud(self, surface)

    def _draw_settlement_info(self, surface, font, small_font):
        campaign_ui.draw_settlement_info(self, surface, font, small_font)

    def _draw_army_info_panel(self, surface, font, small_font):
        """Draw info panel for a selected NPC army."""
        campaign_ui.draw_army_info_panel(self, surface, font, small_font)

    def _draw_diplomacy(self, surface):
        """Draw scrollable diplomacy overview panel."""
        campaign_ui.draw_diplomacy(self, surface)


    def _draw_quest_log(self, surface):
        """B3: Draw quest log overlay."""
        campaign_ui.draw_quest_log(self, surface)

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
        return input_handlers.handle_persuasion_event(self, event)

    def _draw_persuasion(self, surface):
        """B6: Draw persuasion dialog overlay."""
        campaign_ui.draw_persuasion(self, surface)

    def _handle_prisoner_event(self, event):
        """Handle input on the prisoner management panel."""
        return input_handlers.handle_prisoner_event(self, event)

    def _draw_prisoners(self, surface):
        """D6: Draw prisoner management panel."""
        campaign_ui.draw_prisoners(self, surface)

    def _handle_companion_event(self, event):
        """Handle input on the companion management panel."""
        return input_handlers.handle_companion_event(self, event)

    def _draw_companion_panel(self, surface):
        """Draw companion management panel overlay."""
        campaign_ui.draw_companion_panel(self, surface)

    def _handle_tavern_event(self, event):
        """Handle input on the tavern companion recruitment panel."""
        return input_handlers.handle_tavern_event(self, event)

    def _draw_tavern_panel(self, surface):
        """Draw tavern companion recruitment panel overlay."""
        campaign_ui.draw_tavern_panel(self, surface)

    def _handle_capture_event(self, event):
        """Handle input while player is captured."""
        return input_handlers.handle_capture_event(self, event)

    def _draw_capture_overlay(self, surface):
        """D6: Draw player capture state overlay."""
        campaign_ui.draw_capture_overlay(self, surface)

    def _handle_army_panel_event(self, event):
        """C4: Handle army management panel input."""
        return input_handlers.handle_army_panel_event(self, event)

    def _draw_army_panel(self, surface):
        """C4: Draw army management panel."""
        campaign_ui.draw_army_panel(self, surface)
