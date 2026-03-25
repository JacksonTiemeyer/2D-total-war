"""Battle input and command helpers extracted from BattleScene."""

import pygame

from core.audio import get_audio
from core.settings import GOLD, SCREEN_HEIGHT, SCREEN_WIDTH
from core.utils import angle_between, distance, get_font, point_in_rect


def handle_ability_key(scene, key):
    if not scene.selected_general:
        return
    g = scene.selected_general
    key_map = {pygame.K_q: 0, pygame.K_w: 1, pygame.K_e: 2, pygame.K_r: 3}
    index = key_map.get(key, -1)
    if index < 0:
        return
    friendly = scene.player_squads if g.team == 0 else scene.enemy_squads
    enemy = scene.enemy_squads if g.team == 0 else scene.player_squads
    if g.activate_ability(index, friendly, enemy):
        get_audio().play("ability")


def handle_left_click(scene, pos):
    if hasattr(scene, "_ui_buttons") and scene._handle_ui_click(pos):
        return
    wx, wy = scene.camera.screen_to_world(*pos)
    shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
    if not shift:
        for sq in scene.player_squads:
            sq.selected = False
        for g in scene.player_generals:
            g.selected = False
        scene.selected_squads = []
        scene.selected_general = None

    for g in scene.player_generals:
        if not g.alive:
            continue
        if distance(wx, wy, g.x, g.y) < 20:
            g.selected = True
            scene.selected_general = g
            return

    for sq in scene.player_squads:
        if sq.is_destroyed:
            continue
        bbox = sq.get_bounding_box()
        if point_in_rect(wx, wy, *bbox):
            sq.selected = True
            if sq not in scene.selected_squads:
                scene.selected_squads.append(sq)
            return

    scene.selecting = True
    scene.select_start = pos
    scene.select_end = pos


def finish_box_select(scene, pos):
    scene.selecting = False
    sx1, sy1 = scene.camera.screen_to_world(*scene.select_start)
    sx2, sy2 = scene.camera.screen_to_world(*pos)
    min_x, min_y = min(sx1, sx2), min(sy1, sy2)
    max_x, max_y = max(sx1, sx2), max(sy1, sy2)
    if abs(pos[0] - scene.select_start[0]) < 5:
        return
    for sq in scene.player_squads:
        if sq.is_destroyed:
            continue
        cx, cy = sq.center
        if min_x <= cx <= max_x and min_y <= cy <= max_y:
            sq.selected = True
            if sq not in scene.selected_squads:
                scene.selected_squads.append(sq)
    for g in scene.player_generals:
        if not g.alive:
            continue
        if min_x <= g.x <= max_x and min_y <= g.y <= max_y:
            g.selected = True
            scene.selected_general = g


def handle_deployment_event(scene, event):
    scene.camera.handle_event(event)
    if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE):
        scene.deployment_phase = False
        scene._deploy_dragging = None
        scene.selecting = False
        scene._right_click_pos = None
        scene._right_dragging = False
        scene._right_drag_pos = None
        get_audio().play("click")
        return

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        wx, wy = scene.camera.screen_to_world(*event.pos)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        clicked_squad = None
        for sq in scene.player_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                clicked_squad = sq
                break
        # Also check generals
        clicked_general = None
        for g in scene.player_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                clicked_general = g
                break
        if clicked_squad:
            if not shift:
                for s in scene.player_squads:
                    s.selected = False
                scene.selected_squads = []
            scene._deploy_dragging = clicked_squad
            clicked_squad.selected = True
            if clicked_squad not in scene.selected_squads:
                scene.selected_squads.append(clicked_squad)
        elif clicked_general:
            clicked_general.selected = True
            scene.selected_general = clicked_general
        else:
            # Start marquee selection on empty space
            if not shift:
                for s in scene.player_squads:
                    s.selected = False
                for g in scene.player_generals:
                    g.selected = False
                scene.selected_squads = []
                scene.selected_general = None
            scene.selecting = True
            scene.select_start = event.pos
            scene.select_end = event.pos
        return

    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        if getattr(scene, 'selecting', False):
            finish_box_select(scene, event.pos)
        scene._deploy_dragging = None

    if event.type == pygame.MOUSEMOTION:
        if scene._deploy_dragging:
            wx, wy = scene.camera.screen_to_world(*event.pos)
            zx, zy, zw, zh = scene.deploy_zone
            wx = max(zx + 30, min(zx + zw - 30, wx))
            wy = max(zy + 30, min(zy + zh - 30, wy))
            primary = scene._deploy_dragging
            dx = wx - primary.x
            dy = wy - primary.y
            # Move all selected squads together (maintaining relative offsets)
            for sq in scene.selected_squads:
                new_x = sq.x + dx
                new_y = sq.y + dy
                # Clamp each squad within zone
                new_x = max(zx + 30, min(zx + zw - 30, new_x))
                new_y = max(zy + 30, min(zy + zh - 30, new_y))
                sdx = new_x - sq.x
                sdy = new_y - sq.y
                sq.x = new_x
                sq.y = new_y
                sq.target_x = new_x
                sq.target_y = new_y
                for s in sq.alive_soldiers:
                    s.x += sdx
                    s.y += sdy
        elif getattr(scene, 'selecting', False):
            scene.select_end = event.pos
        elif getattr(scene, '_right_click_pos', None):
            dx_p = event.pos[0] - scene._right_click_pos[0]
            dy_p = event.pos[1] - scene._right_click_pos[1]
            if (dx_p * dx_p + dy_p * dy_p) ** 0.5 > 15:
                scene._right_dragging = True
            scene._right_drag_pos = event.pos

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        scene._right_click_pos = event.pos
        scene._right_click_world = scene.camera.screen_to_world(*event.pos)
        scene._right_dragging = False
        scene._right_drag_pos = event.pos

    if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
        if scene._right_dragging and scene.selected_squads:
            wx2, wy2 = scene.camera.screen_to_world(*event.pos)
            wx1, wy1 = scene._right_click_world
            facing = angle_between(wx1, wy1, wx2, wy2)
            for sq in scene.selected_squads:
                sq.facing_angle = facing
        scene._right_click_pos = None
        scene._right_dragging = False


