"""Campaign UI drawing functions.

Render-only helpers for HUD, panels, and modal overlays.
All functions accept the CampaignScene instance as first argument (``scene``).
"""

import pygame
from core.utils import get_font, distance
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_TICKS_PER_DAY,
    CAMPAIGN_SPEED_1X, CAMPAIGN_SPEED_2X, CAMPAIGN_SPEED_3X,
    TEAM_COLORS,
    WHITE, GREY, DARK_GREY, GOLD,
    FACTION_JOIN_THRESHOLD,
    PERSUASION_RANGE,
    SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER,
    BRIBE_COST_BASE,
)
from campaign.faction import FACTION_BY_TEAM
from campaign.diplomacy import DiplomacyState
from campaign.roaming import ROAMING_TYPES


# ---------------------------------------------------------------------------
# Tournament overlay
# ---------------------------------------------------------------------------

def draw_tournament(scene, surface):
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

    t = scene.active_tournament
    title = font.render("TOURNAMENT", True, GOLD)
    surface.blit(title, (px + panel_w // 2 - title.get_width() // 2, py + 15))

    y = py + 60
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


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

def draw_hud(scene, surface):
    font = get_font(22)
    small_font = get_font(16)

    bar = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 200))
    surface.blit(bar, (0, 0))

    season = scene._get_current_season()
    season_colors = {
        SEASON_SPRING: (100, 200, 100),
        SEASON_SUMMER: (220, 200, 50),
        SEASON_AUTUMN: (200, 140, 50),
        SEASON_WINTER: (150, 200, 255),
    }
    season_color = season_colors.get(season, WHITE)
    day_text = font.render(f"Day {scene.day} - {season.capitalize()}", True, season_color)
    surface.blit(day_text, (10, 8))

    gold_text = font.render(f"Gold: {scene.player_army.gold}", True, GOLD)
    surface.blit(gold_text, (150, 8))

    speed_x = 260
    pause_color = (200, 80, 80) if scene.paused else (80, 80, 80)
    pygame.draw.rect(surface, pause_color, (speed_x, 4, 35, 28))
    pygame.draw.rect(surface, WHITE, (speed_x, 4, 35, 28), 1)
    pause_label = small_font.render("||" if not scene.paused else ">>", True, WHITE)
    surface.blit(pause_label, (speed_x + 10, 10))
    speed_x += 40

    for i, (label, spd) in enumerate([("1x", CAMPAIGN_SPEED_1X),
                                       ("2x", CAMPAIGN_SPEED_2X),
                                       ("4x", CAMPAIGN_SPEED_3X)]):
        btn_color = (60, 120, 60) if scene.campaign_speed == spd and not scene.paused else (60, 60, 60)
        pygame.draw.rect(surface, btn_color, (speed_x, 4, 30, 28))
        pygame.draw.rect(surface, WHITE, (speed_x, 4, 30, 28), 1)
        spd_text = small_font.render(label, True, WHITE)
        surface.blit(spd_text, (speed_x + 6, 10))
        speed_x += 35

    faction_str = "Independent"
    if scene.player_faction is not None:
        f_obj = FACTION_BY_TEAM.get(scene.player_faction)
        faction_str = f_obj.name if f_obj else f"Team {scene.player_faction}"
    army_text = font.render(
        f"{faction_str} | "
        f"Army: {scene.player_army.total_soldiers}/{scene.player_army.army_size_limit} | "
        f"Upkeep: {scene.player_army.upkeep}/week",
        True, WHITE)
    surface.blit(army_text, (speed_x + 20, 8))

    progress = scene.day_ticks / CAMPAIGN_TICKS_PER_DAY
    bar_x = SCREEN_WIDTH - 160
    bar_w = 100
    pygame.draw.rect(surface, DARK_GREY, (bar_x, 14, bar_w, 8))
    pygame.draw.rect(surface, (180, 160, 80), (bar_x, 14, int(bar_w * progress), 8))
    time_label = small_font.render("Day", True, (180, 180, 180))
    surface.blit(time_label, (bar_x + bar_w + 5, 12))

    bottom = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
    bottom.fill((0, 0, 0, 200))
    surface.blit(bottom, (0, SCREEN_HEIGHT - 40))

    ctrl_text = small_font.render(
        "[RMB] Move [E] Settlement [R] Recruit [D] Diplomacy "
        "[Q] Quests [A] Army [P] Persuade [J] Prisoners [SPACE] Pause",
        True, (180, 180, 180))
    surface.blit(ctrl_text, (10, SCREEN_HEIGHT - 30))

    btn_rect2 = (SCREEN_WIDTH - 170, SCREEN_HEIGHT - 36, 120, 32)
    pygame.draw.rect(surface, (60, 60, 120), btn_rect2)
    pygame.draw.rect(surface, WHITE, btn_rect2, 1)
    btn_text2 = font.render("Recruit [R]", True, WHITE)
    surface.blit(btn_text2, (btn_rect2[0] + 12, btn_rect2[1] + 7))

    if hasattr(scene, '_save_notification_timer') and scene._save_notification_timer > 0:
        save_text = font.render("Game Saved!", True, (100, 255, 100))
        surface.blit(save_text, (SCREEN_WIDTH // 2 - save_text.get_width() // 2, 45))

    if scene.paused:
        pause_text = get_font(36).render("PAUSED", True, (255, 200, 100))
        surface.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, 45))

    if scene.notifications:
        notif_y = 75 if scene.paused else 45
        for text, timer in scene.notifications[-4:]:
            alpha = min(255, timer * 3)
            notif_surf = small_font.render(text, True, (220, 220, 200))
            notif_alpha_surf = pygame.Surface(notif_surf.get_size(), pygame.SRCALPHA)
            notif_alpha_surf.fill((0, 0, 0, 0))
            notif_alpha_surf.blit(notif_surf, (0, 0))
            notif_alpha_surf.set_alpha(alpha)
            surface.blit(notif_alpha_surf, (10, notif_y))
            notif_y += 18

    if scene.trade_warning:
        warning = small_font.render(scene.trade_warning, True, (255, 180, 80))
        surface.blit(warning, (SCREEN_WIDTH - warning.get_width() - 12, 45))

    if scene.selected_settlement:
        scene._draw_settlement_info(surface, font, small_font)

    if scene.player_army.selected:
        panel = pygame.Surface((280, 300), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        surface.blit(panel, (SCREEN_WIDTH - 290, 45))
        scene.player_army.draw_info_panel(
            surface, SCREEN_WIDTH - 280, 50, font, small_font)

    if getattr(scene, '_selected_army', None) and scene._selected_army in scene.armies:
        scene._draw_army_info_panel(surface, font, small_font)


def draw_settlement_info(scene, surface, font, small_font):
    s = scene.selected_settlement
    panel_h = 160 if scene._is_tournament_available(s) else 140
    panel = pygame.Surface((250, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 180))
    surface.blit(panel, (SCREEN_WIDTH - 260, 45))

    x, y = SCREEN_WIDTH - 250, 50
    name_text = font.render(f"{s.name} ({s.settlement_type.title()})", True, WHITE)
    surface.blit(name_text, (x, y))
    y += 22
    faction_names = {f.team: f.name for f in scene.factions}
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
    team_color = TEAM_COLORS.get(s.owner, GREY)
    pygame.draw.rect(surface, team_color, (x, y, 15, 15))
    pygame.draw.rect(surface, WHITE, (x, y, 15, 15), 1)
    state_text = small_font.render(
        f" {scene.diplomacy.get_state(0, s.owner).upper()}"
        if s.owner is not None and s.owner != 0 else "",
        True, (180, 180, 180))
    surface.blit(state_text, (x + 20, y))
    y += 20

    if scene._is_tournament_available(s):
        tourney_text = small_font.render("Tournament available!", True, (255, 215, 0))
        surface.blit(tourney_text, (x, y))


def draw_army_info_panel(scene, surface, font, small_font):
    """Draw info panel for a selected NPC army."""
    army = scene._selected_army
    panel_h = 180
    panel = pygame.Surface((260, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 190))
    surface.blit(panel, (SCREEN_WIDTH - 270, 45))

    x, y = SCREEN_WIDTH - 260, 50
    team_color = TEAM_COLORS.get(army.team, GREY)
    pygame.draw.rect(surface, team_color, (x, y, 12, 12))
    name_text = font.render(f" {army.general_name}", True, WHITE)
    surface.blit(name_text, (x + 16, y - 3))
    y += 22

    faction_names = {f.team: f.name for f in scene.factions}
    faction_name = faction_names.get(army.team, "Roaming")
    faction_text = small_font.render(f"Faction: {faction_name}", True, (180, 180, 180))
    surface.blit(faction_text, (x, y))
    y += 18

    str_text = small_font.render(f"Soldiers: {army.total_soldiers}", True, WHITE)
    surface.blit(str_text, (x, y))
    y += 18

    loc_text = small_font.render(f"Location: {army.current_location}", True, (180, 180, 180))
    surface.blit(loc_text, (x, y))
    y += 18

    status_text = small_font.render(f"Status: {army.current_status}", True, (180, 180, 180))
    surface.blit(status_text, (x, y))
    y += 18

    if army.team in ROAMING_TYPES:
        state_str = "HOSTILE"
        state_color = (255, 80, 80)
    else:
        state = scene.diplomacy.get_state(0, army.team)
        state_str = state.upper()
        if state == DiplomacyState.WAR:
            state_color = (255, 80, 80)
        elif state in (DiplomacyState.FRIENDLY,):
            state_color = (80, 200, 80)
        elif state == DiplomacyState.ALLIED:
            state_color = (80, 255, 80)
        else:
            state_color = (200, 200, 100)
    state_text = small_font.render(f"Relations: {state_str}", True, state_color)
    surface.blit(state_text, (x, y))
    y += 18

    d = distance(scene.player_army.x, scene.player_army.y, army.x, army.y)
    if d < PERSUASION_RANGE:
        hint = small_font.render("[P] Persuade  [E] Interact", True, GOLD)
    else:
        hint = small_font.render("Move closer to interact", True, (150, 150, 150))
    surface.blit(hint, (x, y))


# ---------------------------------------------------------------------------
# Diplomacy panel
# ---------------------------------------------------------------------------

def draw_diplomacy(scene, surface):
    """Draw scrollable diplomacy overview panel."""
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

    content_top = panel_y + 45
    content_bottom = panel_y + panel_h - 30
    content_h = content_bottom - content_top

    non_player = [f for f in scene.factions if not f.is_player]
    state_colors = {
        DiplomacyState.WAR: (220, 50, 50),
        DiplomacyState.HOSTILE: (200, 130, 50),
        DiplomacyState.NEUTRAL: (180, 180, 180),
        DiplomacyState.FRIENDLY: (100, 200, 100),
        DiplomacyState.ALLIED: (50, 150, 255),
    }

    total_h = 0
    for i, faction in enumerate(non_player):
        total_h += 20 + 18 + 16 + 10
        faction_armies = [a for a in scene.armies if a.team == faction.team]
        total_h += min(len(faction_armies), 2) * 14
    total_h += 30

    max_scroll = max(0, total_h - content_h)
    scene._diplomacy_scroll = min(scene._diplomacy_scroll, max_scroll)

    content_surf = pygame.Surface((panel_w - 4, content_h), pygame.SRCALPHA)
    content_surf.fill((0, 0, 0, 0))

    y = -scene._diplomacy_scroll

    for i, faction in enumerate(non_player):
        rel = scene.diplomacy.get_relation(0, faction.team)
        state = scene.diplomacy.get_state(0, faction.team)
        color = state_colors.get(state, WHITE)
        team_color = TEAM_COLORS.get(faction.team, GREY)

        if 0 <= y < content_h:
            pygame.draw.rect(content_surf, team_color, (13, y + 2, 12, 12))
            name_text = small.render(f"[{i+1}] {faction.name}", True, team_color)
            content_surf.blit(name_text, (30, y))
            state_text = small.render(f"{state.upper()} ({rel:+d})", True, color)
            content_surf.blit(state_text, (248, y))
            pers = tiny.render(f"({faction.personality})", True, (120, 120, 120))
            content_surf.blit(pers, (398, y + 2))

        y += 20

        if 0 <= y < content_h:
            if state == DiplomacyState.WAR:
                hint = tiny.render(f"  Press [{i+1}] to propose peace", True, (150, 150, 150))
            elif state == DiplomacyState.FRIENDLY:
                if scene.player_faction is None and rel >= FACTION_JOIN_THRESHOLD:
                    hint = tiny.render(f"  Press [{i+1}] to JOIN this faction!", True, (100, 255, 100))
                else:
                    hint = tiny.render(f"  Press [{i+1}] to propose alliance", True, (150, 150, 150))
            elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                hint = tiny.render(f"  Press [{i+1}] to declare war", True, (150, 150, 150))
            else:
                hint = tiny.render(f"  Allied", True, (100, 200, 255))
            content_surf.blit(hint, (28, y))
        y += 18

        owned = sum(1 for s in scene.settlements if s.owner == faction.team)
        faction_armies = [a for a in scene.armies if a.team == faction.team]
        if 0 <= y < content_h:
            info = tiny.render(
                f"  Settlements: {owned}  |  Armies: {len(faction_armies)}",
                True, (140, 140, 140))
            content_surf.blit(info, (28, y))
        y += 16

        for army in faction_armies[:2]:
            if 0 <= y < content_h:
                gen_opinion = scene.diplomacy.get_general_opinion(army.general_name)
                ai = scene.ai_controllers.get(id(army))
                personality_str = f" ({ai.personality})" if ai else ""
                op_color = (100, 200, 100) if gen_opinion > 0 else (200, 100, 100) if gen_opinion < 0 else (150, 150, 150)
                gt = tiny.render(
                    f"    {army.general_name}{personality_str}: {gen_opinion:+d}",
                    True, op_color)
                content_surf.blit(gt, (28, y))
            y += 14
        y += 10

    if 0 <= y < content_h:
        if scene.player_faction is not None:
            if scene.player_faction == 0:
                player_settlements = sum(1 for s in scene.settlements if s.owner == 0)
                status = small.render(
                    f"Your Faction | Settlements: {player_settlements} [L] Dissolve",
                    True, (100, 255, 200))
            else:
                f_obj = FACTION_BY_TEAM.get(scene.player_faction)
                f_name = f_obj.name if f_obj else "Unknown"
                status = small.render(f"Vassal of {f_name}  [L] Leave Faction", True, (100, 200, 255))
            content_surf.blit(status, (13, y + 5))
        else:
            own_settlements = sum(1 for s in scene.settlements if s.owner == 0)
            if own_settlements > 0:
                status = small.render("Own settlements! Capture neutral to found faction.", True, (100, 255, 100))
            else:
                status = small.render("Independent. +50 rep to join, or capture settlement.", True, (220, 160, 60))
            content_surf.blit(status, (13, y + 5))

    surface.blit(content_surf, (panel_x + 2, content_top))

    if max_scroll > 0:
        scrollbar_h = max(20, int(content_h * content_h / total_h))
        scrollbar_y = content_top + int((content_h - scrollbar_h) * scene._diplomacy_scroll / max_scroll)
        pygame.draw.rect(surface, (80, 80, 100),
                         (panel_x + panel_w - 10, scrollbar_y, 6, scrollbar_h))

    footer = tiny.render("[ESC] Close | Numbers to interact | Scroll to browse", True, (150, 150, 150))
    surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                          panel_y + panel_h - 25))


