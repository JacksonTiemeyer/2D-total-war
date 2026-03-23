"""Battle runtime orchestration helpers extracted from BattleScene."""

from battle.ai_engine import AIEngine
from battle.engine import CombatEngine
from battle.general import General
from battle.squad import SquadState
from core.audio import get_audio
from core.settings import BATTLE_MAP_HEIGHT, SEASON_SUMMER, SEASON_SUMMER_EXHAUSTION_MULT


def initialize_runtime(scene):
    scene.weather = scene._choose_weather()
    scene.weather_particles = []
    scene._init_weather_particles()
    scene.season_exhaustion_mult = (
        SEASON_SUMMER_EXHAUSTION_MULT if scene.season == SEASON_SUMMER else 1.0
    )
    scene.terrain = []
    scene._generate_terrain()
    scene._combat_engine = CombatEngine(
        player_squads=scene.player_squads,
        enemy_squads=scene.enemy_squads,
        player_generals=scene.player_generals,
        enemy_generals=scene.enemy_generals,
        terrain=scene.terrain,
        weather=scene.weather,
        ai_engine=AIEngine(army=scene.enemy_squads, personality=None),
    )


def deploy_companions(scene, companions):
    base_y = BATTLE_MAP_HEIGHT // 2
    for i, companion in enumerate(companions):
        offset_y = (i + 1) * 100 - (len(companions) * 50)
        general = General(
            companion["name"],
            companion["stats"],
            0,
            200,
            base_y + offset_y,
            player_class=companion.get("player_class"),
        )
        if "level" in companion:
            general.level = companion["level"]
        general._companion_name = companion["name"]
        scene.player_generals.append(general)
        scene._companion_generals.append(general)
    scene.all_generals = scene.player_generals + scene.enemy_generals


def update_battle(scene):
    if scene.paused or scene.deployment_phase:
        scene.camera.update()
        return

    for _ in range(scene.speed_multiplier):
        tick_battle(scene)

    scene.camera.update()
    scene.battle_timer += 1


def tick_battle(scene):
    scene._compute_visibility()
    prev_states = {id(squad): squad.state for squad in scene.all_squads}
    prev_routed = {id(squad) for squad in scene.all_squads if squad.state == SquadState.ROUTED}

    for squad in scene.all_squads:
        mods = scene.get_terrain_modifiers(squad)
        mods["exhaustion_mult"] = scene.season_exhaustion_mult
        squad.terrain_mods = mods

    scene._combat_engine.step()

    if scene.terrain_type == "coastal":
        for squad in scene.all_squads:
            for soldier in squad.soldiers:
                if soldier.alive and scene.is_water_at(soldier.x, soldier.y):
                    for terrain in scene.terrain:
                        if terrain["type"] == "water":
                            rx, ry, rw, rh = terrain["rect"]
                            if rx <= soldier.x <= rx + rw and ry <= soldier.y <= ry + rh:
                                soldier.x = rx - 5

    scene._resolve_collisions()

    audio = get_audio()
    for squad in scene.all_squads:
        old_state = prev_states.get(id(squad))
        if old_state == SquadState.CHARGING and squad.state == SquadState.FIGHTING:
            audio.play("charge")
        if squad.state == SquadState.ROUTED and id(squad) not in prev_routed:
            audio.play("rout")
        if squad.state == SquadState.FIRING and scene.battle_timer % 60 == 0:
            audio.play("arrow_volley")

    dead_generals = [general for general in scene.all_generals if not general.alive]
    for general in dead_generals:
        if general.team == 0:
            general.on_death(scene.player_squads)
            if general in scene.player_generals:
                scene.player_generals.remove(general)
        else:
            general.on_death(scene.enemy_squads)
            if general in scene.enemy_generals:
                scene.enemy_generals.remove(general)
        scene.all_generals.remove(general)
        scene._dead_generals.append(general)

    scene.selected_squads = [squad for squad in scene.selected_squads if not squad.is_destroyed]

    prev_result = scene.result
    player_alive = any(not squad.is_destroyed for squad in scene.player_squads)
    enemy_alive = any(not squad.is_destroyed for squad in scene.enemy_squads)
    if not enemy_alive and player_alive:
        scene.result = "player_win"
    elif not player_alive:
        scene.result = "player_loss"

    if prev_result == "ongoing" and scene.result != "ongoing":
        audio.play("victory" if scene.result == "player_win" else "defeat")