def draw_deployment(scene, surface):
    zx, zy, zw, zh = scene.deploy_zone
    sx, sy = scene.camera.world_to_screen(zx, zy)
    sw = scene.camera.scale(zw)
    sh = scene.camera.scale(zh)
    zone_surf = pygame.Surface((int(sw), int(sh)), pygame.SRCALPHA)
    zone_surf.fill((100, 150, 255, 30))
    surface.blit(zone_surf, (int(sx), int(sy)))
    pygame.draw.rect(surface, (100, 150, 255, 180), (int(sx), int(sy), int(sw), int(sh)), 2)
    font = get_font(24)
    label = font.render("DEPLOYMENT ZONE", True, (150, 200, 255))
    surface.blit(label, (int(sx) + int(sw) // 2 - label.get_width() // 2, int(sy) + 5))
    big_font = get_font(36)
    title = big_font.render("DEPLOYMENT PHASE", True, GOLD)
    surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
    inst_font = get_font(22)
    instructions = ["Drag units to position them within the blue zone", "Right-click + drag to set facing direction", "Press ENTER or SPACE to start the battle"]
    for i, line in enumerate(instructions):
        text = inst_font.render(line, True, (200, 220, 255))
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 90 + i * 24))
    ready_text = big_font.render("[ PRESS ENTER TO BEGIN ]", True, (200, 255, 200))
    surface.blit(ready_text, (SCREEN_WIDTH // 2 - ready_text.get_width() // 2, SCREEN_HEIGHT - 60))

    # Highlight the squad being dragged
    if scene._deploy_dragging:
        sq = scene._deploy_dragging
        bbox = sq.get_bounding_box()
        bx, by = scene.camera.world_to_screen(bbox[0], bbox[1])
        bw = scene.camera.scale(bbox[2] - bbox[0])
        bh = scene.camera.scale(bbox[3] - bbox[1])
        pygame.draw.rect(surface, (255, 255, 100), (int(bx), int(by), int(bw), int(bh)), 2)


def apply_facing_from_drag(scene, release_pos):
    if not scene._right_click_pos:
        return
    wx1, wy1 = scene._right_click_world
    wx2, wy2 = scene.camera.screen_to_world(*release_pos)
    facing = angle_between(wx1, wy1, wx2, wy2)
    for sq in scene.selected_squads:
        sq.facing_angle = facing


def handle_right_click(scene, pos):
    wx, wy = scene.camera.screen_to_world(*pos)
    if scene._try_spell_cast(wx, wy):
        return
    target_squad = None
    for sq in scene.enemy_squads:
        if sq.is_destroyed or (scene.fog_enabled and not sq.visible):
            continue
        bbox = sq.get_bounding_box()
        if point_in_rect(wx, wy, *bbox):
            target_squad = sq
            break
    target_general = None
    for g in scene.enemy_generals:
        if not g.alive or (scene.fog_enabled and not g.visible):
            continue
        if distance(wx, wy, g.x, g.y) < 20:
            target_general = g
            break
    if target_general and scene.selected_general:
        scene.selected_general.challenge_duel(target_general)
        return
    if scene.selected_squads:
        if target_squad:
            for sq in scene.selected_squads:
                sq.give_attack_order(target_squad)
        elif target_general:
            for sq in scene.selected_squads:
                sq.give_move_order(target_general.x, target_general.y)
        else:
            count = len(scene.selected_squads)
            for i, sq in enumerate(scene.selected_squads):
                offset_y = (i - count / 2.0) * 60
                sq.give_move_order(wx, wy + offset_y)
    if scene.selected_general and not target_general:
        if target_squad:
            scene.selected_general.give_attack_order(target_squad)
        else:
            scene.selected_general.give_move_order(wx, wy)
