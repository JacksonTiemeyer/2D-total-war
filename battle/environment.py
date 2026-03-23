"""Battle terrain, weather, and visibility helpers."""

import random

from core.settings import (
    BATTLE_MAP_HEIGHT,
    BATTLE_MAP_WIDTH,
    FOREST_CAVALRY_SPEED_MULT,
    FOREST_MELEE_DEFENSE_BONUS,
    FOREST_RANGED_ACCURACY_MULT,
    HILL_RANGED_BONUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEASON_AUTUMN,
    SEASON_AUTUMN_MUD_CHANCE,
    SEASON_WINTER,
    SEASON_WINTER_HARSH_WEATHER_CHANCE,
    SEASON_WINTER_RANGED_PENALTY,
    VISION_CAVALRY,
    WEATHER_FOG_VISION,
    WEATHER_MUD_CHARGE,
    WEATHER_MUD_SPEED,
    WEATHER_RAIN_ACCURACY,
    WEATHER_RAIN_EXHAUSTION,
    WEATHER_TYPES,
    WEATHER_WIND_ACCURACY,
)
from core.utils import distance


def choose_weather(scene):
    if scene.season == SEASON_AUTUMN and random.random() < SEASON_AUTUMN_MUD_CHANCE:
        return "mud"
    if scene.season == SEASON_WINTER and random.random() < SEASON_WINTER_HARSH_WEATHER_CHANCE:
        return random.choice(["fog", "rain"])
    if scene.terrain_type == "desert":
        return random.choice(["clear", "clear", "clear", "wind"])
    if scene.terrain_type == "coastal":
        return random.choice(["clear", "wind", "rain"])
    return random.choice(WEATHER_TYPES)


