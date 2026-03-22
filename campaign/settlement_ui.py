"""Settlement interaction UI - full-screen overlay for entering settlements.

Implements B9 (Interactable Settlements) and C3 (Settlement Interaction UI)
from PHASE2_PLAN.md.

Tabs:
  - Tavern (Towns, Castles): Hire mercenary bands, hear rumors
  - Recruit (All): Recruit soldiers from faction pool
  - Rest (All): Heal wounded squads, restore morale (costs gold + days)
  - Garrison (Owned only): Transfer squads to/from settlement garrison
"""

import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, GREY, DARK_GREY, GOLD,
    TEAM_COLORS,
    ARMY_SIZE_BASE, ARMY_SIZE_PER_LEVEL, ARMY_SIZE_MAX,
    REST_COST_PER_DAY, REST_REPLENISH_RATE,
    MERCENARY_COST_MULTIPLIER, TAVERN_MERCS_COUNT, TAVERN_RUMORS_COUNT,
    TOURNAMENT_ENTRY_FEE,
)
from core.utils import point_in_rect
from data.unit_types import ALL_RECRUITABLE, FACTION_SPECIALTY_UNITS
from campaign.army import CampaignSquad
from campaign.settlement import SettlementType


# --- Colors used only within this UI ---
_BG = (25, 25, 35)
_PANEL = (35, 35, 50)
_TAB_ACTIVE = (55, 55, 80)
_TAB_INACTIVE = (40, 40, 55)
_BTN = (50, 80, 60)
_BTN_HOVER = (70, 110, 80)
_BTN_DISABLED = (50, 50, 55)
_BTN_DANGER = (120, 45, 45)
_BTN_DANGER_HOVER = (150, 60, 60)
_SEPARATOR = (80, 80, 100)
_TEXT_DIM = (140, 140, 140)
_TEXT_WARN = (220, 160, 60)
_HEALTH_GREEN = (60, 180, 60)
_HEALTH_RED = (180, 60, 60)

# Rest heal fractions (multi-day rest heals more)
_REST_1DAY_HEAL = REST_REPLENISH_RATE
_REST_3DAY_HEAL = min(1.0, REST_REPLENISH_RATE * 3 * 0.85)  # diminishing returns

# Rumor templates
_RUMOR_TEMPLATES = [
    "Travelers speak of a large {faction} army gathering near {settlement}.",
    "Merchants warn that the roads near {settlement} are plagued by bandits.",
    "A {faction} lord was seen recruiting heavily in {settlement}.",
    "Rumor has it the {faction} and {faction2} may soon go to war.",
    "An old soldier claims {faction} forces are weaker than they appear.",
    "Word is that {settlement} has rich gold deposits nearby.",
    "A bard sings tales of a legendary weapon hidden near {settlement}.",
    "Scouts report unusual troop movements by the {faction}.",
    "Traders say the {faction} treasury is nearly empty.",
    "A pilgrim whispers that {settlement} is poorly defended.",
    "Fishermen claim they saw {faction} warships on the coast.",
    "Refugees from {settlement} say morale is low among the garrison.",
]


def _army_size_limit(general_level):
    """Compute army soldier cap based on general level (B11)."""
    return min(ARMY_SIZE_MAX,
               ARMY_SIZE_BASE + (general_level - 1) * ARMY_SIZE_PER_LEVEL)


