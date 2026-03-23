"""Campaign input handler functions.

Click routing, panel button actions, modal event handling, and map interaction commands.
All functions accept the CampaignScene instance as first argument (``scene``).
"""

import pygame
from core.utils import distance
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_SPEED_1X, CAMPAIGN_SPEED_2X, CAMPAIGN_SPEED_3X,
    PERSUASION_RANGE,
    FACTION_JOIN_THRESHOLD,
)
from campaign.diplomacy import DiplomacyState
from campaign.companion import generate_tavern_companions
from campaign.runtime import queue_pending_battle


# ---------------------------------------------------------------------------
# Map click handlers
# ---------------------------------------------------------------------------

def handle_left_click(scene, pos):
    wx, wy = scene.camera.screen_to_world(*pos)
    click_signature = None

    if pos[1] < 36:
        handle_top_bar_click(scene, pos)
        return

    if pos[1] > SCREEN_HEIGHT - 40:
        handle_bottom_bar_click(scene, pos)
        return

    scene.selected_settlement = None
    scene.player_army.selected = False
    scene._selected_army = None

    for s in scene.settlements:
        s.selected = False
        if distance(wx, wy, s.x, s.y) < 30:
            s.selected = True
            scene.selected_settlement = s
            click_signature = ("settlement", id(s))
            if is_double_click(scene, click_signature):
                scene._interact_with_settlement(s)
            return

    for army in scene.armies:
        if army.is_player:
            continue
        if not scene._is_visible(army.x, army.y):
            continue
        if distance(wx, wy, army.x, army.y) < 25:
            scene._selected_army = army
            click_signature = ("army", id(army))
            if is_double_click(scene, click_signature):
                scene._interact_with_army(army)
            return

    if distance(wx, wy, scene.player_army.x, scene.player_army.y) < 20:
        scene.player_army.selected = True
        click_signature = ("player", id(scene.player_army))

    is_double_click(scene, click_signature)


def is_double_click(scene, click_signature):
    """Return True when the same map target is clicked twice quickly."""
    now = pygame.time.get_ticks()
    result = (
        click_signature is not None and
        click_signature == scene._last_click_signature and
        now - scene._last_click_time <= 400
    )
    scene._last_click_signature = click_signature
    scene._last_click_time = now
    return result


def handle_top_bar_click(scene, pos):
    """Handle clicks on the top bar (speed controls)."""
    if 200 <= pos[0] <= 240:
        scene.paused = not scene.paused
        return
    if 245 <= pos[0] <= 275:
        scene.campaign_speed = CAMPAIGN_SPEED_1X
        scene.paused = False
    elif 280 <= pos[0] <= 310:
        scene.campaign_speed = CAMPAIGN_SPEED_2X
        scene.paused = False
    elif 315 <= pos[0] <= 345:
        scene.campaign_speed = CAMPAIGN_SPEED_3X
        scene.paused = False


def handle_bottom_bar_click(scene, pos):
    """Handle clicks on the bottom bar."""
    if SCREEN_WIDTH - 170 < pos[0] < SCREEN_WIDTH - 50:
        scene._try_open_recruitment()


def handle_right_click(scene, pos):
    if scene.paused:
        return
    if scene.general_manager.player_capture.is_captured:
        scene._add_notification("Cannot move while captured!")
        return
    wx, wy = scene.camera.screen_to_world(*pos)
    scene._pending_map_interaction = None
    scene.player_army.give_move_order(wx, wy)


# ---------------------------------------------------------------------------
# Overlay event handlers
# ---------------------------------------------------------------------------