# ---------------------------------------------------------------------------
# Quest log
# ---------------------------------------------------------------------------

def draw_quest_log(scene, surface):
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
    active = scene.quest_manager.active_quests
    if not active:
        t = small.render("No active quests. Visit a settlement bounty board!", True, (150, 150, 150))
        surface.blit(t, (panel_x + 20, y))
    else:
        for q in active:
            qt = small.render(q.title, True, WHITE)
            surface.blit(qt, (panel_x + 20, y))
            y += 20

            desc = tiny.render(q.description, True, (160, 160, 160))
            surface.blit(desc, (panel_x + 30, y))
            y += 16

            progress_parts = []
            if q.is_kill_quest:
                progress_parts.append(f"Kills: {q.kills_done}/{q.kill_count}")
            if q.time_limit > 0:
                progress_parts.append(f"Days left: {q.days_remaining}")
            progress_parts.append(f"Reward: {q.gold_reward}g")
            prog = tiny.render("  ".join(progress_parts), True, (180, 180, 100))
            surface.blit(prog, (panel_x + 30, y))
            y += 22

    y = max(y + 10, panel_y + panel_h - 120)
    pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
    y += 5
    bb = small.render("Bounty Board (varies by settlement/faction)", True, (200, 180, 100))
    surface.blit(bb, (panel_x + 20, y))
    y += 22
    for q in scene.quest_manager.bounty_board[:3]:
        qt = tiny.render(f"  {q.title} - {q.gold_reward}g", True, (140, 140, 140))
        surface.blit(qt, (panel_x + 20, y))
        y += 16

    footer = tiny.render("[Q] Close  |  Accept quests at settlement bounty boards", True, (150, 150, 150))
    surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                          panel_y + panel_h - 25))


