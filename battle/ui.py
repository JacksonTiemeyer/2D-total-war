"""Battle HUD and UI helpers extracted from BattleScene."""

import pygame
from battle.general import DuelState
from battle.squad import Formation
from core.audio import get_audio
from core.settings import (
    GOLD,
    MOVE_MODE_MARCH,
    MOVE_MODE_RUN,
    MOVE_MODE_WALK,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TEAM_COLORS_LIGHT,
    WHITE,
)
from core.utils import get_font


def make_button(x, y, w, h, text, active=False, enabled=True):
    return {"x": x, "y": y, "w": w, "h": h, "text": text, "active": active, "enabled": enabled}


def draw_button(surface, btn, font):
    x, y, w, h = btn["x"], btn["y"], btn["w"], btn["h"]
    if btn["active"]:
        bg_color = (60, 120, 60, 200)
        text_color = (200, 255, 200)
        border_color = (100, 200, 100)
    elif not btn["enabled"]:
        bg_color = (40, 40, 40, 120)
        text_color = (80, 80, 80)
        border_color = (60, 60, 60)
    else:
        bg_color = (50, 50, 60, 180)
        text_color = (200, 200, 210)
        border_color = (100, 100, 120)

    btn_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    btn_surf.fill(bg_color)
    surface.blit(btn_surf, (x, y))
    pygame.draw.rect(surface, border_color, (x, y, w, h), 1)
    text_surf = font.render(btn["text"], True, text_color)
    surface.blit(text_surf, (x + w // 2 - text_surf.get_width() // 2, y + h // 2 - text_surf.get_height() // 2))
    return pygame.Rect(x, y, w, h)


def point_in_button(pos, btn):
    return btn["x"] <= pos[0] <= btn["x"] + btn["w"] and btn["y"] <= pos[1] <= btn["y"] + btn["h"]


def handle_ui_click(scene, pos):
    if not scene._ui_buttons:
        return False
    for btn_id, btn in scene._ui_buttons.items():
        if not btn["enabled"]:
            continue
        if point_in_button(pos, btn):
            on_ui_button_click(scene, btn_id)
            return True
    for i, card_rect in enumerate(scene._unit_card_rects):
        if card_rect.collidepoint(pos):
            on_unit_card_click(scene, i)
            return True
    return False


def on_ui_button_click(scene, btn_id):
    if btn_id == "pause":
        scene.paused = not scene.paused
    elif btn_id == "speed1":
        scene.speed_multiplier = 1
    elif btn_id == "speed2":
        scene.speed_multiplier = 2
    elif btn_id == "speed3":
        scene.speed_multiplier = 4
    elif btn_id == "fog_toggle":
        scene.fog_enabled = not scene.fog_enabled
    elif btn_id == "walk":
        for sq in scene.selected_squads:
            sq.movement_mode = MOVE_MODE_WALK
    elif btn_id == "march":
        for sq in scene.selected_squads:
            sq.movement_mode = MOVE_MODE_MARCH
    elif btn_id == "run":
        for sq in scene.selected_squads:
            sq.movement_mode = MOVE_MODE_RUN
    elif btn_id == "defensive":
        for sq in scene.selected_squads:
            sq.defensive_stance = not sq.defensive_stance
            if sq.defensive_stance:
                sq.defensive_anchor_x = sq.x
                sq.defensive_anchor_y = sq.y
    elif btn_id == "skirmish":
        for sq in scene.selected_squads:
            if sq.is_ranged:
                sq.skirmish_stance = not sq.skirmish_stance
    elif btn_id == "fire":
        for sq in scene.selected_squads:
            if sq.is_ranged:
                sq.fire_at_will = not sq.fire_at_will
    elif btn_id.startswith("form_"):
        form_map = {
            "form_line": Formation.LINE,
            "form_column": Formation.COLUMN,
            "form_square": Formation.SQUARE,
            "form_loose": Formation.LOOSE,
            "form_wedge": Formation.WEDGE,
        }
        if btn_id in form_map:
            for sq in scene.selected_squads:
                sq.set_formation(form_map[btn_id])
    elif btn_id.startswith("ability_"):
        idx = int(btn_id.split("_")[1])
        if scene.selected_general:
            friendly = scene.player_squads if scene.selected_general.team == 0 else scene.enemy_squads
            enemy = scene.enemy_squads if scene.selected_general.team == 0 else scene.player_squads
            if scene.selected_general.activate_ability(idx, friendly, enemy):
                get_audio().play("ability")


def on_unit_card_click(scene, index):
    alive_squads = [sq for sq in scene.player_squads if not sq.is_destroyed]
    if index < len(alive_squads):
        for sq in scene.player_squads:
            sq.selected = False
        for g in scene.player_generals:
            g.selected = False
        scene.selected_general = None
        sq = alive_squads[index]
        sq.selected = True
        scene.selected_squads = [sq]


def draw_hud(scene, surface):
    font = get_font(20)
    small_font = get_font(16)
    btn_font = get_font(15)
    scene._ui_buttons = {}
    scene._unit_card_rects = []

    bar_surf = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
    bar_surf.fill((0, 0, 0, 160))
    surface.blit(bar_surf, (0, 0))

    minutes = scene.battle_timer // (60 * 60)
    seconds = (scene.battle_timer // 60) % 60
    timer_text = font.render(f"Battle: {minutes:02d}:{seconds:02d}", True, WHITE)
    surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 8))

    for i, (label, spd, btn_id) in enumerate([("1x", 1, "speed1"), ("2x", 2, "speed2"), ("4x", 4, "speed3")]):
        bx = SCREEN_WIDTH // 2 + 80 + i * 36
        btn = make_button(bx, 4, 32, 26, label, active=(scene.speed_multiplier == spd))
        scene._ui_buttons[btn_id] = btn
        draw_button(surface, btn, btn_font)

    pause_x = SCREEN_WIDTH // 2 + 80 + 3 * 36 + 8
    pause_btn = make_button(pause_x, 4, 55, 26, "PAUSED" if scene.paused else "Pause", active=scene.paused)
    scene._ui_buttons["pause"] = pause_btn
    draw_button(surface, pause_btn, btn_font)

    fog_x = pause_x + 60
    fog_btn = make_button(fog_x, 4, 65, 26, "FOG: ON" if scene.fog_enabled else "FOG: OFF", active=scene.fog_enabled)
    scene._ui_buttons["fog_toggle"] = fog_btn
    draw_button(surface, fog_btn, btn_font)

    if scene.weather != "clear":
        weather_colors = {"rain": (100, 150, 255), "fog": (180, 180, 200), "mud": (160, 120, 60), "wind": (180, 200, 160)}
        wc = weather_colors.get(scene.weather, WHITE)
        w_text = font.render(f"Weather: {scene.weather.title()}", True, wc)
        surface.blit(w_text, (SCREEN_WIDTH // 2 - 250, 8))

    p_alive = sum(sq.alive_count for sq in scene.player_squads)
    e_alive = sum(sq.alive_count for sq in scene.enemy_squads)
    p_text = font.render(f"Your Army: {p_alive}", True, TEAM_COLORS_LIGHT[0])
    e_text = font.render(f"Enemy Army: {e_alive}", True, TEAM_COLORS_LIGHT[1])
    surface.blit(p_text, (10, 8))
    surface.blit(e_text, (SCREEN_WIDTH - e_text.get_width() - 10, 8))

    panel_h = 110
    panel_y = SCREEN_HEIGHT - panel_h
    panel_surf = pygame.Surface((SCREEN_WIDTH, panel_h), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 180))
    surface.blit(panel_surf, (0, panel_y))
    pygame.draw.line(surface, (80, 80, 100), (0, panel_y), (SCREEN_WIDTH, panel_y), 1)

    draw_unit_cards(scene, surface, panel_y, small_font, btn_font)

    if scene.selected_squads:
        draw_selection_panel(scene, surface, font, small_font, btn_font, panel_y)
    elif scene.selected_general:
        draw_general_panel(scene, surface, font, small_font, btn_font, panel_y)

    if scene.result != "ongoing":
        draw_result_banner(scene, surface)


def draw_unit_cards(scene, surface, panel_y, small_font, btn_font):
    alive_squads = [sq for sq in scene.player_squads if not sq.is_destroyed]
    card_w = 58
    card_h = 40
    card_y = panel_y + 65
    start_x = 10
    scene._unit_card_rects = []

    for i, sq in enumerate(alive_squads):
        cx = start_x + i * (card_w + 4)
        if cx + card_w > SCREEN_WIDTH - 10:
            break
        is_selected = sq in scene.selected_squads
        bg_color = (60, 100, 60, 200) if is_selected else (40, 40, 50, 180)
        border_color = (100, 200, 100) if is_selected else (70, 70, 90)

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill(bg_color)
        surface.blit(card_surf, (cx, card_y))
        pygame.draw.rect(surface, border_color, (cx, card_y, card_w, card_h), 1)

        text = btn_font.render(sq.unit_stats.name[:5], True, TEAM_COLORS_LIGHT[sq.team])
        surface.blit(text, (cx + 2, card_y + 2))
        count_text = btn_font.render(f"{sq.alive_count}", True, WHITE)
        surface.blit(count_text, (cx + 2, card_y + 15))

        bar_x = cx + 2
        bar_y_pos = card_y + card_h - 8
        bar_w = card_w - 4
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y_pos, bar_w, 4))
        morale_w = int(bar_w * sq.morale / 100)
        morale_color = (50, 200, 50) if sq.morale > 50 else ((220, 200, 50) if sq.morale > 25 else (200, 50, 50))
        pygame.draw.rect(surface, morale_color, (bar_x, bar_y_pos, morale_w, 4))
        scene._unit_card_rects.append(pygame.Rect(cx, card_y, card_w, card_h))