def handle_diplomacy_event(scene, event):
    if event.type == pygame.MOUSEWHEEL:
        scene._diplomacy_scroll -= event.y * 30
        scene._diplomacy_scroll = max(0, scene._diplomacy_scroll)
        return None
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            scene.show_diplomacy = False
            scene._diplomacy_scroll = 0
            return None
        if event.key == pygame.K_UP:
            scene._diplomacy_scroll = max(0, scene._diplomacy_scroll - 30)
            return None
        if event.key == pygame.K_DOWN:
            scene._diplomacy_scroll += 30
            return None
        if pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            non_player = [f for f in scene.factions if not f.is_player]
            if idx < len(non_player):
                target = non_player[idx]
                state = scene.diplomacy.get_state(0, target.team)
                rel = scene.diplomacy.get_relation(0, target.team)
                if state == DiplomacyState.WAR:
                    if scene.diplomacy.propose_peace(0, target.team):
                        scene._add_notification(f"Peace with {target.name}!")
                        scene._update_trade_connectivity_warning()
                    else:
                        scene._add_notification(f"{target.name} rejected peace.")
                elif state in (DiplomacyState.FRIENDLY,):
                    if scene.player_faction is None and rel >= FACTION_JOIN_THRESHOLD:
                        scene._join_faction(target)
                    elif scene.diplomacy.propose_alliance(0, target.team):
                        scene._add_notification(f"Allied with {target.name}!")
                        scene._update_trade_connectivity_warning()
                    else:
                        scene._add_notification(f"{target.name} declined alliance.")
                elif state in (DiplomacyState.NEUTRAL, DiplomacyState.HOSTILE):
                    scene.diplomacy.declare_war(0, target.team)
                    scene._add_notification(f"War declared on {target.name}!")
                    scene._update_trade_connectivity_warning()
        if event.key == pygame.K_l and scene.player_faction is not None:
            scene._leave_faction()
    return None


def handle_persuasion_event(scene, event):
    """Handle input on the persuasion dialog."""
    if event.type != pygame.KEYDOWN:
        return None
    if event.key == pygame.K_ESCAPE:
        scene.show_persuasion = False
        scene.persuasion_target = None
        scene.paused = False
        return None

    target = scene.persuasion_target
    if target is None:
        scene.show_persuasion = False
        return None

    name = target.general_name
    gm = scene.general_manager

    if event.key == pygame.K_1:
        success, msg = gm.attempt_bribe(name, scene.player_army, scene.diplomacy)
        scene._add_notification(msg)
    elif event.key == pygame.K_2:
        success, msg = gm.attempt_convince(name, scene.player_army, scene.diplomacy)
        scene._add_notification(msg)
    elif event.key == pygame.K_3:
        success, msg = gm.attempt_threaten(name, scene.player_army, scene.diplomacy)
        scene._add_notification(msg)
    else:
        return None

    scene.show_persuasion = False
    scene.persuasion_target = None
    scene.paused = False
    return None


def handle_prisoner_event(scene, event):
    """Handle input on the prisoner management panel."""
    if event.type != pygame.KEYDOWN:
        return None
    if event.key == pygame.K_ESCAPE or event.key == pygame.K_j:
        scene.show_prisoners = False
        scene.paused = False
        scene.prisoner_action_msg = None
        return None

    gm = scene.general_manager
    prisoners = gm.player_prisoners

    if not prisoners:
        scene.show_prisoners = False
        scene.paused = False
        return None

    if pygame.K_1 <= event.key <= pygame.K_9:
        idx = event.key - pygame.K_1
        if idx < len(prisoners):
            scene._prisoner_selected = idx
            scene.prisoner_action_msg = f"Selected {prisoners[idx].general_name}. [R]ansom / [C]recruit / [X]execute"
            scene.prisoner_action_timer = 300
        return None

    selected = getattr(scene, '_prisoner_selected', None)
    if selected is not None and selected < len(prisoners):
        if event.key == pygame.K_r:
            gold, msg = gm.ransom_prisoner(selected, scene.diplomacy)
            if gold > 0:
                scene.player_army.gold += gold
            scene._add_notification(msg)
            scene.prisoner_action_msg = msg
            scene.prisoner_action_timer = 180
            scene._prisoner_selected = None
        elif event.key == pygame.K_c:
            success, msg, prisoner_data = gm.recruit_prisoner(selected, scene.diplomacy)
            scene._add_notification(msg)
            scene.prisoner_action_msg = msg
            scene.prisoner_action_timer = 180
            scene._prisoner_selected = None
        elif event.key == pygame.K_x:
            msg = gm.execute_prisoner(selected, scene.diplomacy, scene.factions)
            scene._add_notification(msg)
            scene.prisoner_action_msg = msg
            scene.prisoner_action_timer = 180
            scene._prisoner_selected = None

    if not gm.player_prisoners:
        scene.show_prisoners = False
        scene.paused = False

    return None


