"""Battle scene - handles the real-time tactical combat."""

import math
import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT,
    TEAM_COLORS, TEAM_COLORS_LIGHT, GREEN, DARK_GREEN, SAND, BROWN,
    BLACK, WHITE, GREY, GOLD, YELLOW, ORANGE,
    EXHAUSTION_MAX,
    HILL_RANGED_BONUS, HILL_CHARGE_DOWNHILL_BONUS, HILL_SPEED_UPHILL_PENALTY,
    FOREST_CAVALRY_SPEED_MULT, FOREST_RANGED_ACCURACY_MULT, FOREST_MELEE_DEFENSE_BONUS,
    VISION_INFANTRY, VISION_CAVALRY, FOG_ALPHA,
    WEATHER_TYPES, WEATHER_RAIN_ACCURACY, WEATHER_RAIN_EXHAUSTION,
    WEATHER_FOG_VISION, WEATHER_MUD_SPEED, WEATHER_MUD_CHARGE,
    WEATHER_WIND_ACCURACY,
)
from core.camera import Camera
from core.utils import distance, point_in_rect
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
            # Ability hotkeys: Q, W, E, R
            elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r):
                self._handle_ability_key(event.key)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.selecting:
                self._finish_box_select(event.pos)

        if event.type == pygame.MOUSEMOTION and self.selecting:
            self.select_end = event.pos

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

        if target_general and self.selected_general:
            self.selected_general.challenge_duel(target_general)
            return

        if self.selected_squads:
            if target_squad:
                for sq in self.selected_squads:
                    sq.give_attack_order(target_squad)
            else:
                count = len(self.selected_squads)
                for i, sq in enumerate(self.selected_squads):
                    offset_y = (i - count / 2.0) * 60
                    sq.give_move_order(wx, wy + offset_y)

        if self.selected_general and not target_general:
            self.selected_general.give_move_order(wx, wy)

    def update(self):
        if self.paused:
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

        # Track kills for XP
        for g in self.all_generals:
            if g.alive and g.kills > 0:
                new_kills = g.kills
                if not hasattr(g, '_prev_kills'):
                    g._prev_kills = 0
                gained = new_kills - g._prev_kills
                if gained > 0:
                    g.gain_xp(gained)
                    g._prev_kills = new_kills

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

        # Weather particles on top
        self._draw_weather(surface)

        self._draw_hud(surface)

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

    def _draw_hud(self, surface):
        font = pygame.font.SysFont(None, 20)
        small_font = pygame.font.SysFont(None, 16)

        # Top bar
        bar_surf = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 160))
        surface.blit(bar_surf, (0, 0))

        minutes = self.battle_timer // (60 * 60)
        seconds = (self.battle_timer // 60) % 60
        timer_text = font.render(f"Battle: {minutes:02d}:{seconds:02d}", True, WHITE)
        surface.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 8))

        speed_text = font.render(f"Speed: {self.speed_multiplier}x", True, YELLOW)
        surface.blit(speed_text, (SCREEN_WIDTH // 2 + 100, 8))

        if self.weather != "clear":
            weather_colors = {
                "rain": (100, 150, 255), "fog": (180, 180, 200),
                "mud": (160, 120, 60), "wind": (180, 200, 160),
            }
            wc = weather_colors.get(self.weather, WHITE)
            w_text = font.render(f"Weather: {self.weather.title()}", True, wc)
            surface.blit(w_text, (SCREEN_WIDTH // 2 - 250, 8))

        if self.paused:
            pause_text = font.render("PAUSED", True, YELLOW)
            surface.blit(pause_text, (SCREEN_WIDTH // 2 - 150, 8))

        p_alive = sum(sq.alive_count for sq in self.player_squads)
        e_alive = sum(sq.alive_count for sq in self.enemy_squads)
        p_text = font.render(f"Your Army: {p_alive}", True, TEAM_COLORS_LIGHT[0])
        e_text = font.render(f"Enemy Army: {e_alive}", True, TEAM_COLORS_LIGHT[1])
        surface.blit(p_text, (10, 8))
        surface.blit(e_text, (SCREEN_WIDTH - e_text.get_width() - 10, 8))

        if self.selected_squads:
            self._draw_selection_panel(surface, font, small_font)
        elif self.selected_general:
            self._draw_general_panel(surface, font, small_font)

        help_y = SCREEN_HEIGHT - 24
        help_text = small_font.render(
            "[SPACE] Pause  [1/2/3] Speed  [F] Fire  [V] Fog  [Q/W/E/R] Abilities  "
            "[Ctrl+1-5] Formation  [LMB] Select  [RMB] Order",
            True, (180, 180, 180))
        surface.blit(help_text, (10, help_y))

        if self.result != BattleResult.ONGOING:
            self._draw_result_banner(surface)

    def _draw_selection_panel(self, surface, font, small_font):
        panel_h = 80 + len(self.selected_squads) * 35
        panel_surf = pygame.Surface((340, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - panel_h - 30))

        y = SCREEN_HEIGHT - panel_h - 25
        header = font.render("Selected Units:", True, WHITE)
        surface.blit(header, (10, y))
        y += 22
        for sq in self.selected_squads:
            state_str = sq.state.upper()
            info = (f"{sq.unit_stats.name}: {sq.alive_count}/{sq.initial_count} "
                    f"[{state_str}] Morale:{int(sq.morale)}%")
            text = small_font.render(info, True, TEAM_COLORS_LIGHT[sq.team])
            surface.blit(text, (15, y))
            y += 16
            # Second line: exhaustion + weapon stats
            ws = sq.unit_stats.weapon_strength
            ap = sq.unit_stats.armor_penetration
            extra = f"  {sq.exhaustion_display} | WS:{ws} AP:{ap}%"
            if sq.unit_stats.ranged_strength > 0:
                extra += f" RS:{sq.unit_stats.ranged_strength} RAP:{sq.unit_stats.ranged_armor_penetration}%"
            if sq.is_braced:
                extra += " [BRACED]"
            text2 = small_font.render(extra, True, (160, 160, 160))
            surface.blit(text2, (15, y))
            y += 19

    def _draw_general_panel(self, surface, font, small_font):
        g = self.selected_general
        num_abilities = len(g.available_abilities)
        panel_h = 120 + num_abilities * 22
        panel_surf = pygame.Surface((340, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        surface.blit(panel_surf, (0, SCREEN_HEIGHT - panel_h - 30))

        y = SCREEN_HEIGHT - panel_h - 25
        header = font.render(f"{g.name} ({g.general_type}) Lv{g.level}", True, GOLD)
        surface.blit(header, (10, y))
        y += 22
        hp = small_font.render(f"HP: {int(g.health)}/{int(g.max_health)}  XP to next: {g.xp_to_next}", True, WHITE)
        surface.blit(hp, (15, y))
        y += 18
        stats = small_font.render(
            f"ATK:{g.melee_attack} DEF:{g.melee_defense} WS:{g.unit_stats.weapon_strength} "
            f"AP:{g.unit_stats.armor_penetration}%",
            True, WHITE)
        surface.blit(stats, (15, y))
        y += 18
        kills_text = small_font.render(
            f"Kills:{g.kills} Duels Won:{g.duels_won}", True, WHITE)
        surface.blit(kills_text, (15, y))
        y += 18

        if g.duel_state == DuelState.ACTIVE:
            duel_text = small_font.render(
                f"DUELING {g.duel_opponent.name}! Score: {g.duel_score}-{g.duel_opponent.duel_score}",
                True, GOLD)
            surface.blit(duel_text, (15, y))
            y += 18

        # Abilities
        y += 4
        keys = ["Q", "W", "E", "R"]
        for i, ability in enumerate(g.available_abilities):
            if i >= 4:
                break
            cd_text = ""
            if not ability.ready:
                cd_secs = ability.cooldown // 60
                cd_text = f" ({cd_secs}s)"
            color = WHITE if ability.ready else (100, 100, 100)
            text = small_font.render(
                f"[{keys[i]}] {ability.name}{cd_text} - {ability.description[:40]}",
                True, color)
            surface.blit(text, (15, y))
            y += 20

        # Show locked abilities
        for i, ability in enumerate(g.abilities):
            if ability.level_required > g.level:
                text = small_font.render(
                    f"  Lv{ability.level_required}: {ability.name} (Locked)",
                    True, (80, 80, 80))
                surface.blit(text, (15, y))
                y += 18

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