# ---------------------------------------------------------------------------
# Persuasion overlay
# ---------------------------------------------------------------------------

def draw_persuasion(scene, surface):
    """B6: Draw persuasion dialog overlay."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    target = scene.persuasion_target
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
    gm = scene.general_manager
    info = gm.generals.get(name, {})
    loyalty = info.get("loyalty", 70)
    personality = info.get("personality", "unknown")
    gen_opinion = scene.diplomacy.get_general_opinion(name)
    faction_name = "Unknown"
    for f in scene.factions:
        if f.team == target.team:
            faction_name = f.name
            break

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

    pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
    y += 10

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


# ---------------------------------------------------------------------------
# Prisoners panel
# ---------------------------------------------------------------------------

def draw_prisoners(scene, surface):
    """D6: Draw prisoner management panel."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    gm = scene.general_manager
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
        selected = getattr(scene, '_prisoner_selected', None)
        for i, p in enumerate(prisoners):
            is_selected = (i == selected)
            bg = (50, 50, 70) if is_selected else (35, 35, 50)
            row_rect = (panel_x + 10, y, panel_w - 20, 40)
            pygame.draw.rect(surface, bg, row_rect)
            if is_selected:
                pygame.draw.rect(surface, GOLD, row_rect, 1)

            faction_name = "Unknown"
            for f in scene.factions:
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

    if getattr(scene, 'prisoner_action_msg', None):
        y += 10
        msg_text = small.render(scene.prisoner_action_msg, True, (255, 220, 100))
        surface.blit(msg_text, (panel_x + 15, y))

    footer = tiny.render(
        "[1-9] Select  |  [R]ansom [C]recruit [X]execute  |  [J/ESC] Close",
        True, (150, 150, 150))
    surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                          panel_y + panel_h - 25))


