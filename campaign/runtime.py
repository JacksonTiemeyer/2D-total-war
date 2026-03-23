"""Campaign runtime helpers extracted from CampaignScene."""

from core.contracts import PendingBattle
from core.settings import (
    CAMPAIGN_MOVE_SPEED,
    CAMPAIGN_SETTLEMENT_VISION,
    CAMPAIGN_TICKS_PER_DAY,
    CAMPAIGN_VISION_RADIUS,
    SEASON_SUMMER,
    SEASON_SUMMER_DESERT_SPEED_BONUS,
    SEASON_WINTER,
    SEASON_WINTER_MOVE_PENALTY,
)
from core.utils import distance


def queue_pending_battle(scene, enemy_army, terrain_type):
    """Store a typed pending battle handoff on the campaign scene."""
    scene.pending_battle = PendingBattle(
        player_army=scene.player_army,
        enemy_army=enemy_army,
        terrain_type=terrain_type,
    )


def consume_pending_battle(scene):
    """Consume the current pending battle, if any."""
    battle = scene.pending_battle
    scene.pending_battle = None
    return battle


def is_visible(scene, x, y):
    """Check if a world position is visible to the player."""
    if distance(scene.player_army.x, scene.player_army.y, x, y) <= CAMPAIGN_VISION_RADIUS:
        return True
    for settlement in scene.settlements:
        if settlement.owner == 0 or (
            settlement.owner is not None and scene.diplomacy.are_allied(0, settlement.owner)
        ):
            if distance(settlement.x, settlement.y, x, y) <= CAMPAIGN_SETTLEMENT_VISION:
                return True
    return False


def update_campaign(scene):
    """Advance campaign simulation without owning scene rendering/input."""
    scene.camera.update()

    season = scene._get_current_season()
    base_speed = CAMPAIGN_MOVE_SPEED
    effective_speed = base_speed * SEASON_WINTER_MOVE_PENALTY if season == SEASON_WINTER else base_speed

    for army in scene.armies:
        army.speed = effective_speed
        if season == SEASON_SUMMER and army.team == 3:
            army.speed = base_speed * SEASON_SUMMER_DESERT_SPEED_BONUS
        army.update_campaign_context(
            scene.settlements,
            scene._get_terrain_at_position(army.x, army.y),
        )

    if not scene.paused:
        scene.player_army.update()
        scene._update_pending_map_interaction()
        scene.player_army.update_campaign_context(
            scene.settlements,
            scene._get_terrain_at_position(scene.player_army.x, scene.player_army.y),
        )
        scene.player_army.current_status = "Marching" if scene.player_army.moving else "Idle"
    elif scene.settlement_interaction:
        scene.player_army.current_status = f"In {scene.settlement_interaction.settlement.name}"
    else:
        scene.player_army.current_status = "Paused"

    if hasattr(scene, "_save_notification_timer") and scene._save_notification_timer > 0:
        scene._save_notification_timer -= 1

    scene.notifications = [(text, timer - 1) for text, timer in scene.notifications if timer > 1]

    if getattr(scene, "prisoner_action_timer", 0) > 0:
        scene.prisoner_action_timer -= 1
        if scene.prisoner_action_timer <= 0:
            scene.prisoner_action_msg = None

    if not scene.paused:
        for _ in range(scene.campaign_speed):
            scene.day_ticks += 1
            if scene.day_ticks % 10 == 0:
                scene._process_ai_movement()
            if scene.day_ticks >= CAMPAIGN_TICKS_PER_DAY:
                scene.day_ticks = 0
                scene._process_day()

    if not scene.paused and scene.player_army.moving:
        scene._fog_needs_update = True

    for army in scene.armies:
        if army.is_player or army.team == 0:
            continue
        if not scene._are_hostile(0, army.team):
            continue
        if not is_visible(scene, army.x, army.y):
            continue
        if distance(scene.player_army.x, scene.player_army.y, army.x, army.y) < 25:
            battle_x = (scene.player_army.x + army.x) / 2
            battle_y = (scene.player_army.y + army.y) / 2
            terrain_type = scene._get_terrain_at_position(battle_x, battle_y)
            queue_pending_battle(scene, army, terrain_type)
            scene.paused = True
            return