def handle_companion_event(scene, event):
    """Handle input on the companion management panel."""
    if event.type != pygame.KEYDOWN:
        return True
    if event.key == pygame.K_ESCAPE or event.key == pygame.K_n:
        scene.show_companions = False
        scene._companion_selected = None
        return True

    companions = scene.companion_manager.companions

    if pygame.K_1 <= event.key <= pygame.K_5:
        idx = event.key - pygame.K_1
        if idx < len(companions):
            scene._companion_selected = idx
        return True

    selected = getattr(scene, '_companion_selected', None)
    if selected is not None and selected < len(companions):
        if event.key == pygame.K_d:
            comp = companions[selected]
            scene.companion_manager.remove(comp.name)
            scene._add_notification(f"{comp.name} has been dismissed.")
            scene._companion_selected = None
            if not scene.companion_manager.companions:
                scene.show_companions = False
            return True

    return True


def handle_tavern_event(scene, event):
    """Handle input on the tavern companion recruitment panel."""
    if event.type != pygame.KEYDOWN:
        return True
    if event.key == pygame.K_ESCAPE or event.key == pygame.K_t:
        scene.show_tavern = False
        return True

    tavern = scene._tavern_companions
    if not tavern:
        return True

    if pygame.K_1 <= event.key <= pygame.K_3:
        idx = event.key - pygame.K_1
        if idx < len(tavern):
            max_comp = scene.player_character.max_companions if scene.player_character else 0
            current = len(scene.companion_manager.companions)
            if current >= max_comp:
                scene._add_notification(f"No companion slots available ({current}/{max_comp}). Dismiss one first.")
                return True

            comp = tavern[idx]
            cost = comp.level * 50
            if scene.player_army.gold < cost:
                scene._add_notification(f"Not enough gold to recruit {comp.name} ({cost}g needed).")
                return True

            scene.player_army.gold -= cost
            scene.companion_manager.add(comp)
            scene._tavern_companions.pop(idx)
            scene._add_notification(f"{comp.name} has joined your party! (-{cost}g)")
            if not scene._tavern_companions:
                scene.show_tavern = False
            return True

    return True


def handle_capture_event(scene, event):
    """Handle input while player is captured."""
    if event.type != pygame.KEYDOWN:
        return None
    if event.key == pygame.K_r:
        success, msg = scene.general_manager.pay_player_ransom(scene.player_army)
        scene._add_notification(msg)
    return None


def handle_army_panel_event(scene, event):
    """C4: Handle army management panel input."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_a:
            scene.show_army_panel = False
            return None
        if pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            if idx < len(scene.player_army.squads):
                pending = getattr(scene, '_disband_pending', None)
                if pending == idx:
                    if len(scene.player_army.squads) > 1:
                        sq = scene.player_army.squads[idx]
                        scene.player_army.remove_squad(idx)
                        scene._add_notification(f"Disbanded {sq.unit_stats.name}.")
                    else:
                        scene._add_notification("Cannot disband your last squad!")
                    scene._disband_pending = None
                else:
                    sq = scene.player_army.squads[idx]
                    scene._add_notification(f"Press {idx+1} again to confirm disband {sq.unit_stats.name}")
                    scene._disband_pending = idx
        if event.key == pygame.K_UP:
            scene._army_panel_selected = max(0,
                getattr(scene, '_army_panel_selected', 0) - 1)
        elif event.key == pygame.K_DOWN:
            scene._army_panel_selected = min(
                len(scene.player_army.squads) - 1,
                getattr(scene, '_army_panel_selected', 0) + 1)
    return None