def generate_terrain(scene):
    terrain = []
    terrain_type = scene.terrain_type
    width = BATTLE_MAP_WIDTH
    height = BATTLE_MAP_HEIGHT

    if terrain_type == "forest":
        for _ in range(random.randint(5, 7)):
            x = random.randint(200, width - 500)
            y = random.randint(200, height - 400)
            w = random.randint(200, 400)
            h = random.randint(200, 400)
            terrain.append({"type": "forest", "rect": (x, y, w, h), "color": (30, 90, 20)})
        hx = random.randint(400, width - 600)
        hy = random.randint(400, height - 400)
        terrain.append({"type": "hill", "rect": (hx, hy, 350, 200), "color": (80, 140, 60)})
    elif terrain_type == "mountain":
        for _ in range(random.randint(3, 4)):
            x = random.randint(100, width - 600)
            y = random.randint(100, height - 400)
            w = random.randint(400, 600)
            h = random.randint(250, 400)
            terrain.append({"type": "hill", "rect": (x, y, w, h), "color": (120, 110, 80)})
        terrain.append({"type": "forest", "rect": (width // 2 - 150, height // 2 - 100, 300, 200), "color": (40, 80, 30)})
    elif terrain_type == "desert":
        for _ in range(random.randint(2, 4)):
            x = random.randint(200, width - 500)
            y = random.randint(200, height - 400)
            w = random.randint(250, 450)
            h = random.randint(150, 300)
            terrain.append({"type": "hill", "rect": (x, y, w, h), "color": (190, 170, 120)})
    elif terrain_type == "coastal":
        water_x = width * 2 // 3
        terrain.append({"type": "water", "rect": (water_x, 0, width - water_x, height), "color": (40, 80, 150)})
        terrain.append({"type": "hill", "rect": (300, 600, 350, 200), "color": (80, 140, 60)})
        terrain.append({"type": "forest", "rect": (100, 1200, 250, 250), "color": (30, 90, 20)})
    else:
        terrain.extend(
            [
                {"type": "hill", "rect": (800, 600, 400, 200), "color": (80, 140, 60)},
                {"type": "forest", "rect": (1800, 400, 300, 350), "color": (30, 90, 20)},
                {"type": "hill", "rect": (1200, 1200, 350, 180), "color": (80, 140, 60)},
                {"type": "forest", "rect": (500, 1100, 250, 300), "color": (30, 90, 20)},
            ]
        )
    scene.terrain = terrain


def get_terrain_at(scene, x, y):
    for terrain in scene.terrain:
        rx, ry, rw, rh = terrain["rect"]
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return terrain["type"]
    return None


def is_water_at(scene, x, y):
    return get_terrain_at(scene, x, y) == "water"


def get_weather_modifiers(scene):
    mods = {
        "ranged_accuracy": 1.0,
        "exhaustion_rate": 1.0,
        "speed": 1.0,
        "charge": 1.0,
        "vision": 1.0,
    }
    if scene.weather == "rain":
        mods["ranged_accuracy"] = WEATHER_RAIN_ACCURACY
        mods["exhaustion_rate"] = WEATHER_RAIN_EXHAUSTION
    elif scene.weather == "fog":
        mods["vision"] = WEATHER_FOG_VISION
    elif scene.weather == "mud":
        mods["speed"] = WEATHER_MUD_SPEED
        mods["charge"] = WEATHER_MUD_CHARGE
    elif scene.weather == "wind":
        mods["ranged_accuracy"] = 1.0 + scene.wind_direction * WEATHER_WIND_ACCURACY
    return mods


def get_terrain_modifiers(scene, squad):
    cx, cy = squad.center
    terrain_type = get_terrain_at(scene, cx, cy)
    mods = {
        "speed_mult": 1.0,
        "ranged_accuracy_mult": 1.0,
        "ranged_damage_mult": 1.0,
        "melee_defense_mult": 1.0,
        "charge_mult": 1.0,
        "terrain_type": terrain_type,
    }
    if terrain_type == "hill":
        mods["ranged_damage_mult"] = HILL_RANGED_BONUS
        mods["melee_defense_mult"] = 1.1
    elif terrain_type == "forest":
        if squad.is_cavalry:
            mods["speed_mult"] = FOREST_CAVALRY_SPEED_MULT
        mods["ranged_accuracy_mult"] = FOREST_RANGED_ACCURACY_MULT
        mods["melee_defense_mult"] = FOREST_MELEE_DEFENSE_BONUS
    elif terrain_type == "water":
        mods["speed_mult"] = 0.1

    if scene.season == SEASON_WINTER:
        mods["ranged_accuracy_mult"] *= SEASON_WINTER_RANGED_PENALTY

    weather_mods = get_weather_modifiers(scene)
    mods["ranged_accuracy_mult"] *= weather_mods["ranged_accuracy"]
    mods["speed_mult"] *= weather_mods["speed"]
    mods["charge_mult"] *= weather_mods["charge"]
    return mods


def init_weather_particles(scene):
    if scene.weather == "rain":
        for _ in range(150):
            scene.weather_particles.append([random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(3, 7)])
    elif scene.weather == "fog":
        for _ in range(30):
            scene.weather_particles.append([random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.randint(60, 150)])
    elif scene.weather == "wind":
        for _ in range(80):
            scene.weather_particles.append([random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(2, 5)])


def is_los_blocked(scene, x1, y1, x2, y2):
    for terrain in scene.terrain:
        if terrain["type"] != "forest":
            continue
        rx, ry, rw, rh = terrain["rect"]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if rx <= mx <= rx + rw and ry <= my <= ry + rh:
            p1_in = rx <= x1 <= rx + rw and ry <= y1 <= ry + rh
            p2_in = rx <= x2 <= rx + rw and ry <= y2 <= ry + rh
            if not (p1_in and p2_in):
                return True
    return False


def compute_visibility(scene):
    if not scene.fog_enabled:
        for squad in scene.enemy_squads:
            squad.visible = True
        for general in scene.enemy_generals:
            general.visible = True
        return

    scout_active = any(general._scout_active for general in scene.player_generals if general.alive)
    if scout_active:
        for squad in scene.enemy_squads:
            squad.visible = True
        for general in scene.enemy_generals:
            general.visible = True
        return

    weather_vis = get_weather_modifiers(scene)["vision"]
    vision_sources = []
    for squad in scene.player_squads:
        if not squad.is_destroyed:
            cx, cy = squad.center
            vision_sources.append((cx, cy, squad.vision_radius * weather_vis))
    for general in scene.player_generals:
        if general.alive:
            vision_sources.append((general.x, general.y, VISION_CAVALRY * weather_vis))

    for squad in scene.enemy_squads:
        if squad.is_destroyed:
            squad.visible = False
            continue
        cx, cy = squad.center
        squad.visible = any(
            distance(vx, vy, cx, cy) <= vr and not is_los_blocked(scene, vx, vy, cx, cy)
            for vx, vy, vr in vision_sources
        )

    for general in scene.enemy_generals:
        if not general.alive:
            general.visible = False
            continue
        general.visible = any(
            distance(vx, vy, general.x, general.y) <= vr and not is_los_blocked(scene, vx, vy, general.x, general.y)
            for vx, vy, vr in vision_sources
        )
