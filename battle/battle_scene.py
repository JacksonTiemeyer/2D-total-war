"""Battle scene - handles the real-time tactical combat."""

import math
import random
import pygame
from battle import environment as battle_environment
from battle import input_handlers as battle_input
from battle import runtime as battle_runtime
from battle import ui as battle_ui
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
    SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER,
    SEASON_SUMMER_EXHAUSTION_MULT, SEASON_AUTUMN_MUD_CHANCE,
    SEASON_WINTER_RANGED_PENALTY, SEASON_WINTER_HARSH_WEATHER_CHANCE,
)
from core.camera import Camera
from core.utils import distance, point_in_rect, angle_between, get_font
from battle.squad import Squad, SquadState, Formation
from battle.general import General, DuelState
from core.audio import get_audio


class BattleResult:
    ONGOING = "ongoing"
    PLAYER_WIN = "player_win"
    PLAYER_LOSS = "player_loss"


class BattleScene:
    def __init__(self, player_army, enemy_army, terrain_type=None, season=None, companions=None):
        self.camera = Camera(BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT)
        self.camera.center_on(BATTLE_MAP_WIDTH / 2, BATTLE_MAP_HEIGHT / 2)

        # D1: Campaign terrain type and D2: season
        self.terrain_type = terrain_type or "plains"
        self.season = season

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
        self.combat_zones = []  # active CombatZone instances

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

        # Weather and terrain are initialized after deployments are ready.
        self.weather = None
        self.wind_direction = random.uniform(-1, 1)  # -1 = left, +1 = right
        self.weather_particles = []
        self.season_exhaustion_mult = 1.0
        self.terrain = []

        # Deploy armies
        self._deploy_armies(player_army, enemy_army)

        # Deploy companions as additional player generals
        self._companion_generals = []  # track for post-battle XP
        if companions:
            self._deploy_companions(companions)

        # Combat engine (Patch B) — opt-in bridge for future migration
        self._combat_engine = None

        # Wire up generals' enemy general references (for Challenge ability)
        for g in self.player_generals:
            g._all_enemy_generals = self.enemy_generals
        for g in self.enemy_generals:
            g._all_enemy_generals = self.player_generals

        # Patch A: initialize combat engine scaffold after armies and generals are deployed
        battle_runtime.initialize_runtime(self)

    def _choose_weather(self):
        """D2: Choose weather based on season and terrain."""
        return battle_environment.choose_weather(self)

    def _generate_terrain(self):
        """D1: Generate terrain based on terrain_type from campaign map."""
        battle_environment.generate_terrain(self)

    def get_terrain_at(self, x, y):
        """Return terrain type at given world position, or None."""
        return battle_environment.get_terrain_at(self, x, y)

    def is_water_at(self, x, y):
        """D1: Check if position is in water (impassable for coastal maps)."""
        return battle_environment.is_water_at(self, x, y)

    def get_terrain_modifiers(self, squad):
        """Compute terrain modifiers for a squad based on its position."""
        return battle_environment.get_terrain_modifiers(self, squad)

    def _init_weather_particles(self):
        """Create initial particle pool for weather visuals."""
        battle_environment.init_weather_particles(self)

    def get_weather_modifiers(self):
        """Return global combat modifiers based on weather."""
        return battle_environment.get_weather_modifiers(self)

    def _is_los_blocked(self, x1, y1, x2, y2):
        """Check if line of sight is blocked by a forest."""
        return battle_environment.is_los_blocked(self, x1, y1, x2, y2)

    def _compute_visibility(self):
        """Compute which enemy squads are visible to the player."""
        battle_environment.compute_visibility(self)

    def _resolve_collisions(self):
        """Resolve soldier-soldier collisions using spatial grid.

        Includes engagement lock (soldiers in melee contact cannot freely
        disengage) and cavalry punch-through on charge.
        """
        cell_size = COLLISION_GRID_CELL_SIZE
        grid = {}

        # Build spatial grid of all living soldiers
        # Skip idle squads not in combat zones to prevent drift from external pushes
        all_soldiers = []
        for sq in self.all_squads:
            if sq.is_destroyed or sq.state == SquadState.ROUTED:
                continue
            if sq.state == SquadState.IDLE and getattr(sq, 'battleground', None) is None:
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
                # Clear reverse reference to avoid stale pointers
                partner = s.engaged_with
                if partner.engaged_with is s:
                    partner.engaged_with = None
                s.engaged_with = None

        # Check collisions in neighboring cells
        processed_pairs = set()
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
                        # Skip pairs already processed (avoid double push)
                        pair_key = (id(s1), id(s2)) if id(s1) < id(s2) else (id(s2), id(s1))
                        if pair_key in processed_pairs:
                            continue
                        processed_pairs.add(pair_key)
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
                            # Spawn CombatZone for opposing squads if neither is in one
                            if getattr(sq1, 'battleground', None) is None and getattr(sq2, 'battleground', None) is None:
                                try:
                                    from battle.battleground import CombatZone
                                    zone = CombatZone(sq1, sq2)
                                    self.combat_zones.append(zone)
                                    # Add attached generals to the zone
                                    self._add_generals_to_zone(zone, sq1, 'a')
                                    self._add_generals_to_zone(zone, sq2, 'b')
                                except Exception:
                                    pass
                            # If one squad is already in a zone, add the other as reinforcement
                            elif getattr(sq1, 'battleground', None) is not None and getattr(sq2, 'battleground', None) is None:
                                zone = sq1.battleground
                                if zone.active:
                                    side = 'b' if sq1 in zone.squads_a else 'a'
                                    if zone.add_reinforcement(sq2, side):
                                        self._add_generals_to_zone(zone, sq2, side)
                            elif getattr(sq2, 'battleground', None) is not None and getattr(sq1, 'battleground', None) is None:
                                zone = sq2.battleground
                                if zone.active:
                                    side = 'b' if sq2 in zone.squads_a else 'a'
                                    if zone.add_reinforcement(sq1, side):
                                        self._add_generals_to_zone(zone, sq1, side)

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

    def _add_generals_to_zone(self, zone, squad, side):
        """If a squad has an attached general, add them to the combat zone."""
        for g in self.all_generals:
            if g.alive and getattr(g, 'attached_squad', None) is squad:
                if getattr(g, '_in_combat_zone', None) is None:
                    zone.add_general(g, side)

    def _estimate_formation_depth(self, squad):
        """Estimate how many rows deep a formation is (for punch-through check)."""
        alive = squad.alive_soldiers
        if len(alive) <= 1:
            return 1
        # Use facing angle to determine front-back axis
        cos_f = math.cos(squad.facing_angle)
        sin_f = math.sin(squad.facing_angle)
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
                          start_x - 50, BATTLE_MAP_HEIGHT // 2,
                          player_class=gen_data.get("player_class"))
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

    def _deploy_companions(self, companions):
        """Deploy companion heroes as additional player generals."""
        legacy_companions = [
            companion.to_legacy_dict() if hasattr(companion, "to_legacy_dict") else companion
            for companion in companions
        ]
        battle_runtime.deploy_companions(self, legacy_companions)

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
            # Spell targeting: G to toggle, Tab to cycle spell slot, Escape to cancel
            elif event.key == pygame.K_g:
                self._toggle_spell_targeting()
            elif event.key == pygame.K_TAB:
                self._cycle_spell_slot()
            elif event.key == pygame.K_ESCAPE:
                self._cancel_spell_targeting()

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
        battle_input.handle_ability_key(self, key)

    # ── Spell Targeting ─────────────────────────────────────────────

    def _get_spell_caster(self):
        """Return the currently selected spell-capable entity, or None."""
        if self.selected_general and self.selected_general.available_spells:
            return self.selected_general
        if len(self.selected_squads) == 1 and self.selected_squads[0].available_spells:
            return self.selected_squads[0]
        return None

    def _toggle_spell_targeting(self):
        """Toggle spell targeting mode for the selected caster."""
        caster = self._get_spell_caster()
        if not caster:
            return
        if caster._spell_targeting:
            caster._spell_targeting = False
            caster._spell_targeting_spell = None
        else:
            spells = caster.available_spells
            if spells:
                idx = caster._selected_spell_index
                if idx >= len(spells):
                    idx = 0
                spell = spells[idx]
                caster._spell_targeting = True
                caster._spell_targeting_spell = spell
                get_audio().play("click")

    def _cycle_spell_slot(self):
        """Cycle through spell slots on the selected caster."""
        caster = self._get_spell_caster()
        if not caster:
            return
        spells = caster.available_spells
        if not spells:
            return
        caster._selected_spell_index = (caster._selected_spell_index + 1) % len(spells)
        if caster._spell_targeting:
            caster._spell_targeting_spell = spells[caster._selected_spell_index]

    def _cancel_spell_targeting(self):
        """Cancel spell targeting mode."""
        caster = self._get_spell_caster()
        if caster and caster._spell_targeting:
            caster._spell_targeting = False
            caster._spell_targeting_spell = None

    def _try_spell_cast(self, wx, wy):
        """Attempt to cast spell at world position. Returns True if cast happened."""
        caster = self._get_spell_caster()
        if not caster or not caster._spell_targeting or not caster._spell_targeting_spell:
            return False

        spell = caster._spell_targeting_spell

        # Check range
        d = distance(caster.x, caster.y, wx, wy)
        if d > spell.range_distance:
            return False  # out of range, don't consume the click

        # Find target squad at position (for unit-targeted spells)
        target_squad = None
        if spell.targeting == "unit" or spell.effect_type == "damage":
            for sq in self.enemy_squads:
                if sq.is_destroyed:
                    continue
                bbox = sq.get_bounding_box()
                if point_in_rect(wx, wy, *bbox):
                    target_squad = sq
                    break

        # Cast based on entity type
        from battle.squad import Squad
        if isinstance(caster, Squad):
            success = caster.cast_spell(spell, target_squad=target_squad,
                                        target_pos=(wx, wy),
                                        all_squads=self.all_squads)
        else:
            # General
            success = caster.cast_spell(spell, target_squad=target_squad,
                                        target_pos=(wx, wy),
                                        friendly_squads=self.player_squads,
                                        enemy_squads=self.enemy_squads)
        if success:
            get_audio().play("ability")
            # Exit targeting mode after cast
            caster._spell_targeting = False
            caster._spell_targeting_spell = None
        return success

    def _handle_left_click(self, pos):
        battle_input.handle_left_click(self, pos)

    def _finish_box_select(self, pos):
        battle_input.finish_box_select(self, pos)

    def _handle_deployment_event(self, event):
        """Handle input during deployment phase."""
        battle_input.handle_deployment_event(self, event)

    def _draw_deployment(self, surface):
        """Draw deployment zone and instructions."""
        battle_input.draw_deployment(self, surface)

    def _apply_facing_from_drag(self, release_pos):
        """Set selected squads' facing based on right-click drag direction."""
        battle_input.apply_facing_from_drag(self, release_pos)

    def _handle_right_click(self, pos):
        battle_input.handle_right_click(self, pos)

    def update(self):
        battle_runtime.update_battle(self)

    def _tick(self):
        battle_runtime.tick_battle(self)

    def _enemy_ai(self):
        """Delegate to AIEngine if wired, otherwise no-op."""
        if self._combat_engine is not None and self._combat_engine.ai_engine is not None:
            # AIEngine is already called from CombatEngine.step() — no double dispatch
            return
        # Fallback: no engine wired, use AIEngine directly if available
        if hasattr(self, '_ai_engine') and self._ai_engine is not None:
            self._ai_engine.update(
                self.all_squads, self.player_generals, self.enemy_generals)

    def draw(self, surface):
        # D1: Terrain-specific background colors
        bg_colors = {
            "plains": (90, 140, 60),
            "forest": (60, 110, 45),
            "mountain": (110, 105, 80),
            "desert": (195, 175, 130),
            "coastal": (90, 140, 60),
        }
        grid_colors = {
            "plains": (80, 130, 55),
            "forest": (50, 100, 40),
            "mountain": (100, 95, 72),
            "desert": (180, 160, 120),
            "coastal": (80, 130, 55),
        }
        # D2: Season tinting
        bg = bg_colors.get(self.terrain_type, (90, 140, 60))
        if self.season == SEASON_WINTER:
            # Whiten the background slightly for snow
            bg = (min(255, bg[0] + 40), min(255, bg[1] + 40), min(255, bg[2] + 50))
        elif self.season == SEASON_AUTUMN:
            # Warmer/browner tones
            bg = (min(255, bg[0] + 20), bg[1], max(0, bg[2] - 10))
        surface.fill(bg)

        grid_color = grid_colors.get(self.terrain_type, (80, 130, 55))
        grid_size = 100
        for x in range(0, BATTLE_MAP_WIDTH, grid_size):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, BATTLE_MAP_HEIGHT)
            pygame.draw.line(surface, grid_color, start, end, 1)
        for y in range(0, BATTLE_MAP_HEIGHT, grid_size):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(BATTLE_MAP_WIDTH, y)
            pygame.draw.line(surface, grid_color, start, end, 1)

        for t in self.terrain:
            rx, ry, rw, rh = t["rect"]
            screen_pos = self.camera.world_to_screen(rx, ry)
            w = self.camera.scale(rw)
            h = self.camera.scale(rh)
            pygame.draw.rect(surface, t["color"], (*screen_pos, w, h))
            # D1: Water gets wave lines
            if t["type"] == "water" and self.camera.zoom > 0.3:
                for wy in range(int(screen_pos[1]), int(screen_pos[1] + h), max(1, int(self.camera.scale(40)))):
                    pygame.draw.line(surface, (60, 100, 170),
                                     (int(screen_pos[0]), wy),
                                     (int(screen_pos[0] + w), wy), 1)
            if self.camera.zoom > 0.4:
                font = get_font(16)
                text = font.render(t["type"].title(), True, (200, 200, 200))
                surface.blit(text, (screen_pos[0] + 5, screen_pos[1] + 5))

        # Draw fog overlay behind enemy units
        if self.fog_enabled:
            self._draw_fog(surface)

        for sq in self.all_squads:
            if not sq.is_destroyed:
                fog_hidden = (sq.team != 0 and not sq.visible and self.fog_enabled)
                sq.draw(surface, self.camera, fog_hidden=fog_hidden)

        # Draw active combat zone effects (dust, sparks, swing arcs)
        for zone in self.combat_zones:
            if zone.active:
                zone.draw(surface, self.camera)

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
                eng_font = get_font(16)
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

        # General targeting indicator (move waypoint, attack target, or duel).
        if self.selected_general and self.selected_general.alive:
            g = self.selected_general
            gsx, gsy = self.camera.world_to_screen(g.x, g.y)

            # Duel indicator (highest priority) — red line to duel opponent
            if getattr(g, "duel_opponent", None) and g.duel_opponent.alive:
                osx, osy = self.camera.world_to_screen(g.duel_opponent.x, g.duel_opponent.y)
                duel_color = (255, 50, 50, 180)
                pygame.draw.line(target_surf, duel_color, (int(gsx), int(gsy)), (int(osx), int(osy)), 2)
                pygame.draw.circle(target_surf, duel_color, (int(osx), int(osy)), 12, 2)
                # Crossed-swords icon: two small X lines at midpoint
                mx, my = (gsx + osx) / 2, (gsy + osy) / 2
                pygame.draw.line(target_surf, (255, 220, 60, 200),
                                 (int(mx - 6), int(my - 6)), (int(mx + 6), int(my + 6)), 2)
                pygame.draw.line(target_surf, (255, 220, 60, 200),
                                 (int(mx + 6), int(my - 6)), (int(mx - 6), int(my + 6)), 2)
            # Attack target -> squad center marker
            elif getattr(g, "target_squad", None) and not g.target_squad.is_destroyed:
                tx, ty = g.target_squad.center
                tsx, tsy = self.camera.world_to_screen(tx, ty)
                gcolor = (100, 200, 255, 120) if g.team == 0 else (255, 80, 80, 90)
                pygame.draw.line(target_surf, gcolor, (int(gsx), int(gsy)), (int(tsx), int(tsy)), 2)
                pygame.draw.circle(target_surf, gcolor, (int(tsx), int(tsy)), 6, 0)
            # Move order -> waypoint marker
            else:
                dx = g.target_x - g.x
                dy = g.target_y - g.y
                if dx * dx + dy * dy > 25:  # ~5 units threshold
                    tsx, tsy = self.camera.world_to_screen(g.target_x, g.target_y)
                    gcolor = (200, 200, 100, 95)
                    pygame.draw.line(target_surf, gcolor, (int(gsx), int(gsy)), (int(tsx), int(tsy)), 2)
                    pygame.draw.circle(target_surf, gcolor, (int(tsx), int(tsy)), 6, 0)

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
        return battle_ui.make_button(x, y, w, h, text, active=active, enabled=enabled)

    def _draw_button(self, surface, btn, font):
        """Draw a single UI button."""
        return battle_ui.draw_button(surface, btn, font)

    def _point_in_button(self, pos, btn):
        return battle_ui.point_in_button(pos, btn)

    def _handle_ui_click(self, pos):
        """Handle clicks on bottom panel UI buttons. Returns True if handled."""
        return battle_ui.handle_ui_click(self, pos)

    def _on_ui_button_click(self, btn_id):
        """Handle a UI button being clicked."""
        battle_ui.on_ui_button_click(self, btn_id)

    def _on_unit_card_click(self, index):
        """Select a player squad by clicking its unit card."""
        battle_ui.on_unit_card_click(self, index)

    def _draw_hud(self, surface):
        battle_ui.draw_hud(self, surface)

    def _draw_unit_cards(self, surface, panel_y, small_font, btn_font):
        """Draw clickable unit cards along the bottom of the screen."""
        battle_ui.draw_unit_cards(self, surface, panel_y, small_font, btn_font)

    def _draw_selection_panel(self, surface, font, small_font, btn_font, panel_y):
        """Draw selected unit info with clickable stance/mode buttons."""
        battle_ui.draw_selection_panel(self, surface, font, small_font, btn_font, panel_y)

    def _draw_general_panel(self, surface, font, small_font, btn_font, panel_y):
        battle_ui.draw_general_panel(self, surface, font, small_font, btn_font, panel_y)

    def _draw_result_banner(self, surface):
        battle_ui.draw_result_banner(self, surface)