# ---------------------------------------------------------------------------
# Companion panel
# ---------------------------------------------------------------------------

def draw_companion_panel(scene, surface):
    """Draw companion management panel overlay."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    companions = scene.companion_manager.companions
    max_comp = scene.player_character.max_companions if scene.player_character else 0

    panel_w, panel_h = 520, 440
    panel_x = SCREEN_WIDTH // 2 - panel_w // 2
    panel_y = 80
    pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

    font = get_font(28)
    small = get_font(20)
    tiny = get_font(16)

    title = font.render(f"Companions ({len(companions)}/{max_comp})", True, GOLD)
    surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

    y = panel_y + 50
    if not companions:
        t = small.render("No companions in your party.", True, (150, 150, 150))
        surface.blit(t, (panel_x + 20, y))
        y += 30
        if max_comp == 0:
            hint = tiny.render("Reach level 5 to unlock companion slots.", True, (120, 120, 120))
        else:
            hint = tiny.render("Visit a tavern [T] near a settlement to recruit.", True, (120, 120, 120))
        surface.blit(hint, (panel_x + 20, y))
    else:
        selected = getattr(scene, '_companion_selected', None)
        for i, c in enumerate(companions):
            is_selected = (i == selected)
            bg = (50, 50, 70) if is_selected else (35, 35, 50)
            row_rect = (panel_x + 10, y, panel_w - 20, 58)
            pygame.draw.rect(surface, bg, row_rect)
            if is_selected:
                pygame.draw.rect(surface, GOLD, row_rect, 1)

            name_text = small.render(
                f"[{i+1}] {c.name}  Lv{c.level} {c.race.capitalize()} {c.companion_class.capitalize()}",
                True, WHITE)
            surface.blit(name_text, (panel_x + 15, y + 4))

            status = "Active" if c.alive else f"Captured ({c.capture_timer}d)"
            detail = tiny.render(
                f"    {c.personality.capitalize()} | {status}",
                True, (160, 160, 160))
            surface.blit(detail, (panel_x + 15, y + 26))

            bar_x = panel_x + panel_w - 130
            bar_y = y + 8
            bar_w = 100
            bar_h = 12
            pygame.draw.rect(surface, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            loyalty_w = int(bar_w * c.loyalty / 100)
            loyalty_color = (80, 200, 80) if c.loyalty >= 50 else (200, 200, 50) if c.loyalty >= 25 else (200, 60, 60)
            pygame.draw.rect(surface, loyalty_color, (bar_x, bar_y, loyalty_w, bar_h))
            pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)
            loy_text = tiny.render(f"{c.loyalty}", True, WHITE)
            surface.blit(loy_text, (bar_x + bar_w + 5, bar_y - 2))

            y += 62

        if selected is not None and selected < len(companions):
            y += 5
            pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
            y += 8
            c = companions[selected]
            detail_text = small.render(
                f"[D] Dismiss {c.name}", True, (255, 180, 100))
            surface.blit(detail_text, (panel_x + 15, y))

    footer = tiny.render(
        "[1-5] Select  |  [D] Dismiss  |  [N/ESC] Close",
        True, (150, 150, 150))
    surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                          panel_y + panel_h - 25))


# ---------------------------------------------------------------------------
# Tavern panel
# ---------------------------------------------------------------------------

def draw_tavern_panel(scene, surface):
    """Draw tavern companion recruitment panel overlay."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    tavern = scene._tavern_companions
    settlement_name = scene._tavern_settlement.name if scene._tavern_settlement else "Unknown"
    max_comp = scene.player_character.max_companions if scene.player_character else 0
    current = len(scene.companion_manager.companions)

    panel_w, panel_h = 540, 420
    panel_x = SCREEN_WIDTH // 2 - panel_w // 2
    panel_y = 80
    pygame.draw.rect(surface, (30, 30, 40), (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(surface, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

    font = get_font(28)
    small = get_font(20)
    tiny = get_font(16)

    title = font.render(f"Tavern - {settlement_name}", True, GOLD)
    surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 10))

    slots_color = (80, 200, 80) if current < max_comp else (200, 60, 60)
    slots_text = small.render(f"Companion Slots: {current}/{max_comp}", True, slots_color)
    surface.blit(slots_text, (panel_x + panel_w // 2 - slots_text.get_width() // 2, panel_y + 42))

    gold_text = tiny.render(f"Gold: {scene.player_army.gold}", True, GOLD)
    surface.blit(gold_text, (panel_x + panel_w - 120, panel_y + 46))

    y = panel_y + 72
    if not tavern:
        t = small.render("No companions available at this tavern.", True, (150, 150, 150))
        surface.blit(t, (panel_x + 20, y))
    else:
        for i, c in enumerate(tavern):
            bg = (35, 35, 50)
            row_rect = (panel_x + 10, y, panel_w - 20, 72)
            pygame.draw.rect(surface, bg, row_rect)
            pygame.draw.rect(surface, (60, 60, 80), row_rect, 1)

            cost = c.level * 50
            can_afford = scene.player_army.gold >= cost
            has_slot = current < max_comp

            name_color = WHITE if (can_afford and has_slot) else (120, 120, 120)
            name_text = small.render(
                f"[{i+1}] {c.name}  -  Lv{c.level} {c.race.capitalize()} {c.companion_class.capitalize()}",
                True, name_color)
            surface.blit(name_text, (panel_x + 15, y + 6))

            detail = tiny.render(
                f"    Personality: {c.personality.capitalize()}  |  Loyalty: {c.loyalty}",
                True, (160, 160, 160))
            surface.blit(detail, (panel_x + 15, y + 28))

            cost_color = GOLD if can_afford else (200, 60, 60)
            cost_text = small.render(f"{cost}g", True, cost_color)
            surface.blit(cost_text, (panel_x + panel_w - 70, y + 6))

            if not has_slot:
                hint = tiny.render("No slots", True, (200, 60, 60))
                surface.blit(hint, (panel_x + panel_w - 80, y + 50))
            elif not can_afford:
                hint = tiny.render("Can't afford", True, (200, 60, 60))
                surface.blit(hint, (panel_x + panel_w - 100, y + 50))

            y += 76

    footer = tiny.render(
        "[1-3] Recruit  |  [T/ESC] Close",
        True, (150, 150, 150))
    surface.blit(footer, (panel_x + panel_w // 2 - footer.get_width() // 2,
                          panel_y + panel_h - 25))


# ---------------------------------------------------------------------------
# Capture overlay
# ---------------------------------------------------------------------------

def draw_capture_overlay(scene, surface):
    """D6: Draw player capture state overlay."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    cap = scene.general_manager.player_capture
    font = get_font(40)
    small = get_font(24)
    tiny = get_font(18)

    title = font.render("YOU ARE CAPTURED", True, (220, 60, 60))
    surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))

    captor_name = "Unknown"
    for f in scene.factions:
        if f.team == cap.captor_team:
            captor_name = f.name
            break

    y = 260
    info_lines = [
        f"Held by: {captor_name}",
        f"Days remaining: {cap.days_remaining}",
        f"Ransom cost: {cap.ransom_cost} gold (you have {scene.player_army.gold})",
        "",
        "Your army is dispersing while you are held captive.",
        "You will automatically escape when the timer runs out,",
        "but your army will be weakened.",
    ]
    for line in info_lines:
        text = small.render(line, True, WHITE)
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
        y += 28

    if scene.player_army.gold >= cap.ransom_cost:
        opt = small.render("[R] Pay Ransom", True, GOLD)
    else:
        opt = small.render("[R] Pay Ransom (not enough gold)", True, (120, 120, 120))
    surface.blit(opt, (SCREEN_WIDTH // 2 - opt.get_width() // 2, y + 20))

    wait = tiny.render("Or wait for automatic escape...", True, (150, 150, 150))
    surface.blit(wait, (SCREEN_WIDTH // 2 - wait.get_width() // 2, y + 50))


# ---------------------------------------------------------------------------
# Army management panel
# ---------------------------------------------------------------------------

def draw_army_panel(scene, surface):
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

    y = panel_y + 45
    pa = scene.player_army
    gen_info = small.render(
        f"General: {pa.general_name} ({pa.general_stats.name}) Lv{pa.general_level}",
        True, WHITE)
    surface.blit(gen_info, (panel_x + 15, y))
    y += 22

    army_info = small.render(
        f"Army: {pa.total_soldiers}/{pa.army_size_limit} soldiers  |  "
        f"Strength: {pa.army_strength}  |  Upkeep: {pa.upkeep}/week",
        True, (180, 180, 180))
    surface.blit(army_info, (panel_x + 15, y))
    y += 22

    gold_info = small.render(f"Gold: {pa.gold}", True, GOLD)
    surface.blit(gold_info, (panel_x + 15, y))
    y += 28

    pygame.draw.line(surface, (80, 80, 100), (panel_x + 10, y), (panel_x + panel_w - 10, y))
    y += 8

    header = tiny.render(
        f"{'#':<3} {'Unit':<22} {'Count':>8} {'Rank':<12} {'Kills':>6} {'Str':>6}",
        True, (140, 140, 140))
    surface.blit(header, (panel_x + 15, y))
    y += 18

    selected = getattr(scene, '_army_panel_selected', 0)
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