class SettlementInteraction:
    """Full-screen settlement interaction overlay.

    Instantiate when the player enters a non-hostile settlement.
    Call handle_event() per pygame event and draw() each frame.
    handle_event() returns None normally, or a dict describing an
    action the campaign scene should process:

        {"action": "leave"}
        {"action": "advance_day", "days": int}
        {"action": "recruit", "unit_stats": UnitStats}
    """

    TABS = ["tavern", "recruit", "rest", "garrison", "quests"]
    TAB_LABELS = {"tavern": "Tavern", "recruit": "Recruit",
                  "rest": "Rest", "garrison": "Garrison",
                  "quests": "Quests"}

    def __init__(self, settlement, player_army, diplomacy, factions, day,
                 all_settlements=None, all_armies=None, quest_manager=None,
                 tournament_available=False):
        self.settlement = settlement
        self.army = player_army
        self.diplomacy = diplomacy
        self.factions = factions  # list of Faction objects
        self.day = day
        self.all_settlements = all_settlements or []
        self.all_armies = all_armies or []
        self.quest_manager = quest_manager  # B3: quest manager reference
        self.tournament_available = tournament_available  # D5: tournament

        # Determine available tabs
        self._available_tabs = self._compute_available_tabs()
        self.current_tab = self._available_tabs[0] if self._available_tabs else "recruit"

        # Tavern state
        self.mercenary_pool = []   # list of UnitStats
        self.rumors = []           # list of str
        self._generate_mercenaries()
        self._generate_rumors()

        # Recruit state - reuse settlement's available_recruits
        # (already faction-aware via Settlement.refresh_recruits)

        # Scroll offset for recruit/army lists
        self.recruit_scroll = 0
        self.army_scroll = 0

        # Cached rects for click detection (rebuilt each draw)
        self._tab_rects = {}       # tab_name -> (x, y, w, h)
        self._button_rects = {}    # identifier -> (x, y, w, h)
        self._leave_rect = (0, 0, 0, 0)

        # Fonts (created once)
        self._font_title = pygame.font.SysFont(None, 30)
        self._font = pygame.font.SysFont(None, 22)
        self._font_small = pygame.font.SysFont(None, 18)
        self._font_tiny = pygame.font.SysFont(None, 15)

        # Message flash
        self._message = ""
        self._message_timer = 0

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _compute_available_tabs(self):
        tabs = []
        st = self.settlement.settlement_type
        # Tavern available in towns and castles
        if st in (SettlementType.TOWN, SettlementType.CASTLE):
            tabs.append("tavern")
        tabs.append("recruit")
        tabs.append("rest")
        # B3: Quests/bounty board available at towns and castles
        if st in (SettlementType.TOWN, SettlementType.CASTLE):
            tabs.append("quests")
        # Garrison only for player-owned settlements
        if self.settlement.owner == self.army.team:
            tabs.append("garrison")
        return tabs

    def _generate_mercenaries(self):
        """Create a random pool of mercenary units for hire."""
        pool = ALL_RECRUITABLE[:]
        random.shuffle(pool)
        self.mercenary_pool = pool[:TAVERN_MERCS_COUNT]

    def _generate_rumors(self):
        """Create flavor-text rumors about the world."""
        faction_names = [f.name for f in self.factions]
        settlement_names = [s.name for s in self.all_settlements] if self.all_settlements else [self.settlement.name]
        self.rumors = []
        templates = random.sample(_RUMOR_TEMPLATES,
                                  min(TAVERN_RUMORS_COUNT, len(_RUMOR_TEMPLATES)))
        for tmpl in templates:
            text = tmpl
            if "{faction}" in text:
                text = text.replace("{faction}", random.choice(faction_names), 1)
            if "{faction2}" in text:
                text = text.replace("{faction2}", random.choice(faction_names), 1)
            if "{settlement}" in text:
                text = text.replace("{settlement}", random.choice(settlement_names), 1)
            self.rumors.append(text)

    # ------------------------------------------------------------------
    # Flash message
    # ------------------------------------------------------------------

    def _flash(self, msg):
        self._message = msg
        self._message_timer = 180  # 3 seconds at 60 fps

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """Process a single pygame event.

        Returns None or a dict describing a campaign-level action.
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return {"action": "leave"}
            # Number keys switch tabs
            if pygame.K_1 <= event.key <= pygame.K_4:
                idx = event.key - pygame.K_1
                if idx < len(self._available_tabs):
                    self.current_tab = self._available_tabs[idx]
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Leave button
            if point_in_rect(mx, my, *self._leave_rect):
                return {"action": "leave"}

            # Tab clicks
            for tab_name, rect in self._tab_rects.items():
                if point_in_rect(mx, my, *rect):
                    self.current_tab = tab_name
                    return None

            # Delegate to per-tab handler
            if self.current_tab == "tavern":
                return self._handle_tavern_click(mx, my)
            elif self.current_tab == "recruit":
                return self._handle_recruit_click(mx, my)
            elif self.current_tab == "rest":
                return self._handle_rest_click(mx, my)
            elif self.current_tab == "garrison":
                return self._handle_garrison_click(mx, my)
            elif self.current_tab == "quests":
                return self._handle_quests_click(mx, my)

        return None

    # --- Per-tab click handlers ---

    def _handle_tavern_click(self, mx, my):
        # Hire mercenary buttons
        for i in range(len(self.mercenary_pool)):
            key = f"merc_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                return self._hire_mercenary(i)

        # D5: Tournament entry
        key = "tournament_enter"
        if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
            if self.tournament_available and self.army.gold >= TOURNAMENT_ENTRY_FEE:
                return {"action": "enter_tournament"}
            elif self.army.gold < TOURNAMENT_ENTRY_FEE:
                self._flash("Not enough gold for entry fee.")

        # Dismiss rumor buttons
        for i in range(len(self.rumors)):
            key = f"rumor_dismiss_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                self.rumors.pop(i)
                return None
        return None

    def _handle_recruit_click(self, mx, my):
        recruits = self.settlement.available_recruits
        for i in range(len(recruits)):
            key = f"recruit_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                return self._recruit_unit(i)

        # Disband buttons for current army
        for i in range(len(self.army.squads)):
            key = f"disband_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                self.army.remove_squad(i)
                self._flash("Squad disbanded.")
                return None
        return None

    def _handle_rest_click(self, mx, my):
        if "rest_1" in self._button_rects and point_in_rect(mx, my, *self._button_rects["rest_1"]):
            return self._rest(1, _REST_1DAY_HEAL)
        if "rest_3" in self._button_rects and point_in_rect(mx, my, *self._button_rects["rest_3"]):
            return self._rest(3, _REST_3DAY_HEAL)
        return None

    def _handle_quests_click(self, mx, my):
        """B3: Handle quest bounty board clicks."""
        if not self.quest_manager:
            return None
        board = self.quest_manager.get_bounty_board(self.settlement)
        for i in range(len(board)):
            key = f"quest_accept_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                q = board[i]
                if self.quest_manager.accept_quest(q, self.day, settlement=self.settlement):
                    self._flash(f"Quest accepted: {q.title}")
                else:
                    self._flash("Cannot accept more quests (max 5).")
                return None
        return None

    def _handle_garrison_click(self, mx, my):
        # Add to garrison
        for i in range(len(self.army.squads)):
            key = f"garrison_add_{i}"
            if key in self._button_rects and point_in_rect(mx, my, *self._button_rects[key]):
                return self._add_to_garrison(i)

        # Withdraw from garrison
        if "garrison_withdraw" in self._button_rects and point_in_rect(mx, my, *self._button_rects["garrison_withdraw"]):
            return self._withdraw_from_garrison()
        return None

    # ------------------------------------------------------------------
    # Action logic
    # ------------------------------------------------------------------

    def _hire_mercenary(self, index):
        if index >= len(self.mercenary_pool):
            return None
        unit = self.mercenary_pool[index]
        cost = int(unit.cost * MERCENARY_COST_MULTIPLIER)
        limit = _army_size_limit(self.army.general_level)
        if self.army.total_soldiers + unit.squad_size > limit:
            self._flash(f"Army limit reached ({limit} soldiers).")
            return None
        if self.army.gold < cost:
            self._flash("Not enough gold.")
            return None
        self.army.gold -= cost
        self.army.add_squad(unit)
        self.mercenary_pool.pop(index)
        self._flash(f"Hired {unit.name} for {cost}g.")
        return None

    def _recruit_unit(self, index):
        recruits = self.settlement.available_recruits
        if index >= len(recruits):
            return None
        unit = recruits[index]
        limit = _army_size_limit(self.army.general_level)
        if self.army.total_soldiers + unit.squad_size > limit:
            self._flash(f"Army limit reached ({limit} soldiers).")
            return None
        if self.army.gold < unit.cost:
            self._flash("Not enough gold.")
            return None
        self.army.gold -= unit.cost
        self.army.add_squad(unit)
        recruits.pop(index)
        self._flash(f"Recruited {unit.name}.")
        return None

    def _rest(self, days, heal_fraction):
        cost = REST_COST_PER_DAY * days
        if self.army.gold < cost:
            self._flash("Not enough gold.")
            return None
        self.army.gold -= cost
        healed_total = 0
        for sq in self.army.squads:
            if sq.is_understrength:
                missing = sq.max_count - sq.current_count
                restore = max(1, int(missing * heal_fraction))
                sq.replenish(restore)
                healed_total += restore
        self.day += days
        self._flash(f"Rested {days} day(s). Restored {healed_total} soldiers. (-{cost}g)")
        return {"action": "advance_day", "days": days}

    def _add_to_garrison(self, index):
        if index >= len(self.army.squads):
            return None
        if len(self.army.squads) <= 1:
            self._flash("Cannot garrison your last squad.")
            return None
        sq = self.army.squads[index]
        self.settlement.garrison_strength += sq.strength
        self.army.remove_squad(index)
        self._flash(f"Squad added to garrison. Garrison strength: {self.settlement.garrison_strength}")
        return None

    def _withdraw_from_garrison(self):
        if self.settlement.garrison_strength <= 0:
            self._flash("Garrison is empty.")
            return None
        # Withdraw creates a militia squad from garrison strength
        from data.unit_types import MILITIA
        limit = _army_size_limit(self.army.general_level)
        squad_size = MILITIA.squad_size
        if self.army.total_soldiers + squad_size > limit:
            self._flash(f"Army limit reached ({limit} soldiers).")
            return None
        self.army.add_squad(MILITIA)
        cost_strength = MILITIA.squad_size * (MILITIA.melee_attack + MILITIA.melee_defense + MILITIA.health // 10)
        self.settlement.garrison_strength = max(0, self.settlement.garrison_strength - cost_strength)
        self._flash(f"Withdrew militia from garrison. Garrison: {self.settlement.garrison_strength}")
        return None

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface):
        """Draw the full-screen settlement interaction overlay."""
        self._button_rects.clear()

        # Darken background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Main panel
        margin = 40
        px, py = margin, margin
        pw = SCREEN_WIDTH - margin * 2
        ph = SCREEN_HEIGHT - margin * 2
        pygame.draw.rect(surface, _BG, (px, py, pw, ph))
        pygame.draw.rect(surface, GOLD, (px, py, pw, ph), 2)

        # Title bar
        self._draw_title_bar(surface, px, py, pw)

        # Tabs
        tab_y = py + 50
        self._draw_tabs(surface, px, tab_y, pw)

        # Content area
        content_y = tab_y + 35
        content_h = ph - (content_y - py) - 50
        content_rect = (px + 10, content_y, pw - 20, content_h)

        if self.current_tab == "tavern":
            self._draw_tavern(surface, *content_rect)
        elif self.current_tab == "recruit":
            self._draw_recruit(surface, *content_rect)
        elif self.current_tab == "rest":
            self._draw_rest(surface, *content_rect)
        elif self.current_tab == "garrison":
            self._draw_garrison(surface, *content_rect)
        elif self.current_tab == "quests":
            self._draw_quests(surface, *content_rect)

        # Leave button
        leave_w, leave_h = 160, 32
        leave_x = px + pw // 2 - leave_w // 2
        leave_y = py + ph - 42
        mx, my = pygame.mouse.get_pos()
        hovered = point_in_rect(mx, my, leave_x, leave_y, leave_w, leave_h)
        btn_col = _BTN_DANGER_HOVER if hovered else _BTN_DANGER
        pygame.draw.rect(surface, btn_col, (leave_x, leave_y, leave_w, leave_h))
        pygame.draw.rect(surface, WHITE, (leave_x, leave_y, leave_w, leave_h), 1)
        lbl = self._font.render("Leave Settlement", True, WHITE)
        surface.blit(lbl, (leave_x + leave_w // 2 - lbl.get_width() // 2,
                           leave_y + leave_h // 2 - lbl.get_height() // 2))
        self._leave_rect = (leave_x, leave_y, leave_w, leave_h)

        # Flash message
        if self._message_timer > 0:
            self._message_timer -= 1
            alpha = min(255, self._message_timer * 4)
            msg_surf = self._font.render(self._message, True, _TEXT_WARN)
            msg_bg = pygame.Surface((msg_surf.get_width() + 20, msg_surf.get_height() + 10), pygame.SRCALPHA)
            msg_bg.fill((0, 0, 0, min(180, alpha)))
            cx = SCREEN_WIDTH // 2 - msg_bg.get_width() // 2
            cy = SCREEN_HEIGHT - 100
            surface.blit(msg_bg, (cx, cy))
            surface.blit(msg_surf, (cx + 10, cy + 5))

    # --- Title bar ---

    def _draw_title_bar(self, surface, px, py, pw):
        owner_name = self._faction_name(self.settlement.owner)
        stype = self.settlement.settlement_type.capitalize()
        title = f"{self.settlement.name} ({stype}) - {owner_name}"
        t = self._font_title.render(title, True, GOLD)
        surface.blit(t, (px + 15, py + 12))

        # Gold & army info
        info = f"Gold: {self.army.gold}  |  Army: {self.army.total_soldiers}/{_army_size_limit(self.army.general_level)}  |  Day {self.day}"
        it = self._font_small.render(info, True, WHITE)
        surface.blit(it, (px + pw - it.get_width() - 15, py + 18))

    # --- Tabs ---

    def _draw_tabs(self, surface, px, ty, pw):
        self._tab_rects.clear()
        tab_w = 120
        tab_h = 30
        x = px + 15
        for i, tab in enumerate(self._available_tabs):
            active = (tab == self.current_tab)
            color = _TAB_ACTIVE if active else _TAB_INACTIVE
            pygame.draw.rect(surface, color, (x, ty, tab_w, tab_h))
            if active:
                pygame.draw.rect(surface, GOLD, (x, ty, tab_w, tab_h), 2)
            else:
                pygame.draw.rect(surface, GREY, (x, ty, tab_w, tab_h), 1)
            hotkey = str(i + 1)
            label = f"[{hotkey}] {self.TAB_LABELS.get(tab, tab)}"
            lt = self._font_small.render(label, True, WHITE if active else _TEXT_DIM)
            surface.blit(lt, (x + tab_w // 2 - lt.get_width() // 2,
                              ty + tab_h // 2 - lt.get_height() // 2))
            self._tab_rects[tab] = (x, ty, tab_w, tab_h)
            x += tab_w + 5

    # ------------------------------------------------------------------
    # Tab content drawers
    # ------------------------------------------------------------------

    def _draw_tavern(self, surface, cx, cy, cw, ch):
        mx, my = pygame.mouse.get_pos()
        y = cy + 5

        # Section: Mercenaries
        header = self._font.render("Mercenaries for Hire", True, WHITE)
        surface.blit(header, (cx + 5, y))
        y += 25

        if not self.mercenary_pool:
            t = self._font_small.render("No mercenaries available.", True, _TEXT_DIM)
            surface.blit(t, (cx + 15, y))
            y += 20
        else:
            for i, unit in enumerate(self.mercenary_pool):
                cost = int(unit.cost * MERCENARY_COST_MULTIPLIER)
                can_afford = self.army.gold >= cost
                limit = _army_size_limit(self.army.general_level)
                can_fit = self.army.total_soldiers + unit.squad_size <= limit

                btn_h = 50
                key = f"merc_{i}"
                rect = (cx + 10, y, cw - 20, btn_h)
                hovered = point_in_rect(mx, my, *rect)

                if can_afford and can_fit:
                    col = _BTN_HOVER if hovered else _BTN
                else:
                    col = _BTN_DISABLED
                pygame.draw.rect(surface, col, rect)
                pygame.draw.rect(surface, GREY, rect, 1)
                self._button_rects[key] = rect

                name_t = self._font.render(f"{unit.name} ({unit.squad_size} soldiers) - {cost}g", True,
                                           WHITE if can_afford and can_fit else _TEXT_DIM)
                surface.blit(name_t, (cx + 18, y + 4))

                stats_str = (f"ATK:{unit.melee_attack} DEF:{unit.melee_defense} "
                             f"HP:{unit.health} SPD:{unit.speed:.1f} ARM:{unit.armor}")
                if unit.ranged_attack:
                    stats_str += f" RNG:{unit.ranged_attack} DIST:{unit.range_distance}"
                stats_t = self._font_tiny.render(stats_str, True, _TEXT_DIM)
                surface.blit(stats_t, (cx + 18, y + 24))

                desc_t = self._font_tiny.render(unit.description[:80], True, (120, 120, 150))
                surface.blit(desc_t, (cx + 18, y + 36))

                y += btn_h + 5

        # D5: Tournament section
        if self.tournament_available:
            y += 10
            pygame.draw.line(surface, _SEPARATOR, (cx + 10, y), (cx + cw - 10, y))
            y += 10
            tourney_header = self._font.render("Tournament!", True, GOLD)
            surface.blit(tourney_header, (cx + 5, y))
            y += 25

            can_afford = self.army.gold >= TOURNAMENT_ENTRY_FEE
            btn_h = 36
            key = "tournament_enter"
            rect = (cx + 10, y, cw - 20, btn_h)
            hovered = point_in_rect(mx, my, *rect)
            col = (_BTN_HOVER if hovered else _BTN) if can_afford else _BTN_DISABLED
            pygame.draw.rect(surface, col, rect)
            pygame.draw.rect(surface, GOLD if can_afford else GREY, rect, 1)
            self._button_rects[key] = rect

            entry_text = f"Enter Tournament (Entry Fee: {TOURNAMENT_ENTRY_FEE}g)"
            et = self._font.render(entry_text, True, WHITE if can_afford else _TEXT_DIM)
            surface.blit(et, (cx + 18, y + 8))
            y += btn_h + 5

            desc = self._font_small.render(
                "Fight 3 rounds for gold and glory!", True, _TEXT_DIM)
            surface.blit(desc, (cx + 18, y))
            y += 20

        # Separator
        y += 10
        pygame.draw.line(surface, _SEPARATOR, (cx + 10, y), (cx + cw - 10, y))
        y += 10

        # Section: Rumors
        header2 = self._font.render("Rumors", True, WHITE)
        surface.blit(header2, (cx + 5, y))
        y += 25

        if not self.rumors:
            t = self._font_small.render("No rumors to hear.", True, _TEXT_DIM)
            surface.blit(t, (cx + 15, y))
        else:
            for i, rumor in enumerate(self.rumors):
                rumor_h = 30
                rect = (cx + 10, y, cw - 20, rumor_h)
                pygame.draw.rect(surface, (40, 40, 55), rect)
                pygame.draw.rect(surface, (60, 60, 80), rect, 1)

                rt = self._font_small.render(rumor[:90], True, (180, 180, 200))
                surface.blit(rt, (cx + 18, y + 7))

                # Dismiss button
                dismiss_rect = (cx + cw - 60, y + 3, 40, 22)
                dismiss_key = f"rumor_dismiss_{i}"
                hovered_d = point_in_rect(mx, my, *dismiss_rect)
                pygame.draw.rect(surface, (100, 60, 60) if hovered_d else (70, 50, 50), dismiss_rect)
                dt = self._font_tiny.render("OK", True, WHITE)
                surface.blit(dt, (dismiss_rect[0] + 12, dismiss_rect[1] + 4))
                self._button_rects[dismiss_key] = dismiss_rect

                y += rumor_h + 4

    def _draw_recruit(self, surface, cx, cy, cw, ch):
        mx, my = pygame.mouse.get_pos()
        y = cy + 5
        half_w = cw // 2 - 10

        # Left side: available recruits
        header = self._font.render("Available Recruits", True, WHITE)
        surface.blit(header, (cx + 5, y))
        y_left = y + 25

        recruits = self.settlement.available_recruits
        if not recruits:
            t = self._font_small.render("No recruits available.", True, _TEXT_DIM)
            surface.blit(t, (cx + 15, y_left))
        else:
            limit = _army_size_limit(self.army.general_level)
            for i, unit in enumerate(recruits):
                can_afford = self.army.gold >= unit.cost
                can_fit = self.army.total_soldiers + unit.squad_size <= limit

                btn_h = 55
                key = f"recruit_{i}"
                rect = (cx + 10, y_left, half_w, btn_h)
                hovered = point_in_rect(mx, my, *rect)

                if can_afford and can_fit:
                    col = _BTN_HOVER if hovered else _BTN
                else:
                    col = _BTN_DISABLED
                pygame.draw.rect(surface, col, rect)
                pygame.draw.rect(surface, GREY, rect, 1)
                self._button_rects[key] = rect

                name_t = self._font.render(f"{unit.name} ({unit.squad_size}) - {unit.cost}g", True,
                                           WHITE if can_afford and can_fit else _TEXT_DIM)
                surface.blit(name_t, (cx + 18, y_left + 3))

                stats_str = (f"ATK:{unit.melee_attack} DEF:{unit.melee_defense} "
                             f"HP:{unit.health} SPD:{unit.speed:.1f} ARM:{unit.armor}")
                if unit.ranged_attack:
                    stats_str += f" RNG:{unit.ranged_attack}"
                stats_t = self._font_tiny.render(stats_str, True, _TEXT_DIM)
                surface.blit(stats_t, (cx + 18, y_left + 22))

                desc_t = self._font_tiny.render(unit.description[:70], True, (120, 120, 150))
                surface.blit(desc_t, (cx + 18, y_left + 36))

                y_left += btn_h + 4

        # Right side: current army
        right_x = cx + half_w + 20
        header2 = self._font.render("Your Army", True, WHITE)
        surface.blit(header2, (right_x, y))
        y_right = y + 25

        for i, sq in enumerate(self.army.squads):
            stats = sq.unit_stats
            row_h = 28
            # Background
            pygame.draw.rect(surface, (40, 40, 55), (right_x, y_right, half_w, row_h))
            pygame.draw.rect(surface, (60, 60, 80), (right_x, y_right, half_w, row_h), 1)

            count_str = f"{sq.current_count}/{sq.max_count}" if sq.is_understrength else str(sq.current_count)
            rank_str = f" [{sq.rank_name}]" if sq.battles_survived > 0 else ""
            txt = self._font_small.render(
                f"{stats.name} ({count_str}){rank_str} - {stats.upkeep}/week",
                True, WHITE)
            surface.blit(txt, (right_x + 5, y_right + 5))

            # Disband button
            disband_rect = (right_x + half_w - 50, y_right + 3, 42, 20)
            hovered = point_in_rect(mx, my, *disband_rect)
            pygame.draw.rect(surface, _BTN_DANGER_HOVER if hovered else _BTN_DANGER, disband_rect)
            dt = self._font_tiny.render("Drop", True, WHITE)
            surface.blit(dt, (disband_rect[0] + 8, disband_rect[1] + 3))
            self._button_rects[f"disband_{i}"] = disband_rect

            y_right += row_h + 3

        # Footer info
        limit = _army_size_limit(self.army.general_level)
        footer = self._font_small.render(
            f"Soldiers: {self.army.total_soldiers}/{limit}  |  "
            f"Upkeep: {self.army.upkeep}/week  |  Gold: {self.army.gold}",
            True, _TEXT_DIM)
        surface.blit(footer, (cx + 10, cy + ch - 25))

    def _draw_rest(self, surface, cx, cy, cw, ch):
        mx, my = pygame.mouse.get_pos()
        y = cy + 5

        header = self._font.render("Rest & Recuperate", True, WHITE)
        surface.blit(header, (cx + 5, y))
        y += 30

        # Current army status
        sub = self._font_small.render("Current Army Status:", True, WHITE)
        surface.blit(sub, (cx + 10, y))
        y += 22

        understrength_count = 0
        for sq in self.army.squads:
            row_h = 22
            name = sq.unit_stats.name
            cur = sq.current_count
            mx_count = sq.max_count
            pct = cur / mx_count if mx_count > 0 else 1.0

            # Health bar background
            bar_x = cx + 15
            bar_w = 200
            pygame.draw.rect(surface, DARK_GREY, (bar_x, y, bar_w, row_h - 4))
            bar_fill = int(bar_w * pct)
            bar_color = _HEALTH_GREEN if pct > 0.6 else (_TEXT_WARN if pct > 0.3 else _HEALTH_RED)
            pygame.draw.rect(surface, bar_color, (bar_x, y, bar_fill, row_h - 4))
            pygame.draw.rect(surface, GREY, (bar_x, y, bar_w, row_h - 4), 1)

            label = self._font_small.render(f"{name}: {cur}/{mx_count}", True, WHITE)
            surface.blit(label, (bar_x + bar_w + 10, y))

            if sq.is_understrength:
                understrength_count += 1
            y += row_h + 2

        y += 15

        # Rest buttons
        if understrength_count == 0:
            t = self._font.render("All squads are at full strength.", True, _HEALTH_GREEN)
            surface.blit(t, (cx + 15, y))
            y += 30
        else:
            t = self._font_small.render(f"{understrength_count} squad(s) understrength.", True, _TEXT_WARN)
            surface.blit(t, (cx + 15, y))
            y += 25

        # Rest 1 day button
        cost_1 = REST_COST_PER_DAY
        can_afford_1 = self.army.gold >= cost_1
        btn_rect_1 = (cx + 15, y, 300, 36)
        hovered_1 = point_in_rect(mx, my, *btn_rect_1)
        col_1 = (_BTN_HOVER if hovered_1 else _BTN) if can_afford_1 else _BTN_DISABLED
        pygame.draw.rect(surface, col_1, btn_rect_1)
        pygame.draw.rect(surface, GREY, btn_rect_1, 1)
        lbl_1 = self._font.render(f"Rest 1 Day - {cost_1}g (restore ~{int(_REST_1DAY_HEAL*100)}% missing)", True,
                                   WHITE if can_afford_1 else _TEXT_DIM)
        surface.blit(lbl_1, (btn_rect_1[0] + 10, btn_rect_1[1] + 8))
        self._button_rects["rest_1"] = btn_rect_1
        y += 44

        # Rest 3 days button
        cost_3 = REST_COST_PER_DAY * 3
        can_afford_3 = self.army.gold >= cost_3
        btn_rect_3 = (cx + 15, y, 300, 36)
        hovered_3 = point_in_rect(mx, my, *btn_rect_3)
        col_3 = (_BTN_HOVER if hovered_3 else _BTN) if can_afford_3 else _BTN_DISABLED
        pygame.draw.rect(surface, col_3, btn_rect_3)
        pygame.draw.rect(surface, GREY, btn_rect_3, 1)
        lbl_3 = self._font.render(f"Rest 3 Days - {cost_3}g (restore ~{int(_REST_3DAY_HEAL*100)}% missing)", True,
                                   WHITE if can_afford_3 else _TEXT_DIM)
        surface.blit(lbl_3, (btn_rect_3[0] + 10, btn_rect_3[1] + 8))
        self._button_rects["rest_3"] = btn_rect_3
        y += 50

        # Info
        info = self._font_small.render(
            f"Resting costs {REST_COST_PER_DAY}g per day. Current gold: {self.army.gold}",
            True, _TEXT_DIM)
        surface.blit(info, (cx + 15, y))

    def _draw_garrison(self, surface, cx, cy, cw, ch):
        mx, my = pygame.mouse.get_pos()
        y = cy + 5

        header = self._font.render("Garrison Management", True, WHITE)
        surface.blit(header, (cx + 5, y))
        y += 28

        # Garrison strength
        strength_t = self._font.render(
            f"Garrison Strength: {self.settlement.garrison_strength}", True, WHITE)
        surface.blit(strength_t, (cx + 15, y))
        y += 28

        pygame.draw.line(surface, _SEPARATOR, (cx + 10, y), (cx + cw - 10, y))
        y += 10

        # Add to garrison section
        sub = self._font.render("Add Squad to Garrison:", True, WHITE)
        surface.blit(sub, (cx + 10, y))
        y += 25

        if len(self.army.squads) <= 1:
            t = self._font_small.render("Cannot garrison your last squad.", True, _TEXT_DIM)
            surface.blit(t, (cx + 20, y))
            y += 22
        else:
            for i, sq in enumerate(self.army.squads):
                row_h = 28
                key = f"garrison_add_{i}"
                rect = (cx + 15, y, cw // 2, row_h)
                hovered = point_in_rect(mx, my, *rect)
                col = _BTN_HOVER if hovered else _BTN
                pygame.draw.rect(surface, col, rect)
                pygame.draw.rect(surface, GREY, rect, 1)

                count_str = f"{sq.current_count}/{sq.max_count}" if sq.is_understrength else str(sq.current_count)
                txt = self._font_small.render(
                    f"{sq.unit_stats.name} ({count_str}) - Strength: {sq.strength}",
                    True, WHITE)
                surface.blit(txt, (cx + 22, y + 5))
                self._button_rects[key] = rect

                y += row_h + 3

        y += 15
        pygame.draw.line(surface, _SEPARATOR, (cx + 10, y), (cx + cw - 10, y))
        y += 10

        # Withdraw from garrison
        sub2 = self._font.render("Withdraw from Garrison:", True, WHITE)
        surface.blit(sub2, (cx + 10, y))
        y += 25

        can_withdraw = self.settlement.garrison_strength > 0
        limit = _army_size_limit(self.army.general_level)
        from data.unit_types import MILITIA
        can_fit = self.army.total_soldiers + MILITIA.squad_size <= limit

        w_rect = (cx + 15, y, 320, 36)
        hovered_w = point_in_rect(mx, my, *w_rect)
        if can_withdraw and can_fit:
            col_w = _BTN_HOVER if hovered_w else _BTN
        else:
            col_w = _BTN_DISABLED
        pygame.draw.rect(surface, col_w, w_rect)
        pygame.draw.rect(surface, GREY, w_rect, 1)

        w_text = "Withdraw Militia Squad from Garrison"
        if not can_withdraw:
            w_text = "Garrison is empty"
        elif not can_fit:
            w_text = f"Army limit reached ({limit})"
        wt = self._font.render(w_text, True, WHITE if (can_withdraw and can_fit) else _TEXT_DIM)
        surface.blit(wt, (w_rect[0] + 10, w_rect[1] + 8))
        self._button_rects["garrison_withdraw"] = w_rect

        y += 50
        info = self._font_small.render(
            "Adding a squad transfers its soldiers permanently to the garrison.",
            True, _TEXT_DIM)
        surface.blit(info, (cx + 15, y))

    def _draw_quests(self, surface, cx, cy, cw, ch):
        """B3: Draw bounty board / quest tab."""
        mx, my = pygame.mouse.get_pos()
        y = cy + 5

        header = self._font.render("Bounty Board", True, WHITE)
        surface.blit(header, (cx + 5, y))
        y += 25

        if not self.quest_manager:
            t = self._font_small.render("Quest system not available.", True, _TEXT_DIM)
            surface.blit(t, (cx + 15, y))
            return

        # Available quests
        board = self.quest_manager.get_bounty_board(self.settlement)
        if not board:
            t = self._font_small.render("No local contracts available here right now.", True, _TEXT_DIM)
            surface.blit(t, (cx + 15, y))
            y += 22
        else:
            for i, q in enumerate(board):
                btn_h = 60
                key = f"quest_accept_{i}"
                rect = (cx + 10, y, cw - 20, btn_h)
                hovered = point_in_rect(mx, my, *rect)

                can_accept = len(self.quest_manager.active_quests) < self.quest_manager.MAX_ACTIVE_QUESTS
                col = (_BTN_HOVER if hovered else _BTN) if can_accept else _BTN_DISABLED
                pygame.draw.rect(surface, col, rect)
                pygame.draw.rect(surface, GREY, rect, 1)
                self._button_rects[key] = rect

                title_t = self._font.render(q.title, True, WHITE if can_accept else _TEXT_DIM)
                surface.blit(title_t, (cx + 18, y + 3))

                desc_t = self._font_tiny.render(q.description[:80], True, _TEXT_DIM)
                surface.blit(desc_t, (cx + 18, y + 22))

                reward_parts = [f"Reward: {q.gold_reward}g"]
                if q.rep_reward:
                    reward_parts.append(f"+{q.rep_reward} rep")
                if q.time_limit:
                    reward_parts.append(f"Time: {q.time_limit} days")
                reward_t = self._font_tiny.render("  |  ".join(reward_parts), True, (180, 180, 100))
                surface.blit(reward_t, (cx + 18, y + 38))

                y += btn_h + 4

        # Active quests
        y += 10
        pygame.draw.line(surface, _SEPARATOR, (cx + 10, y), (cx + cw - 10, y))
        y += 8
        active_h = self._font.render(
            f"Active Quests ({len(self.quest_manager.active_quests)}/{self.quest_manager.MAX_ACTIVE_QUESTS})",
            True, WHITE)
        surface.blit(active_h, (cx + 5, y))
        y += 25

        for q in self.quest_manager.active_quests:
            qt = self._font_small.render(q.title, True, WHITE)
            surface.blit(qt, (cx + 15, y))
            y += 18
            progress_parts = []
            if q.is_kill_quest:
                progress_parts.append(f"Progress: {q.kills_done}/{q.kill_count}")
            if q.time_limit > 0:
                progress_parts.append(f"Days left: {q.days_remaining}")
            if progress_parts:
                pt = self._font_tiny.render("  ".join(progress_parts), True, (160, 160, 100))
                surface.blit(pt, (cx + 25, y))
                y += 16
            y += 4

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _faction_name(self, team):
        """Look up faction name by team index."""
        if team == 0:
            return "Player"
        for f in self.factions:
            if f.team == team:
                return f.name
        return "Independent"