def draw_selection_panel(scene, surface, font, small_font, btn_font, panel_y):
    y = panel_y + 4
    sq = scene.selected_squads[0] if len(scene.selected_squads) == 1 else None

    if sq:
        info = f"{sq.unit_stats.name}: {sq.alive_count}/{sq.initial_count}  Morale:{int(sq.morale)}%  {sq.exhaustion_display}"
        surface.blit(small_font.render(info, True, TEAM_COLORS_LIGHT[sq.team]), (10, y))
        y += 16
        extra = f"WS:{sq.unit_stats.weapon_strength} AP:{sq.unit_stats.armor_penetration}%"
        if sq.unit_stats.ranged_strength > 0:
            extra += f"  RS:{sq.unit_stats.ranged_strength} RAP:{sq.unit_stats.ranged_armor_penetration}%"
        if sq.is_braced:
            extra += "  BRACED"
        if sq.max_mana > 0:
            extra += f"  Mana:{int(sq.mana)}/{sq.max_mana}"
        surface.blit(small_font.render(extra, True, (160, 160, 160)), (10, y))
        if sq.max_mana > 0 and sq.available_spells:
            y += 16
            sp = sq.available_spells[sq._selected_spell_index] if sq._selected_spell_index < len(sq.available_spells) else sq.available_spells[0]
            cd = sq.spell_cooldowns.get(sp.name, 0)
            cd_s = f" CD:{cd // 60}s" if cd > 0 else " READY"
            spell_info = f"[G] Cast: {sp.name} ({sp.mana_cost}mp){cd_s}  [Tab] cycle"
            spell_color = (100, 180, 255) if sq._spell_targeting else (140, 140, 180)
            surface.blit(small_font.render(spell_info, True, spell_color), (10, y))
    else:
        count = len(scene.selected_squads)
        total = sum(sq.alive_count for sq in scene.selected_squads)
        surface.blit(font.render(f"{count} units selected ({total} soldiers)", True, WHITE), (10, y))

    btn_y = panel_y + 4
    btn_x = 350
    surface.blit(small_font.render("Move:", True, (150, 150, 160)), (btn_x, btn_y + 2))
    btn_x += 40
    active_mode = scene.selected_squads[0].movement_mode if scene.selected_squads else MOVE_MODE_MARCH
    for label, mode, bid in [("Walk", MOVE_MODE_WALK, "walk"), ("March", MOVE_MODE_MARCH, "march"), ("Run", MOVE_MODE_RUN, "run")]:
        btn = make_button(btn_x, btn_y, 44, 20, label, active=(active_mode == mode))
        scene._ui_buttons[bid] = btn
        draw_button(surface, btn, btn_font)
        btn_x += 48

    btn_x += 8
    surface.blit(small_font.render("Stance:", True, (150, 150, 160)), (btn_x, btn_y + 2))
    btn_x += 50
    any_def = any(sq.defensive_stance for sq in scene.selected_squads)
    btn = make_button(btn_x, btn_y, 60, 20, "Defensive", active=any_def)
    scene._ui_buttons["defensive"] = btn
    draw_button(surface, btn, btn_font)
    btn_x += 64

    any_skirm = any(sq.skirmish_stance for sq in scene.selected_squads)
    has_ranged = any(sq.is_ranged for sq in scene.selected_squads)
    btn = make_button(btn_x, btn_y, 58, 20, "Skirmish", active=any_skirm, enabled=has_ranged)
    scene._ui_buttons["skirmish"] = btn
    draw_button(surface, btn, btn_font)
    btn_x += 62

    any_fire = any(sq.fire_at_will for sq in scene.selected_squads if sq.is_ranged)
    btn = make_button(btn_x, btn_y, 48, 20, "Fire", active=any_fire, enabled=has_ranged)
    scene._ui_buttons["fire"] = btn
    draw_button(surface, btn, btn_font)

    btn_y2 = panel_y + 30
    btn_x2 = 350
    surface.blit(small_font.render("Formation:", True, (150, 150, 160)), (btn_x2, btn_y2 + 2))
    btn_x2 += 72
    active_form = scene.selected_squads[0].formation if scene.selected_squads else Formation.LINE
    for label, form, bid in [("Line", Formation.LINE, "form_line"), ("Column", Formation.COLUMN, "form_column"), ("Square", Formation.SQUARE, "form_square"), ("Loose", Formation.LOOSE, "form_loose"), ("Wedge", Formation.WEDGE, "form_wedge")]:
        btn = make_button(btn_x2, btn_y2, 48, 20, label, active=(active_form == form))
        scene._ui_buttons[bid] = btn
        draw_button(surface, btn, btn_font)
        btn_x2 += 52


