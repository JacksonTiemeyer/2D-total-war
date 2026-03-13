"""Battle scene - handles the real-time tactical combat."""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT,
    TEAM_COLORS, TEAM_COLORS_LIGHT, GREEN, DARK_GREEN, SAND, BROWN,
    BLACK, WHITE, GREY, GOLD, YELLOW, ORANGE,
    EXHAUSTION_MAX, MELEE_RANGE,
    HILL_RANGED_BONUS, HILL_CHARGE_DOWNHILL_BONUS, HILL_SPEED_UPHILL_PENALTY,
    FOREST_CAVALRY_SPEED_MULT, FOREST_RANGED_ACCURACY_MULT, FOREST_MELEE_DEFENSE_BONUS,
    VISION_INFANTRY, VISION_CAVALRY, FOG_ALPHA,
    WEATHER_TYPES, WEATHER_RAIN_ACCURACY, WEATHER_RAIN_EXHAUSTION,
    WEATHER_FOG_VISION, WEATHER_MUD_SPEED, WEATHER_MUD_CHARGE,
    WEATHER_WIND_ACCURACY,
    SOLDIER_RADIUS, SOLDIER_SPACING, COLLISION_GRID_CELL_SIZE, COLLISION_PUSH_STRENGTH,
    COLLISION_FRIENDLY_PUSH, COLLISION_ENGAGE_RADIUS,
    COLLISION_RADIUS, ENGAGEMENT_LOCK_DISTANCE, ENGAGEMENT_BREAK_DISTANCE,
    CAVALRY_PUNCHTHROUGH_MASS_RATIO, CAVALRY_PUNCHTHROUGH_PUSH,
    CAVALRY_PUNCHTHROUGH_MIN_DEPTH,
    MOVE_MODE_WALK, MOVE_MODE_MARCH, MOVE_MODE_RUN,
)
from core.camera import Camera
from core.utils import distance, point_in_rect, angle_between
from battle.squad import Squad, SquadState, Formation
from battle.general import General, DuelState
from core.audio import get_audio


class BattleResult:
    ONGOING = "ongoing"
    PLAYER_WIN = "player_win"
    PLAYER_LOSS = "player_loss"


class BattleScene:
    def __init__(self, player_army, enemy_army):
        self.camera = Camera(BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT)
        self.camera.center_on(BATTLE_MAP_WIDTH / 2, BATTLE_MAP_HEIGHT / 2)

        self.player_squads = []
        self.enemy_squads = []
        self.player_generals = []
        self.enemy_generals = []
        self.all_squads = []
        self.all_generals = []
        self._dead_generals = []

        self.result = BattleResult.ONGOING
        self.selected_squads = []
        self.selected_general = None
        self.selecting = False
        self.select_start = (0, 0)
        self.select_end = (0, 0)
        self.paused = False
        self.battle_timer = 0
        self.speed_multiplier = 1
        self.fog_enabled = True  # fog of war toggle

        # Right-click drag state for facing control
        self._right_dragging = False
        self._right_click_pos = None      # screen position of initial right click
        self._right_click_world = None    # world position of initial right click
        self._right_drag_pos = None       # current screen position during drag

        # Deployment phase
        self.deployment_phase = True
        self.deploy_zone = (50, 50, 500, BATTLE_MAP_HEIGHT - 100)  # left side zone
        self._deploy_dragging = None  # squad being dragged during deployment

        # Hover tracking for targeting indicator (A8)
        self._hovered_squad = None
        self._mouse_world_pos = (0, 0)

        # UI button state
        self._ui_buttons = {}
        self._unit_card_rects = []

        # Weather
        self.weather = random.choice(WEATHER_TYPES)
        self.wind_direction = random.uniform(-1, 1)  # -1 = left, +1 = right
        self.weather_particles = []
        self._init_weather_particles()

        # Terrain features
        self.terrain = []
        self._generate_terrain()

        # Deploy armies
        self._deploy_armies(player_army, enemy_army)

        # Wire up generals' enemy general references (for Challenge ability)
        for g in self.player_generals:
            g._all_enemy_generals = self.enemy_generals
        for g in self.enemy_generals:
            g._all_enemy_generals = self.player_generals

    def _generate_terrain(self):
        self.terrain.append({"type": "hill", "rect": (800, 600, 400, 200), "color": (80, 140, 60)})
        self.terrain.append({"type": "forest", "rect": (1800, 400, 300, 350), "color": (30, 90, 20)})
        self.terrain.append({"type": "hill", "rect": (1200, 1200, 350, 180), "color": (80, 140, 60)})
        self.terrain.append({"type": "forest", "rect": (500, 1100, 250, 300), "color": (30, 90, 20)})

    def get_terrain_at(self, x, y):
        """Return terrain type at given world position, or None."""
        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return t["type"]
        return None

    def get_terrain_modifiers(self, squad):
        """Compute terrain modifiers for a squad based on its position."""
        cx, cy = squad.center
        terrain_type = self.get_terrain_at(cx, cy)
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
            mods["charge_mult"] = HILL_CHARGE_DOWNHILL_BONUS
            mods["speed_mult"] = HILL_SPEED_UPHILL_PENALTY  # penalty for enemies moving onto hill
        elif terrain_type == "forest":
            if squad.is_cavalry:
                mods["speed_mult"] = FOREST_CAVALRY_SPEED_MULT
            mods["ranged_accuracy_mult"] = FOREST_RANGED_ACCURACY_MULT
            mods["melee_defense_mult"] = FOREST_MELEE_DEFENSE_BONUS

        # Apply weather modifiers
        wmods = self.get_weather_modifiers()
        mods["ranged_accuracy_mult"] *= wmods["ranged_accuracy"]
        mods["speed_mult"] *= wmods["speed"]
        mods["charge_mult"] *= wmods["charge"]
        return mods

    def _init_weather_particles(self):
        """Create initial particle pool for weather visuals."""
        if self.weather == "rain":
            for _ in range(150):
                self.weather_particles.append([
                    random.randint(0, SCREEN_WIDTH),
                    random.randint(0, SCREEN_HEIGHT),
                    random.uniform(3, 7),  # speed
                ])
        elif self.weather == "fog":
            for _ in range(30):
                self.weather_particles.append([
                    random.randint(0, SCREEN_WIDTH),
                    random.randint(0, SCREEN_HEIGHT),
                    random.randint(60, 150),  # radius
                ])
        elif self.weather == "wind":
            for _ in range(80):
                self.weather_particles.append([
                    random.randint(0, SCREEN_WIDTH),
                    random.randint(0, SCREEN_HEIGHT),
                    random.uniform(2, 5),  # speed
                ])

    def get_weather_modifiers(self):
        """Return global combat modifiers based on weather."""
        mods = {
            "ranged_accuracy": 1.0,
            "exhaustion_rate": 1.0,
            "speed": 1.0,
            "charge": 1.0,
            "vision": 1.0,
        }
        if self.weather == "rain":
            mods["ranged_accuracy"] = WEATHER_RAIN_ACCURACY
            mods["exhaustion_rate"] = WEATHER_RAIN_EXHAUSTION
        elif self.weather == "fog":
            mods["vision"] = WEATHER_FOG_VISION
        elif self.weather == "mud":
            mods["speed"] = WEATHER_MUD_SPEED
            mods["charge"] = WEATHER_MUD_CHARGE
        elif self.weather == "wind":
            mods["ranged_accuracy"] = 1.0 + self.wind_direction * WEATHER_WIND_ACCURACY
        return mods

    def _is_los_blocked(self, x1, y1, x2, y2):
        """Check if line of sight is blocked by a forest."""
        for t in self.terrain:
            if t["type"] != "forest":
                continue
            rx, ry, rw, rh = t["rect"]
            # Simple: check if the midpoint of the LOS line falls inside a forest
            # and neither endpoint is in that same forest
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                # Midpoint is in forest — blocked unless both endpoints are too
                p1_in = rx <= x1 <= rx + rw and ry <= y1 <= ry + rh
                p2_in = rx <= x2 <= rx + rw and ry <= y2 <= ry + rh
                if not (p1_in and p2_in):
                    return True
        return False

    def _compute_visibility(self):
        """Compute which enemy squads are visible to the player."""
        if not self.fog_enabled:
            for sq in self.enemy_squads:
                sq.visible = True
            for g in self.enemy_generals:
                g.visible = True
            return

        # Check if any player general has Scout Report active
        scout_active = any(g._scout_active for g in self.player_generals if g.alive)
        if scout_active:
            for sq in self.enemy_squads:
                sq.visible = True
            for g in self.enemy_generals:
                g.visible = True
            return

        # Build list of (x, y, vision_radius) for all player units
        weather_vis = self.get_weather_modifiers()["vision"]
        vision_sources = []
        for sq in self.player_squads:
            if not sq.is_destroyed:
                cx, cy = sq.center
                vision_sources.append((cx, cy, sq.vision_radius * weather_vis))
        for g in self.player_generals:
            if g.alive:
                base_v = VISION_CAVALRY * weather_vis
                vision_sources.append((g.x, g.y, base_v))

        # Check each enemy squad
        for sq in self.enemy_squads:
            if sq.is_destroyed:
                sq.visible = False
                continue
            cx, cy = sq.center
            sq.visible = False
            for vx, vy, vr in vision_sources:
                d = distance(vx, vy, cx, cy)
                if d <= vr and not self._is_los_blocked(vx, vy, cx, cy):
                    sq.visible = True
                    break

        # Check each enemy general
        for g in self.enemy_generals:
            if not g.alive:
                g.visible = False
                continue
            g.visible = False
            for vx, vy, vr in vision_sources:
                d = distance(vx, vy, g.x, g.y)
                if d <= vr and not self._is_los_blocked(vx, vy, g.x, g.y):
                    g.visible = True
                    break

    def _resolve_collisions(self):
        """Resolve soldier-soldier collisions using spatial grid.

        Includes engagement lock (soldiers in melee contact cannot freely
        disengage) and cavalry punch-through on charge.
        """
        cell_size = COLLISION_GRID_CELL_SIZE
        grid = {}

        # Build spatial grid of all living soldiers
        all_soldiers = []
        for sq in self.all_squads:
            if sq.is_destroyed or sq.state == SquadState.ROUTED:
                continue
            for s in sq.alive_soldiers:
                cx = int(s.x // cell_size)
                cy = int(s.y // cell_size)
                key = (cx, cy)
                if key not in grid:
                    grid[key] = []
                grid[key].append((s, sq))
                all_soldiers.append((s, sq))

        push_radius = COLLISION_RADIUS
        engage_dist = ENGAGEMENT_LOCK_DISTANCE
        break_dist = ENGAGEMENT_BREAK_DISTANCE

        # Clear dead engagements
        for (s, sq) in all_soldiers:
            if s.engaged_with is not None and (
                not s.engaged_with.alive
                or sq.state == SquadState.ROUTED
            ):
                s.engaged_with = None

        # Check collisions in neighboring cells
        for (s1, sq1) in all_soldiers:
            cx = int(s1.x // cell_size)
            cy = int(s1.y // cell_size)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    key = (cx + dx, cy + dy)
                    if key not in grid:
                        continue
                    for (s2, sq2) in grid[key]:
                        if s1 is s2:
                            continue
                        ddx = s1.x - s2.x
                        ddy = s1.y - s2.y
                        dist_sq = ddx * ddx + ddy * ddy
                        same_team = sq1.team == sq2.team

                        # Engagement lock for enemies within engage distance
                        if not same_team and dist_sq < engage_dist * engage_dist and dist_sq > 0.01:
                            if s1.engaged_with is None:
                                s1.engaged_with = s2
                            if s2.engaged_with is None:
                                s2.engaged_with = s1

                        if dist_sq >= push_radius * push_radius or dist_sq < 0.01:
                            continue
                        dist_val = dist_sq ** 0.5
                        overlap = push_radius - dist_val
                        nx = ddx / dist_val
                        ny = ddy / dist_val

                        if same_team:
                            # Soft push for friendlies
                            push = overlap * COLLISION_FRIENDLY_PUSH * 0.5
                            s1.x += nx * push
                            s1.y += ny * push
                            s2.x -= nx * push
                            s2.y -= ny * push
                        else:
                            # Hard push for enemies, mass-weighted
                            mass1 = sq1.unit_stats.mass
                            mass2 = sq2.unit_stats.mass
                            total_mass = mass1 + mass2
                            # Lighter unit gets pushed more
                            push1 = overlap * COLLISION_PUSH_STRENGTH * (mass2 / total_mass)
                            push2 = overlap * COLLISION_PUSH_STRENGTH * (mass1 / total_mass)

                            # Cavalry punch-through: charging cavalry pushes harder
                            # against thin formations
                            if (sq1.is_cavalry and sq1.state == SquadState.CHARGING
                                    and mass1 / mass2 >= CAVALRY_PUNCHTHROUGH_MASS_RATIO):
                                target_depth = self._estimate_formation_depth(sq2)
                                if target_depth < CAVALRY_PUNCHTHROUGH_MIN_DEPTH:
                                    push2 *= CAVALRY_PUNCHTHROUGH_PUSH
                            elif (sq2.is_cavalry and sq2.state == SquadState.CHARGING
                                    and mass2 / mass1 >= CAVALRY_PUNCHTHROUGH_MASS_RATIO):
                                target_depth = self._estimate_formation_depth(sq1)
                                if target_depth < CAVALRY_PUNCHTHROUGH_MIN_DEPTH:
                                    push1 *= CAVALRY_PUNCHTHROUGH_PUSH

                            s1.x += nx * push1
                            s1.y += ny * push1
                            s2.x -= nx * push2
                            s2.y -= ny * push2

        # Engagement lock: pull engaged soldiers back toward their opponent
        for (s, sq) in all_soldiers:
            if s.engaged_with is not None and s.engaged_with.alive:
                ddx = s.x - s.engaged_with.x
                ddy = s.y - s.engaged_with.y
                d2 = ddx * ddx + ddy * ddy
                if d2 > break_dist * break_dist:
                    # Too far: disengage
                    s.engaged_with = None
                elif d2 > engage_dist * engage_dist and sq.state != SquadState.ROUTED:
                    # Trying to move away but still within lock range: pull back
                    d = d2 ** 0.5
                    pull = (d - engage_dist) * 0.3
                    s.x -= (ddx / d) * pull
                    s.y -= (ddy / d) * pull

        # General-soldier collisions: generals push and get pushed by enemy soldiers
        # and also deal/take melee damage when in contact
        gen_push_radius = COLLISION_RADIUS * 1.5  # generals are bigger
        for g in self.all_generals:
            if not g.alive or g.duel_state == DuelState.ACTIVE:
                continue
            gcx = int(g.x // cell_size)
            gcy = int(g.y // cell_size)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    key = (gcx + dx, gcy + dy)
                    if key not in grid:
                        continue
                    for (s, sq) in grid[key]:
                        if sq.team == g.team:
                            continue  # only collide with enemy soldiers
                        ddx = g.x - s.x
                        ddy = g.y - s.y
                        dist_sq_val = ddx * ddx + ddy * ddy
                        if dist_sq_val >= gen_push_radius * gen_push_radius or dist_sq_val < 0.01:
                            continue
                        dist_val = dist_sq_val ** 0.5
                        overlap = gen_push_radius - dist_val
                        nx = ddx / dist_val
                        ny = ddy / dist_val
                        # General has high mass (2.0+), push soldier more
                        g_mass = g.unit_stats.mass
                        s_mass = sq.unit_stats.mass
                        total = g_mass + s_mass
                        push_g = overlap * COLLISION_PUSH_STRENGTH * (s_mass / total) * 0.5
                        push_s = overlap * COLLISION_PUSH_STRENGTH * (g_mass / total)
                        g.x += nx * push_g
                        g.y += ny * push_g
                        s.x -= nx * push_s
                        s.y -= ny * push_s
                        # General auto-attacks nearby enemy soldiers
                        if dist_val < MELEE_RANGE * 2 and g.attack_cooldown == 0:
                            dmg = max(1, g.unit_stats.weapon_strength *
                                      random.uniform(0.8, 1.2) - s.stats.armor * 0.3)
                            s.take_damage(dmg, g.unit_stats.armor_penetration)
                            g.attack_cooldown = 20
                            if not s.alive:
                                g.kills += 1
                                sq._dying_soldiers.append(s)
                                sq.on_casualty()

    def _estimate_formation_depth(self, squad):
        """Estimate how many rows deep a formation is (for punch-through check)."""
        alive = squad.alive_soldiers
        if len(alive) <= 1:
            return 1
        import math as _math
        # Use facing angle to determine front-back axis
        cos_f = _math.cos(squad.facing_angle)
        sin_f = _math.sin(squad.facing_angle)
        cx, cy = squad.center
        # Project each soldier onto the facing axis
        depths = []
        for s in alive:
            dx = s.x - cx
            dy = s.y - cy
            depth = dx * cos_f + dy * sin_f
            depths.append(depth)
        if not depths:
            return 1
        span = max(depths) - min(depths)
        # Estimate rows from span and spacing
        row_count = max(1, int(span / SOLDIER_SPACING + 0.5))
        return row_count

    def _deploy_armies(self, player_army, enemy_army):
        start_x = 300
        start_y = BATTLE_MAP_HEIGHT // 2 - 300
        spacing_y = 80

        for i, squad_entry in enumerate(player_army.get("squads", [])):
            unit_stats, soldier_count = squad_entry[0], squad_entry[1]
            vet_data = squad_entry[2] if len(squad_entry) > 2 else None
            y = start_y + i * spacing_y
            squad = Squad(unit_stats, 0, start_x, y, facing_angle=0,
                          soldier_count=soldier_count if soldier_count != 1 else None,
                          vet_data=vet_data)
            self.player_squads.append(squad)

        gen_data = player_army.get("general")
        if gen_data:
            gen = General(gen_data["name"], gen_data["stats"], 0,
                          start_x - 50, BATTLE_MAP_HEIGHT // 2)
            if "xp" in gen_data:
                gen.xp = gen_data["xp"]
                gen.level = gen_data["level"]
            self.player_generals.append(gen)

        start_x = BATTLE_MAP_WIDTH - 300
        start_y = BATTLE_MAP_HEIGHT // 2 - 300
        for i, squad_entry in enumerate(enemy_army.get("squads", [])):
            unit_stats, soldier_count = squad_entry[0], squad_entry[1]
            vet_data = squad_entry[2] if len(squad_entry) > 2 else None
            y = start_y + i * spacing_y
            squad = Squad(unit_stats, 1, start_x, y, facing_angle=math.pi,
                          soldier_count=soldier_count if soldier_count != 1 else None,
                          vet_data=vet_data)
            self.enemy_squads.append(squad)

        gen_data = enemy_army.get("general")
        if gen_data:
            gen = General(gen_data["name"], gen_data["stats"], 1,
                          start_x + 50, BATTLE_MAP_HEIGHT // 2)
            if "xp" in gen_data:
                gen.xp = gen_data["xp"]
                gen.level = gen_data["level"]
            self.enemy_generals.append(gen)

        self.all_squads = self.player_squads + self.enemy_squads
        self.all_generals = self.player_generals + self.enemy_generals

    def handle_event(self, event):
        self.camera.handle_event(event)

        # Deployment phase handling
        if self.deployment_phase:
            self._handle_deployment_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_f:
                for sq in self.selected_squads:
                    if sq.is_ranged:
                        sq.fire_at_will = not sq.fire_at_will
            elif event.key == pygame.K_v:
                self.fog_enabled = not self.fog_enabled
            # Number keys: Ctrl+1-5 = formations, plain 1-3 = speed
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
                if ctrl and self.selected_squads:
                    formations = [Formation.LINE, Formation.COLUMN, Formation.SQUARE,
                                  Formation.LOOSE, Formation.WEDGE]
                    idx = event.key - pygame.K_1
                    if idx < len(formations):
                        for sq in self.selected_squads:
                            sq.set_formation(formations[idx])
                elif not ctrl:
                    if event.key == pygame.K_1:
                        self.speed_multiplier = 1
                    elif event.key == pygame.K_2:
                        self.speed_multiplier = 2
                    elif event.key == pygame.K_3:
                        self.speed_multiplier = 4
            # Movement mode hotkeys
            elif event.key == pygame.K_z:
                for sq in self.selected_squads:
                    sq.movement_mode = MOVE_MODE_WALK
            elif event.key == pygame.K_x:
                for sq in self.selected_squads:
                    sq.movement_mode = MOVE_MODE_MARCH
            elif event.key == pygame.K_c:
                for sq in self.selected_squads:
                    sq.movement_mode = MOVE_MODE_RUN
            # Stance toggles
            elif event.key == pygame.K_d:
                for sq in self.selected_squads:
                    sq.defensive_stance = not sq.defensive_stance
                    if sq.defensive_stance:
                        sq.defensive_anchor_x = sq.x
                        sq.defensive_anchor_y = sq.y
            elif event.key == pygame.K_s:
                for sq in self.selected_squads:
                    if sq.is_ranged:
                        sq.skirmish_stance = not sq.skirmish_stance
            # Ability hotkeys: Q, W, E, R
            elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r):
                self._handle_ability_key(event.key)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                # Start tracking right-click drag for facing control
                self._right_click_pos = event.pos
                self._right_click_world = self.camera.screen_to_world(*event.pos)
                self._right_dragging = False
                self._right_drag_pos = event.pos

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.selecting:
                self._finish_box_select(event.pos)
            elif event.button == 3:
                if self._right_dragging and self.selected_squads:
                    # Drag release: set facing direction
                    self._apply_facing_from_drag(event.pos)
                elif self._right_click_pos:
                    # Short click: normal right-click behavior
                    self._handle_right_click(self._right_click_pos)
                self._right_click_pos = None
                self._right_dragging = False
                self._right_drag_pos = None

        if event.type == pygame.MOUSEMOTION:
            # Track hover for targeting indicators
            wx, wy = self.camera.screen_to_world(*event.pos)
            self._mouse_world_pos = (wx, wy)
            self._hovered_squad = self._find_squad_at(wx, wy)
            if self.selecting:
                self.select_end = event.pos
            if self._right_click_pos:
                dx = event.pos[0] - self._right_click_pos[0]
                dy = event.pos[1] - self._right_click_pos[1]
                drag_dist = (dx * dx + dy * dy) ** 0.5
                if drag_dist > 15:
                    self._right_dragging = True
                self._right_drag_pos = event.pos

    def _find_squad_at(self, wx, wy):
        """Find squad under world coordinates for hover detection."""
        for sq in self.all_squads:
            if sq.is_destroyed:
                continue
            if sq.team != 0 and self.fog_enabled and not sq.visible:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                return sq
        return None

    def _handle_ability_key(self, key):
        """Activate general ability via Q/W/E/R hotkeys."""
        if not self.selected_general:
            return
        g = self.selected_general
        key_map = {pygame.K_q: 0, pygame.K_w: 1, pygame.K_e: 2, pygame.K_r: 3}
        index = key_map.get(key, -1)
        if index < 0:
            return
        friendly = self.player_squads if g.team == 0 else self.enemy_squads
        enemy = self.enemy_squads if g.team == 0 else self.player_squads
        if g.activate_ability(index, friendly, enemy):
            get_audio().play("ability")

    def _handle_left_click(self, pos):
        # Check UI buttons first
        if hasattr(self, '_ui_buttons') and self._handle_ui_click(pos):
            return
        wx, wy = self.camera.screen_to_world(*pos)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT

        if not shift:
            for sq in self.player_squads:
                sq.selected = False
            for g in self.player_generals:
                g.selected = False
            self.selected_squads = []
            self.selected_general = None

        for g in self.player_generals:
            if not g.alive:
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                g.selected = True
                self.selected_general = g
                return

        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                sq.selected = True
                if sq not in self.selected_squads:
                    self.selected_squads.append(sq)
                return

        self.selecting = True
        self.select_start = pos
        self.select_end = pos

    def _finish_box_select(self, pos):
        self.selecting = False
        sx1, sy1 = self.camera.screen_to_world(*self.select_start)
        sx2, sy2 = self.camera.screen_to_world(*pos)
        min_x, min_y = min(sx1, sx2), min(sy1, sy2)
        max_x, max_y = max(sx1, sx2), max(sy1, sy2)

        if abs(pos[0] - self.select_start[0]) < 5:
            return

        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            cx, cy = sq.center
            if min_x <= cx <= max_x and min_y <= cy <= max_y:
                sq.selected = True
                if sq not in self.selected_squads:
                    self.selected_squads.append(sq)

        for g in self.player_generals:
            if not g.alive:
                continue
            if min_x <= g.x <= max_x and min_y <= g.y <= max_y:
                g.selected = True
                self.selected_general = g

    def _handle_deployment_event(self, event):
        """Handle input during deployment phase."""
        self.camera.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Ready up - start the battle
                self.deployment_phase = False
                self._deploy_dragging = None
                get_audio().play("click")
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            wx, wy = self.camera.screen_to_world(*event.pos)
            # Check if clicking on a player squad to drag it
            for sq in self.player_squads:
                if sq.is_destroyed:
                    continue
                bbox = sq.get_bounding_box()
                if point_in_rect(wx, wy, *bbox):
                    self._deploy_dragging = sq
                    sq.selected = True
                    self.selected_squads = [sq]
                    return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._deploy_dragging = None

        if event.type == pygame.MOUSEMOTION and self._deploy_dragging:
            wx, wy = self.camera.screen_to_world(*event.pos)
            zx, zy, zw, zh = self.deploy_zone
            # Clamp to deployment zone
            wx = max(zx + 30, min(zx + zw - 30, wx))
            wy = max(zy + 30, min(zy + zh - 30, wy))
            # Move the squad
            sq = self._deploy_dragging
            dx = wx - sq.x
            dy = wy - sq.y
            sq.x = wx
            sq.y = wy
            sq.target_x = wx
            sq.target_y = wy
            for s in sq.alive_soldiers:
                s.x += dx
                s.y += dy

        # Right-click during deployment: set facing
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._right_click_pos = event.pos
            self._right_click_world = self.camera.screen_to_world(*event.pos)
            self._right_dragging = False
            self._right_drag_pos = event.pos

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if self._right_dragging and self.selected_squads:
                # Set facing only (no move during deployment)
                wx2, wy2 = self.camera.screen_to_world(*event.pos)
                wx1, wy1 = self._right_click_world
                facing = angle_between(wx1, wy1, wx2, wy2)
                for sq in self.selected_squads:
                    sq.facing_angle = facing
            self._right_click_pos = None
            self._right_dragging = False

        if event.type == pygame.MOUSEMOTION and self._right_click_pos:
            dx = event.pos[0] - self._right_click_pos[0]
            dy = event.pos[1] - self._right_click_pos[1]
            if (dx * dx + dy * dy) ** 0.5 > 15:
                self._right_dragging = True
            self._right_drag_pos = event.pos

    def _draw_deployment(self, surface):
        """Draw deployment zone and instructions."""
        zx, zy, zw, zh = self.deploy_zone
        sx, sy = self.camera.world_to_screen(zx, zy)
        sw = self.camera.scale(zw)
        sh = self.camera.scale(zh)

        # Semi-transparent deployment zone
        zone_surf = pygame.Surface((int(sw), int(sh)), pygame.SRCALPHA)
        zone_surf.fill((100, 150, 255, 30))
        surface.blit(zone_surf, (int(sx), int(sy)))
        pygame.draw.rect(surface, (100, 150, 255, 180),
                         (int(sx), int(sy), int(sw), int(sh)), 2)

        # "DEPLOYMENT ZONE" label
        font = pygame.font.SysFont(None, 24)
        label = font.render("DEPLOYMENT ZONE", True, (150, 200, 255))
        surface.blit(label, (int(sx) + int(sw) // 2 - label.get_width() // 2,
                             int(sy) + 5))

        # Instructions at top
        big_font = pygame.font.SysFont(None, 36)
        title = big_font.render("DEPLOYMENT PHASE", True, GOLD)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        inst_font = pygame.font.SysFont(None, 22)
        instructions = [
            "Drag units to position them within the blue zone",
            "Right-click + drag to set facing direction",
            "Press ENTER or SPACE to start the battle",
        ]
        for i, line in enumerate(instructions):
            text = inst_font.render(line, True, (200, 220, 255))
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 90 + i * 24))

        # Ready button hint
        ready_text = big_font.render("[ PRESS ENTER TO BEGIN ]", True, (200, 255, 200))
        surface.blit(ready_text,
                     (SCREEN_WIDTH // 2 - ready_text.get_width() // 2,
                      SCREEN_HEIGHT - 60))

    def _apply_facing_from_drag(self, release_pos):
        """Set selected squads' facing based on right-click drag direction."""
        if not self._right_click_pos:
            return
        wx1, wy1 = self._right_click_world
        wx2, wy2 = self.camera.screen_to_world(*release_pos)
        facing = angle_between(wx1, wy1, wx2, wy2)
        for sq in self.selected_squads:
            sq.facing_angle = facing
            # Also move to the click position
            sq.give_move_order(wx1, wy1)
            sq.facing_angle = facing  # override the angle set by give_move_order

    def _handle_right_click(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)

        target_squad = None
        for sq in self.enemy_squads:
            if sq.is_destroyed or (self.fog_enabled and not sq.visible):
                continue
            bbox = sq.get_bounding_box()
            if point_in_rect(wx, wy, *bbox):
                target_squad = sq
                break

        target_general = None
        for g in self.enemy_generals:
            if not g.alive or (self.fog_enabled and not g.visible):
                continue
            if distance(wx, wy, g.x, g.y) < 20:
                target_general = g
                break

        # Selected general + enemy general = duel challenge
        if target_general and self.selected_general:
            self.selected_general.challenge_duel(target_general)
            return

        # Selected squads targeting
        if self.selected_squads:
            if target_squad:
                for sq in self.selected_squads:
                    sq.give_attack_order(target_squad)
            elif target_general:
                # Squads move to attack the enemy general's position
                for sq in self.selected_squads:
                    sq.give_move_order(target_general.x, target_general.y)
            else:
                count = len(self.selected_squads)
                for i, sq in enumerate(self.selected_squads):
                    offset_y = (i - count / 2.0) * 60
                    sq.give_move_order(wx, wy + offset_y)

        # Selected general with no enemy general target = move order
        if self.selected_general and not target_general:
            if target_squad:
                # General moves to attack the enemy squad position
                self.selected_general.give_move_order(target_squad.x, target_squad.y)
            else:
                self.selected_general.give_move_order(wx, wy)

    def update(self):
        if self.paused or self.deployment_phase:
            self.camera.update()
            return

        for _ in range(self.speed_multiplier):
            self._tick()

        self.camera.update()
        self.battle_timer += 1

    def _tick(self):
        # Compute fog of war visibility
        self._compute_visibility()

        # Snapshot states for sound triggers
        prev_states = {id(sq): sq.state for sq in self.all_squads}
        prev_routed = {id(sq) for sq in self.all_squads
                       if sq.state == SquadState.ROUTED}

        for sq in self.all_squads:
            sq.terrain_mods = self.get_terrain_modifiers(sq)
            sq.update(self.all_squads)

        # Resolve soldier-soldier collisions
        self._resolve_collisions()

        for g in self.player_generals:
            g.update(self.player_squads, self.enemy_squads)
        for g in self.enemy_generals:
            g.update(self.enemy_squads, self.player_squads)

        self._enemy_ai()

        # Sound triggers: charge impact and rout
        audio = get_audio()
        for sq in self.all_squads:
            old_state = prev_states.get(id(sq))
            # Charge -> Fighting = impact sound
            if old_state == SquadState.CHARGING and sq.state == SquadState.FIGHTING:
                audio.play("charge")
            # Newly routed
            if sq.state == SquadState.ROUTED and id(sq) not in prev_routed:
                audio.play("rout")
            # Ranged firing (occasional)
            if sq.state == SquadState.FIRING and self.battle_timer % 60 == 0:
                audio.play("arrow_volley")

        # XP is now awarded post-battle, not during battle (A6 fix)
        # Track kills for post-battle XP calculation only

        # Check general deaths
        dead_generals = [g for g in self.all_generals if not g.alive]
        for g in dead_generals:
            if g.team == 0:
                g.on_death(self.player_squads)
            else:
                g.on_death(self.enemy_squads)
            self.all_generals.remove(g)
            self._dead_generals.append(g)

        self.selected_squads = [s for s in self.selected_squads if not s.is_destroyed]

        prev_result = self.result
        player_alive = any(not sq.is_destroyed for sq in self.player_squads)
        enemy_alive = any(not sq.is_destroyed for sq in self.enemy_squads)
        if not enemy_alive and player_alive:
            self.result = BattleResult.PLAYER_WIN
        elif not player_alive and enemy_alive:
            self.result = BattleResult.PLAYER_LOSS
        elif not player_alive and not enemy_alive:
            self.result = BattleResult.PLAYER_LOSS

        # Victory/defeat sound
        if prev_result == BattleResult.ONGOING and self.result != BattleResult.ONGOING:
            if self.result == BattleResult.PLAYER_WIN:
                audio.play("victory")
            else:
                audio.play("defeat")

    def _enemy_ai(self):
        """Role-based AI: melee advances, cavalry flanks, ranged stays back."""
        alive_enemy = [sq for sq in self.enemy_squads
                       if not sq.is_destroyed and
                       sq.state not in (SquadState.ROUTED, SquadState.BROKEN)]
        alive_player = [sq for sq in self.player_squads if not sq.is_destroyed]
        if not alive_enemy or not alive_player:
            return

        # Classify enemy squads by role
        melee = [sq for sq in alive_enemy if not sq.is_ranged and not sq.is_cavalry]
        cavalry = [sq for sq in alive_enemy if sq.is_cavalry]
        ranged = [sq for sq in alive_enemy if sq.is_ranged and not sq.is_cavalry]

        # Detect battle phase
        engaged_count = sum(1 for sq in alive_enemy if sq.state == SquadState.FIGHTING)
        phase = "opening" if engaged_count == 0 else "engaged"

        # --- Melee infantry: advance toward nearest enemy ---
        for sq in melee:
            if sq.state != SquadState.IDLE:
                continue
            best = self._ai_find_best_target(sq, alive_player, prefer_melee=True)
            if best:
                sq.give_attack_order(best)

        # --- Spearmen: if they can brace, hold position when cavalry is near ---
        for sq in melee:
            if sq.is_spear and sq.state == SquadState.IDLE:
                # Check if any enemy cavalry is approaching
                enemy_cav = [p for p in alive_player if p.is_cavalry]
                for cav in enemy_cav:
                    d = distance(sq.x, sq.y, cav.x, cav.y)
                    if d < 300:
                        # Stay put and brace! Don't give attack order
                        break

        # --- Cavalry: wait for engagement, then flank ---
        for sq in cavalry:
            if sq.state != SquadState.IDLE:
                continue
            if phase == "opening":
                # Opening: hold cavalry back, wait for melee to engage
                # Only engage if no melee units to screen
                if melee:
                    continue
            # Find best flanking target (prefer enemies already fighting)
            target = self._ai_find_flank_target(sq, alive_player)
            if target:
                sq.give_attack_order(target)

        # --- Ranged: stay behind melee line, pick high-value targets ---
        for sq in ranged:
            if sq.state != SquadState.IDLE:
                continue
            # Target priority: other ranged > low-morale > nearest
            target = self._ai_find_ranged_target(sq, alive_player)
            if target:
                d = distance(sq.x, sq.y, target.x, target.y)
                if d <= sq.unit_stats.range_distance:
                    sq.give_attack_order(target)
                else:
                    # Move toward range but not too close
                    tx, ty = target.center
                    # Stop at max range distance
                    dx, dy = tx - sq.x, ty - sq.y
                    dist = max(1, (dx**2 + dy**2)**0.5)
                    approach_dist = dist - sq.unit_stats.range_distance * 0.8
                    if approach_dist > 0:
                        nx, ny = dx / dist, dy / dist
                        sq.give_move_order(sq.x + nx * approach_dist,
                                           sq.y + ny * approach_dist)

        # --- General AI ---
        for g in self.enemy_generals:
            if not g.alive or g.duel_state == DuelState.ACTIVE:
                continue

            # Smart ability usage based on general type
            self._ai_use_general_abilities(g)

            # Champion: seek duels
            if g.general_type == "Champion":
                for pg in self.player_generals:
                    if pg.alive and pg.duel_state == DuelState.NONE:
                        d = distance(g.x, g.y, pg.x, pg.y)
                        if d < 200:
                            g.challenge_duel(pg)
                            break

            # Move general toward the battle
            if alive_player:
                targets = [sq for sq in alive_player if sq.state == SquadState.FIGHTING]
                if not targets:
                    targets = alive_player
                if targets:
                    t = min(targets, key=lambda s: distance(g.x, g.y, s.x, s.y))
                    g.give_move_order(t.x, t.y)

    def _ai_find_best_target(self, sq, enemies, prefer_melee=False):
        """Find best target for a melee unit."""
        best = None
        best_score = -float("inf")
        for e in enemies:
            d = distance(sq.x, sq.y, e.x, e.y)
            # Score: prefer close, low morale, and already-fighting enemies
            score = -d * 0.1
            if e.morale < 40:
                score += 50  # attack wavering enemies
            if e.state == SquadState.FIGHTING:
                score += 30  # pile on engaged enemies
            if prefer_melee and e.is_ranged:
                score += 20  # melee should try to reach ranged
            if score > best_score:
                best_score = score
                best = e
        return best

    def _ai_find_flank_target(self, cavalry_sq, enemies):
        """Find best target for cavalry to flank."""
        best = None
        best_score = -float("inf")
        for e in enemies:
            d = distance(cavalry_sq.x, cavalry_sq.y, e.x, e.y)
            score = -d * 0.05
            # Strongly prefer enemies already engaged in melee (rear charge!)
            if e.state == SquadState.FIGHTING:
                score += 100
            # Avoid braced spearmen
            if e.is_braced or (e.is_spear and e.state == SquadState.IDLE):
                score -= 200
            # Prefer low morale (push them to rout)
            if e.morale < 50:
                score += 40
            # Prefer ranged units (they're squishy)
            if e.is_ranged:
                score += 30
            if score > best_score:
                best_score = score
                best = e
        return best

    def _ai_find_ranged_target(self, ranged_sq, enemies):
        """Find best target for ranged units."""
        in_range = [e for e in enemies
                    if distance(ranged_sq.x, ranged_sq.y, e.x, e.y)
                    <= ranged_sq.unit_stats.range_distance * 1.2]
        if not in_range:
            # Target nearest
            return min(enemies, key=lambda e: distance(ranged_sq.x, ranged_sq.y, e.x, e.y))

        best = None
        best_score = -float("inf")
        for e in in_range:
            score = 0
            # Target priority: ranged > cavalry > low armor > low morale
            if e.is_ranged:
                score += 40
            if e.is_cavalry:
                score += 20
            if e.unit_stats.armor < 15:
                score += 30  # easy to damage
            if e.morale < 50:
                score += 25  # push them over the edge
            # Prefer larger groups (more value per volley)
            score += e.alive_count * 2
            if score > best_score:
                best_score = score
                best = e
        return best

    def _ai_use_general_abilities(self, general):
        """Smart ability usage for enemy generals."""
        avail = general.available_abilities
        ready = [(i, a) for i, a in enumerate(avail) if a.ready]
        if not ready:
            return

        friendly = self.enemy_squads
        enemy = self.player_squads

        for idx, ability in ready:
            name = ability.name

            # Commander abilities
            if name == "Rally the Troops":
                # Use when squads are low morale
                low_morale = [sq for sq in friendly if not sq.is_destroyed and sq.morale < 40]
                if low_morale:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Second Wind":
                # Use when squads are exhausted
                tired = [sq for sq in friendly if not sq.is_destroyed and sq.exhaustion > 60]
                if tired:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Hold the Line":
                # Use when multiple squads near breaking
                breaking = [sq for sq in friendly if not sq.is_destroyed and sq.morale < 30]
                if len(breaking) >= 2:
                    general.activate_ability(idx, friendly, enemy)
                    return

            # Champion abilities
            elif name == "Bloodlust":
                # Use before engaging
                if general.duel_state == DuelState.ACTIVE or any(
                    distance(general.x, general.y, e.x, e.y) < 100
                    for e in enemy if not e.is_destroyed
                ):
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Intimidate":
                # Use when near enemy clusters
                nearby_enemy = [e for e in enemy if not e.is_destroyed and
                                distance(general.x, general.y, e.x, e.y) < ability.radius]
                if len(nearby_enemy) >= 2:
                    general.activate_ability(idx, friendly, enemy)
                    return

            # Strategist abilities
            elif name == "Precision Volley":
                # Use when ranged units are firing
                ranged_firing = [sq for sq in friendly if sq.is_ranged and
                                 sq.state == SquadState.FIRING and not sq.is_destroyed]
                if ranged_firing:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Weaken Resolve":
                # Target enemy with lowest morale
                targets = [e for e in enemy if not e.is_destroyed and e.morale < 50]
                if targets:
                    general.activate_ability(idx, friendly, enemy)
                    return

    def draw(self, surface):
        surface.fill((90, 140, 60))

        grid_size = 100
        for x in range(0, BATTLE_MAP_WIDTH, grid_size):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, BATTLE_MAP_HEIGHT)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)
        for y in range(0, BATTLE_MAP_HEIGHT, grid_size):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(BATTLE_MAP_WIDTH, y)
            pygame.draw.line(surface, (80, 130, 55), start, end, 1)

        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            screen_pos = self.camera.world_to_screen(rx, ry)
            w = self.camera.scale(rw)
            h = self.camera.scale(rh)
            pygame.draw.rect(surface, t["color"], (*screen_pos, w, h))
            if self.camera.zoom > 0.4:
                font = pygame.font.SysFont(None, 16)
                text = font.render(t["type"].title(), True, (200, 200, 200))
                surface.blit(text, (screen_pos[0] + 5, screen_pos[1] + 5))

        # Draw fog overlay behind enemy units
        if self.fog_enabled:
            self._draw_fog(surface)

        for sq in self.all_squads:
            if not sq.is_destroyed:
                fog_hidden = (sq.team != 0 and not sq.visible and self.fog_enabled)
                sq.draw(surface, self.camera, fog_hidden=fog_hidden)

        for g in self.all_generals:
            fog_hidden = (g.team != 0 and not g.visible and self.fog_enabled)
            g.draw(surface, self.camera, fog_hidden=fog_hidden)

        if self.selecting:
            sx = min(self.select_start[0], self.select_end[0])
            sy = min(self.select_start[1], self.select_end[1])
            sw = abs(self.select_end[0] - self.select_start[0])
            sh = abs(self.select_end[1] - self.select_start[1])
            if sw > 0 and sh > 0:
                select_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                select_surf.fill((100, 200, 100, 40))
                surface.blit(select_surf, (sx, sy))
                pygame.draw.rect(surface, (100, 200, 100), (sx, sy, sw, sh), 1)

        # Right-click drag facing indicator
        if self._right_dragging and self._right_click_pos and self._right_drag_pos:
            sx1, sy1 = self._right_click_pos
            sx2, sy2 = self._right_drag_pos
            # Draw movement destination marker
            pygame.draw.circle(surface, (200, 200, 255), (int(sx1), int(sy1)), 6, 2)
            # Draw facing direction arrow
            dx, dy = sx2 - sx1, sy2 - sy1
            d = max(1, (dx * dx + dy * dy) ** 0.5)
            nx, ny = dx / d, dy / d
            arrow_len = min(d, 60)
            ax, ay = sx1 + nx * arrow_len, sy1 + ny * arrow_len
            pygame.draw.line(surface, (200, 200, 255),
                             (int(sx1), int(sy1)), (int(ax), int(ay)), 3)
            # Arrowhead
            for side in [-0.5, 0.5]:
                head_angle = math.atan2(ny, nx) + side
                hx = ax - math.cos(head_angle) * 12
                hy = ay - math.sin(head_angle) * 12
                pygame.draw.line(surface, (200, 200, 255),
                                 (int(ax), int(ay)), (int(hx), int(hy)), 3)

        # Targeting indicators
        self._draw_targeting_lines(surface)

        # Weather particles on top
        self._draw_weather(surface)

        self._draw_hud(surface)

        # Deployment overlay (on top of everything)
        if self.deployment_phase:
            self._draw_deployment(surface)

    def _draw_targeting_lines(self, surface):
        """Draw targeting lines for selected and hovered units.

        Selected units: show movement/attack order lines (waypoint indicators).
        Hovered units: show current target line, attack range circle, and
        engagement state.  When nothing is hovered the battlefield stays clean.
        """
        target_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Determine which squads to show targeting for
        show_squads = set(self.selected_squads)
        if self._hovered_squad:
            show_squads.add(self._hovered_squad)

        for sq in show_squads:
            if sq.is_destroyed:
                continue

            scx, scy = self.camera.world_to_screen(*sq.center)

            # Show range indicator for hovered ranged units (selected ones already
            # get their range indicator drawn in squad.draw)
            if sq is self._hovered_squad and sq.is_ranged and not sq.selected:
                light_color = TEAM_COLORS_LIGHT.get(sq.team, (180, 180, 180))
                r = self.camera.scale(sq.unit_stats.range_distance)
                if r > 2:
                    if sq.unit_stats.can_fire_while_moving:
                        # Circle for mobile shooters
                        range_surf = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
                        pygame.draw.circle(range_surf, (*light_color, 30), (int(r), int(r)), int(r))
                        pygame.draw.circle(range_surf, (*light_color, 60), (int(r), int(r)), int(r), 1)
                        surface.blit(range_surf, (int(scx - r), int(scy - r)))
                    else:
                        # Cone for stationary ranged
                        cone_half_angle = 0.5
                        cone_surf = pygame.Surface((int(r * 2 + 4), int(r * 2 + 4)), pygame.SRCALPHA)
                        cx_s, cy_s = int(r + 2), int(r + 2)
                        num_pts = 16
                        pts = [(cx_s, cy_s)]
                        for ii in range(num_pts + 1):
                            a = sq.facing_angle - cone_half_angle + (2 * cone_half_angle * ii / num_pts)
                            px = cx_s + math.cos(a) * r
                            py = cy_s + math.sin(a) * r
                            pts.append((int(px), int(py)))
                        pts.append((cx_s, cy_s))
                        pygame.draw.polygon(cone_surf, (*light_color, 25), pts)
                        pygame.draw.lines(cone_surf, (*light_color, 50), True, pts, 1)
                        surface.blit(cone_surf, (int(scx - r - 2), int(scy - r - 2)))

            # Show engagement state for hovered squad
            if sq is self._hovered_squad and sq.state == SquadState.FIGHTING:
                eng_font = pygame.font.SysFont(None, 16)
                eng_text = eng_font.render("ENGAGED", True, (255, 200, 80))
                surface.blit(eng_text, (int(scx) - eng_text.get_width() // 2,
                                        int(scy) + self.camera.scale(25)))

            # Target line
            if not sq.target_squad or sq.target_squad.is_destroyed:
                continue
            cx, cy = sq.center
            tx, ty = sq.target_squad.center
            sx1, sy1 = self.camera.world_to_screen(cx, cy)
            sx2, sy2 = self.camera.world_to_screen(tx, ty)
            if sq.team == 0:
                if sq.state == SquadState.FIRING:
                    color = (100, 200, 255, 100)
                elif sq.state in (SquadState.CHARGING, SquadState.FIGHTING):
                    color = (100, 255, 100, 120)
                else:
                    color = (200, 200, 100, 80)
            else:
                color = (255, 80, 80, 90)
            pygame.draw.line(target_surf, color,
                             (int(sx1), int(sy1)), (int(sx2), int(sy2)), 2)
            pygame.draw.circle(target_surf, color, (int(sx2), int(sy2)), 4)

        surface.blit(target_surf, (0, 0))

    def _draw_weather(self, surface):
        """Draw weather particle effects."""
        if self.weather == "clear":
            return
        elif self.weather == "rain":
            for p in self.weather_particles:
                p[1] += p[2]  # fall
                p[0] += 1     # slight angle
                if p[1] > SCREEN_HEIGHT:
                    p[1] = 0
                    p[0] = random.randint(0, SCREEN_WIDTH)
                pygame.draw.line(surface, (150, 170, 220),
                                 (int(p[0]), int(p[1])),
                                 (int(p[0]) + 1, int(p[1]) + 4))
        elif self.weather == "fog":
            fog_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for p in self.weather_particles:
                p[0] += random.uniform(-0.3, 0.3)  # drift
                alpha = random.randint(15, 35)
                r = p[2]
                pygame.draw.circle(fog_surf, (200, 200, 210, alpha),
                                   (int(p[0]) % SCREEN_WIDTH, int(p[1])), int(r))
            surface.blit(fog_surf, (0, 0))
        elif self.weather == "mud":
            # Brown tint overlay
            mud_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            mud_surf.fill((80, 50, 20, 25))
            surface.blit(mud_surf, (0, 0))
        elif self.weather == "wind":
            for p in self.weather_particles:
                p[0] += p[2] * self.wind_direction * 2
                p[1] += random.uniform(-0.5, 0.5)
                if p[0] > SCREEN_WIDTH or p[0] < 0:
                    p[0] = 0 if self.wind_direction > 0 else SCREEN_WIDTH
                    p[1] = random.randint(0, SCREEN_HEIGHT)
                pygame.draw.line(surface, (180, 180, 160),
                                 (int(p[0]), int(p[1])),
                                 (int(p[0]) + int(3 * self.wind_direction), int(p[1])))

    def _draw_fog(self, surface):
        """Draw fog of war overlay with vision holes for player units."""
        # Create a dark overlay covering the whole screen
        fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fog.fill((0, 0, 0, FOG_ALPHA))

        # Cut holes for each player vision source
        for sq in self.player_squads:
            if sq.is_destroyed:
                continue
            cx, cy = sq.center
            sx, sy = self.camera.world_to_screen(cx, cy)
            r = self.camera.scale(sq.vision_radius)
            if r > 2:
                pygame.draw.circle(fog, (0, 0, 0, 0), (int(sx), int(sy)), int(r))

        for g in self.player_generals:
            if not g.alive:
                continue
            sx, sy = self.camera.world_to_screen(g.x, g.y)
            r = self.camera.scale(VISION_CAVALRY)
            if r > 2:
                pygame.draw.circle(fog, (0, 0, 0, 0), (int(sx), int(sy)), int(r))

        surface.blit(fog, (0, 0))

    # ─── UI Button System ───
    def _make_button(self, x, y, w, h, text, active=False, enabled=True):
        """Return a button dict for the UI system."""
        return {"x": x, "y": y, "w": w, "h": h, "text": text,
                "active": active, "enabled": enabled}

    def _draw_button(self, surface, btn, font):
        """Draw a single UI button."""
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
        surface.blit(text_surf, (x + w // 2 - text_surf.get_width() // 2,
                                  y + h // 2 - text_surf.get_height() // 2))
        return pygame.Rect(x, y, w, h)

    def _point_in_button(self, pos, btn):
        return (btn["x"] <= pos[0] <= btn["x"] + btn["w"] and
                btn["y"] <= pos[1] <= btn["y"] + btn["h"])

    def _handle_ui_click(self, pos):
        """Handle clicks on bottom panel UI buttons. Returns True if handled."""
        if not self._ui_buttons:
            return False
        for btn_id, btn in self._ui_buttons.items():
            if not btn["enabled"]:
                continue
            if self._point_in_button(pos, btn):
                self._on_ui_button_click(btn_id)
                return True
        # Check unit card clicks
        for i, card_rect in enumerate(self._unit_card_rects):
            if card_rect.collidepoint(pos):
                self._on_unit_card_click(i)
                return True
        return False

    def _on_ui_button_click(self, btn_id):
        """Handle a UI button being clicked."""
        if btn_id == "pause":
            self.paused = not self.paused
        elif btn_id == "speed1":
            self.speed_multiplier = 1
        elif btn_id == "speed2":
            self.speed_multiplier = 2
        elif btn_id == "speed3":
            self.speed_multiplier = 4
        elif btn_id == "walk":
            for sq in self.selected_squads:
                sq.movement_mode = MOVE_MODE_WALK
        elif btn_id == "march":
            for sq in self.selected_squads:
                sq.movement_mode = MOVE_MODE_MARCH
        elif btn_id == "run":
            for sq in self.selected_squads:
                sq.movement_mode = MOVE_MODE_RUN
        elif btn_id == "defensive":
            for sq in self.selected_squads:
                sq.defensive_stance = not sq.defensive_stance
                if sq.defensive_stance:
                    sq.defensive_anchor_x = sq.x
                    sq.defensive_anchor_y = sq.y
        elif btn_id == "skirmish":
            for sq in self.selected_squads:
                if sq.is_ranged:
                    sq.skirmish_stance = not sq.skirmish_stance
        elif btn_id == "fire":
            for sq in self.selected_squads:
                if sq.is_ranged:
                    sq.fire_at_will = not sq.fire_at_will
        elif btn_id.startswith("form_"):
            form_map = {"form_line": Formation.LINE, "form_column": Formation.COLUMN,
                        "form_square": Formation.SQUARE, "form_loose": Formation.LOOSE,
                        "form_wedge": Formation.WEDGE}
            if btn_id in form_map:
                for sq in self.selected_squads:
                    sq.set_formation(form_map[btn_id])
        elif btn_id.startswith("ability_"):
            idx = int(btn_id.split("_")[1])
            if self.selected_general:
                friendly = self.player_squads if self.selected_general.team == 0 else self.enemy_squads
                enemy = self.enemy_squads if self.selected_general.team == 0 else self.player_squads
                if self.selected_general.activate_ability(idx, friendly, enemy):
                    get_audio().play("ability")

    def _on_unit_card_click(self, index):
        """Select a player squad by clicking its unit card."""
        alive_squads = [sq for sq in self.player_squads if not sq.is_destroyed]
        if index < len(alive_squads):
            for sq in self.player_squads:
                sq.selected = False
            for g in self.player_generals:
                g.selected = False
            self.selected_general = None
            sq = alive_squads[index]
            sq.selected = True
            self.selected_squads = [sq]

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 20)
        small_font = pygame.font.SysFont(None, 16)
        btn_font = pygame.font.SysFont(None, 15)
        self._ui_buttons = {}
        self._unit_card_rects = []

        # ── Top bar ──
        bar_surf = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 160))
        surface.blit(bar_surf, (0, 0))

        minutes = self.battle_timer // (60 * 60)
        seconds = (self.battle_timer // 60) % 60
        timer_text = font.render(f"Battle: {minutes:02d}:{seconds:02d}", True, WHITE)
        surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 8))

        # Speed buttons in top bar
        for i, (label, spd, btn_id) in enumerate([("1x", 1, "speed1"),
                                                    ("2x", 2, "speed2"),
                                                    ("4x", 4, "speed3")]):
            bx = SCREEN_WIDTH // 2 + 80 + i * 36
            btn = self._make_button(bx, 4, 32, 26, label,
                                     active=(self.speed_multiplier == spd))
            self._ui_buttons[btn_id] = btn
            self._draw_button(surface, btn, btn_font)

        # Pause button
        pause_btn = self._make_button(SCREEN_WIDTH // 2 + 80 + 3 * 36 + 8, 4, 55, 26,
                                       "PAUSED" if self.paused else "Pause",
                                       active=self.paused)
        self._ui_buttons["pause"] = pause_btn
        self._draw_button(surface, pause_btn, btn_font)

        if self.weather != "clear":
            weather_colors = {
                "rain": (100, 150, 255), "fog": (180, 180, 200),
                "mud": (160, 120, 60), "wind": (180, 200, 160),
            }
            wc = weather_colors.get(self.weather, WHITE)
            w_text = font.render(f"Weather: {self.weather.title()}", True, wc)
            surface.blit(w_text, (SCREEN_WIDTH // 2 - 250, 8))

        p_alive = sum(sq.alive_count for sq in self.player_squads)
        e_alive = sum(sq.alive_count for sq in self.enemy_squads)
        p_text = font.render(f"Your Army: {p_alive}", True, TEAM_COLORS_LIGHT[0])
        e_text = font.render(f"Enemy Army: {e_alive}", True, TEAM_COLORS_LIGHT[1])
        surface.blit(p_text, (10, 8))
        surface.blit(e_text, (SCREEN_WIDTH - e_text.get_width() - 10, 8))

        # ── Bottom panel ──
        panel_h = 110
        panel_y = SCREEN_HEIGHT - panel_h
        panel_surf = pygame.Surface((SCREEN_WIDTH, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, panel_y))
        pygame.draw.line(surface, (80, 80, 100), (0, panel_y), (SCREEN_WIDTH, panel_y), 1)

        # Unit cards along bottom
        self._draw_unit_cards(surface, panel_y, small_font, btn_font)

        # Selected unit info + buttons
        if self.selected_squads:
            self._draw_selection_panel(surface, font, small_font, btn_font, panel_y)
        elif self.selected_general:
            self._draw_general_panel(surface, font, small_font, btn_font, panel_y)

        if self.result != BattleResult.ONGOING:
            self._draw_result_banner(surface)

    def _draw_unit_cards(self, surface, panel_y, small_font, btn_font):
        """Draw clickable unit cards along the bottom of the screen."""
        alive_squads = [sq for sq in self.player_squads if not sq.is_destroyed]
        card_w = 58
        card_h = 40
        card_y = panel_y + 65
        start_x = 10
        self._unit_card_rects = []

        for i, sq in enumerate(alive_squads):
            cx = start_x + i * (card_w + 4)
            if cx + card_w > SCREEN_WIDTH - 10:
                break

            is_selected = sq in self.selected_squads
            bg_color = (60, 100, 60, 200) if is_selected else (40, 40, 50, 180)
            border_color = (100, 200, 100) if is_selected else (70, 70, 90)

            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill(bg_color)
            surface.blit(card_surf, (cx, card_y))
            pygame.draw.rect(surface, border_color, (cx, card_y, card_w, card_h), 1)

            # Unit type abbreviation
            abbrev = sq.unit_stats.name[:5]
            text = btn_font.render(abbrev, True, TEAM_COLORS_LIGHT[sq.team])
            surface.blit(text, (cx + 2, card_y + 2))

            # Count
            count_text = btn_font.render(f"{sq.alive_count}", True, WHITE)
            surface.blit(count_text, (cx + 2, card_y + 15))

            # Mini morale bar
            bar_x = cx + 2
            bar_y_pos = card_y + card_h - 8
            bar_w = card_w - 4
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y_pos, bar_w, 4))
            morale_w = int(bar_w * sq.morale / 100)
            morale_color = (50, 200, 50) if sq.morale > 50 else (
                (220, 200, 50) if sq.morale > 25 else (200, 50, 50))
            pygame.draw.rect(surface, morale_color, (bar_x, bar_y_pos, morale_w, 4))

            self._unit_card_rects.append(pygame.Rect(cx, card_y, card_w, card_h))

    def _draw_selection_panel(self, surface, font, small_font, btn_font, panel_y):
        """Draw selected unit info with clickable stance/mode buttons."""
        # Unit info area (left side of bottom panel)
        y = panel_y + 4
        sq = self.selected_squads[0] if len(self.selected_squads) == 1 else None

        if sq:
            # Single unit selected — detailed view
            info = (f"{sq.unit_stats.name}: {sq.alive_count}/{sq.initial_count}"
                    f"  Morale:{int(sq.morale)}%  {sq.exhaustion_display}")
            text = small_font.render(info, True, TEAM_COLORS_LIGHT[sq.team])
            surface.blit(text, (10, y))
            y += 16
            ws = sq.unit_stats.weapon_strength
            ap = sq.unit_stats.armor_penetration
            extra = f"WS:{ws} AP:{ap}%"
            if sq.unit_stats.ranged_strength > 0:
                extra += f"  RS:{sq.unit_stats.ranged_strength} RAP:{sq.unit_stats.ranged_armor_penetration}%"
            if sq.is_braced:
                extra += "  BRACED"
            text2 = small_font.render(extra, True, (160, 160, 160))
            surface.blit(text2, (10, y))
        else:
            # Multiple units — summary
            count = len(self.selected_squads)
            total = sum(sq.alive_count for sq in self.selected_squads)
            text = font.render(f"{count} units selected ({total} soldiers)", True, WHITE)
            surface.blit(text, (10, y))

        # ── Clickable buttons (right side of bottom panel) ──
        btn_y = panel_y + 4
        btn_x = 350

        # Movement mode buttons
        mode_label = small_font.render("Move:", True, (150, 150, 160))
        surface.blit(mode_label, (btn_x, btn_y + 2))
        btn_x += 40
        active_mode = self.selected_squads[0].movement_mode if self.selected_squads else MOVE_MODE_MARCH
        for label, mode, bid in [("Walk", MOVE_MODE_WALK, "walk"),
                                  ("March", MOVE_MODE_MARCH, "march"),
                                  ("Run", MOVE_MODE_RUN, "run")]:
            btn = self._make_button(btn_x, btn_y, 44, 20, label,
                                     active=(active_mode == mode))
            self._ui_buttons[bid] = btn
            self._draw_button(surface, btn, btn_font)
            btn_x += 48

        # Stance buttons
        btn_x += 8
        stance_label = small_font.render("Stance:", True, (150, 150, 160))
        surface.blit(stance_label, (btn_x, btn_y + 2))
        btn_x += 50
        any_def = any(sq.defensive_stance for sq in self.selected_squads)
        btn = self._make_button(btn_x, btn_y, 60, 20, "Defensive", active=any_def)
        self._ui_buttons["defensive"] = btn
        self._draw_button(surface, btn, btn_font)
        btn_x += 64

        any_skirm = any(sq.skirmish_stance for sq in self.selected_squads)
        has_ranged = any(sq.is_ranged for sq in self.selected_squads)
        btn = self._make_button(btn_x, btn_y, 58, 20, "Skirmish",
                                 active=any_skirm, enabled=has_ranged)
        self._ui_buttons["skirmish"] = btn
        self._draw_button(surface, btn, btn_font)
        btn_x += 62

        any_fire = any(sq.fire_at_will for sq in self.selected_squads if sq.is_ranged)
        btn = self._make_button(btn_x, btn_y, 48, 20, "Fire",
                                 active=any_fire, enabled=has_ranged)
        self._ui_buttons["fire"] = btn
        self._draw_button(surface, btn, btn_font)

        # Formation buttons (second row)
        btn_y2 = panel_y + 30
        btn_x2 = 350
        form_label = small_font.render("Formation:", True, (150, 150, 160))
        surface.blit(form_label, (btn_x2, btn_y2 + 2))
        btn_x2 += 72
        active_form = self.selected_squads[0].formation if self.selected_squads else Formation.LINE
        for label, form, bid in [("Line", Formation.LINE, "form_line"),
                                  ("Column", Formation.COLUMN, "form_column"),
                                  ("Square", Formation.SQUARE, "form_square"),
                                  ("Loose", Formation.LOOSE, "form_loose"),
                                  ("Wedge", Formation.WEDGE, "form_wedge")]:
            btn = self._make_button(btn_x2, btn_y2, 48, 20, label,
                                     active=(active_form == form))
            self._ui_buttons[bid] = btn
            self._draw_button(surface, btn, btn_font)
            btn_x2 += 52

    def _draw_general_panel(self, surface, font, small_font, btn_font, panel_y):
        g = self.selected_general

        y = panel_y + 4
        header = font.render(f"{g.name} ({g.general_type}) Lv{g.level}", True, GOLD)
        surface.blit(header, (10, y))
        y += 20
        hp = small_font.render(
            f"HP: {int(g.health)}/{int(g.max_health)}  ATK:{g.melee_attack} DEF:{g.melee_defense}"
            f"  Kills:{g.kills} Duels:{g.duels_won}",
            True, WHITE)
        surface.blit(hp, (10, y))
        y += 16

        if g.duel_state == DuelState.ACTIVE:
            duel_text = small_font.render(
                f"DUELING {g.duel_opponent.name}! Score: {g.duel_score}-{g.duel_opponent.duel_score}",
                True, GOLD)
            surface.blit(duel_text, (10, y))

        # Ability buttons (right side)
        btn_x = 400
        btn_y = panel_y + 4
        keys = ["Q", "W", "E", "R"]
        for i, ability in enumerate(g.available_abilities):
            if i >= 4:
                break
            cd_text = ""
            if not ability.ready:
                cd_secs = ability.cooldown // 60
                cd_text = f" {cd_secs}s"
            label = f"[{keys[i]}] {ability.name}{cd_text}"
            btn = self._make_button(btn_x, btn_y + i * 24, 200, 20, label,
                                     active=False, enabled=ability.ready)
            self._ui_buttons[f"ability_{i}"] = btn
            self._draw_button(surface, btn, btn_font)

        # Locked abilities
        lock_y = btn_y + len(g.available_abilities) * 24
        for ability in g.abilities:
            if ability.level_required > g.level:
                text = small_font.render(
                    f"Lv{ability.level_required}: {ability.name} (Locked)",
                    True, (80, 80, 80))
                surface.blit(text, (btn_x, lock_y))
                lock_y += 16

    def _draw_result_banner(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))

        big_font = pygame.font.SysFont(None, 72)
        if self.result == BattleResult.PLAYER_WIN:
            text = big_font.render("VICTORY!", True, GOLD)
        else:
            text = big_font.render("DEFEAT!", True, (200, 50, 50))
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2,
                            SCREEN_HEIGHT // 2 - 50))

        font = pygame.font.SysFont(None, 28)
        sub = font.render("Press ENTER to continue", True, WHITE)
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                           SCREEN_HEIGHT // 2 + 30))