def draw_general_panel(scene, surface, font, small_font, btn_font, panel_y):
    g = scene.selected_general
    y = panel_y + 4
    surface.blit(font.render(f"{g.name} ({g.general_type}) Lv{g.level}", True, GOLD), (10, y))
    y += 20
    hp = f"HP: {int(g.health)}/{int(g.max_health)}  ATK:{g.melee_attack} DEF:{g.melee_defense}  Kills:{g.kills} Duels:{g.duels_won}"
    surface.blit(small_font.render(hp, True, WHITE), (10, y))
    y += 16

    if g.duel_state == DuelState.ACTIVE:
        duel_text = f"DUELING {g.duel_opponent.name}! Score: {g.duel_score}-{g.duel_opponent.duel_score}"
        surface.blit(small_font.render(duel_text, True, GOLD), (10, y))

    if g.max_mana > 0 and g.available_spells:
        surface.blit(small_font.render(f"Mana: {int(g.mana)}/{g.max_mana}", True, (100, 180, 255)), (10, y))
        y += 16
        sp = g.available_spells[g._selected_spell_index] if g._selected_spell_index < len(g.available_spells) else g.available_spells[0]
        cd = g.spell_cooldowns.get(sp.name, 0)
        cd_s = f" CD:{cd // 60}s" if cd > 0 else " READY"
        spell_info = f"[G] Cast: {sp.name} ({sp.mana_cost}mp){cd_s}  [Tab] cycle"
        spell_color = (100, 180, 255) if g._spell_targeting else (140, 140, 180)
        surface.blit(small_font.render(spell_info, True, spell_color), (10, y))

    btn_x = 400
    btn_y = panel_y + 4
    keys = ["Q", "W", "E", "R"]
    for i, ability in enumerate(g.available_abilities):
        if i >= 4:
            break
        cd_text = f" {ability.cooldown // 60}s" if not ability.ready else ""
        label = f"[{keys[i]}] {ability.name}{cd_text}"
        btn = make_button(btn_x, btn_y + i * 24, 200, 20, label, active=False, enabled=ability.ready)
        scene._ui_buttons[f"ability_{i}"] = btn
        draw_button(surface, btn, btn_font)

    lock_y = btn_y + len(g.available_abilities) * 24
    for ability in g.abilities:
        if ability.level_required > g.level:
            surface.blit(small_font.render(f"Lv{ability.level_required}: {ability.name} (Locked)", True, (80, 80, 80)), (btn_x, lock_y))
            lock_y += 16


def draw_result_banner(scene, surface):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))
    surface.blit(overlay, (0, 0))
    big_font = get_font(72)
    is_victory = scene.result == "player_win"
    text = big_font.render("VICTORY!" if is_victory else "DEFEAT!", True, GOLD if is_victory else (200, 50, 50))
    surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
    font = get_font(28)
    sub = font.render("Press ENTER to continue", True, WHITE)
    surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 30))
