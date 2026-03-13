"""Squad - a group of soldiers that moves and fights as a unit."""

import math
import random
import pygame
from core.settings import (
    SOLDIER_SPACING, MELEE_RANGE, SOLDIER_RADIUS,
    MORALE_BREAK_THRESHOLD, MORALE_ROUT_THRESHOLD,
    MORALE_RECOVERY_RATE, MORALE_DAMAGE_LOSS, MORALE_CASUALTY_LOSS,
    CHARGE_BONUS_DISTANCE, TEAM_COLORS, TEAM_COLORS_LIGHT,
    FLANK_ANGLE_THRESHOLD, REAR_ANGLE_THRESHOLD,
    FLANK_DAMAGE_BONUS, REAR_DAMAGE_BONUS,
    REAR_CHARGE_MORALE_SHOCK, FLANK_MORALE_SHOCK,
    EXHAUSTION_MAX, EXHAUSTION_IDLE_RATE, EXHAUSTION_MOVE_RATE,
    EXHAUSTION_WALK_RATE, EXHAUSTION_MARCH_RATE,
    EXHAUSTION_FIGHT_RATE, EXHAUSTION_CHARGE_RATE,
    EXHAUSTION_MORALE_THRESHOLD, EXHAUSTION_MORALE_DRAIN,
    EXHAUSTION_SPEED_PENALTY,
    BRACE_CHARGE_MORALE_SHOCK, BRACE_MIN_IDLE_FRAMES,
    FORMATION_LOOSE_SPACING_MULT,
    VISION_INFANTRY, VISION_CAVALRY, VISION_HILL_BONUS,
    MOVE_MODE_WALK, MOVE_MODE_MARCH, MOVE_MODE_RUN,
    WALK_SPEED_MULT, MARCH_SPEED_MULT,
    RUN_SPEED_MULT_INFANTRY, RUN_SPEED_MULT_CAVALRY,
    COLLISION_ENGAGE_RADIUS,
)
from core.utils import distance, angle_between, normalize, clamp
from battle.soldier import Soldier


class Formation:
    LINE = "line"         # default: wide, shallow
    COLUMN = "column"     # deep, narrow: +20% charge bonus
    SQUARE = "square"     # dense block: +30% vs cavalry, immune to rear, -25% speed
    LOOSE = "loose"       # spread out: -40% ranged damage taken, -20% melee defense
    WEDGE = "wedge"       # V-shape: +40% charge bonus, -15% defense

    # (charge_mult, defense_mult, speed_mult, ranged_damage_taken_mult, rear_immune)
    MODIFIERS = {
        "line":   (1.0, 1.0, 1.0, 1.0, False),
        "column": (1.2, 1.0, 1.0, 1.0, False),
        "square": (1.0, 1.3, 0.75, 0.85, True),
        "loose":  (1.0, 0.8, 1.0, 0.6, False),
        "wedge":  (1.4, 0.85, 1.05, 1.0, False),
    }


class SquadState:
    IDLE = "idle"
    MOVING = "moving"
    CHARGING = "charging"
    FIGHTING = "fighting"
    FIRING = "firing"
    BROKEN = "broken"
    ROUTED = "routed"


class Squad:
    def __init__(self, unit_stats, team, x, y, facing_angle=0.0, soldier_count=None,
                 vet_data=None):
        self.unit_stats = unit_stats
        self.team = team
        self.x = x
        self.y = y
        self.facing_angle = facing_angle
        self.target_x = x
        self.target_y = y
        self.state = SquadState.IDLE
        self.morale = 100.0  # vet morale bonus applied after vet_data is set
        self.selected = False
        self.target_squad = None
        self.is_cavalry = unit_stats.speed >= 3.5
        self.is_ranged = unit_stats.ranged_attack > 0 and unit_stats.range_distance > 0
        self.is_spear = unit_stats.can_brace
        self.fire_at_will = True
        self.charging = False
        self.charge_timer = 0
        self.formation = Formation.LINE

        # Movement mode (walk/march/run)
        self.movement_mode = MOVE_MODE_MARCH

        # Stances
        self.defensive_stance = False    # hold position, engage nearby only
        self.skirmish_stance = False     # ranged: retreat from approaching enemies
        self.defensive_anchor_x = x     # position to return to in defensive stance
        self.defensive_anchor_y = y

        # Veterancy modifiers
        self.vet_data = vet_data or {}
        self.vet_atk_mult = self.vet_data.get("atk_mult", 1.0)
        self.vet_def_mult = self.vet_data.get("def_mult", 1.0)
        self.vet_morale_bonus = self.vet_data.get("morale_bonus", 0)
        self.vet_exhaustion_mult = self.vet_data.get("exhaustion_mult", 1.0)
        self.vet_rank_name = self.vet_data.get("rank_name", "Raw")
        self.vet_rank_index = self.vet_data.get("rank_index", 0)

        # Exhaustion
        self.exhaustion = 0.0
        self.idle_frames = 0  # how long we've been standing still

        # Flanking state (set each frame for display)
        self.being_flanked = False
        self.being_rear_charged = False
        self.is_braced = False

        # Fog of war visibility (set each frame by battle scene)
        self.visible = True

        # Visual effects (slash lines, projectiles)
        self.visual_effects = []
        # Recently dead soldiers for death animation
        self._dying_soldiers = []

        # Terrain modifiers (set each frame by battle scene)
        self.terrain_mods = {
            "speed_mult": 1.0, "ranged_accuracy_mult": 1.0,
            "ranged_damage_mult": 1.0, "melee_defense_mult": 1.0,
            "charge_mult": 1.0, "terrain_type": None,
        }

        # Create soldiers in formation (use custom count for understrength squads)
        self.soldiers = []
        actual_count = soldier_count if soldier_count is not None else unit_stats.squad_size
        self._create_formation(unit_stats, actual_count)

        # Track for morale
        self.initial_count = len(self.soldiers)
        self.kills = 0

    def _create_formation(self, stats, count=None):
        if count is None:
            count = stats.squad_size
        offsets = self._compute_formation_offsets(count, self.formation)
        for ox, oy in offsets:
            sx = self.x + ox
            sy = self.y + oy
            soldier = Soldier(sx, sy, stats, self.team)
            soldier.formation_x = ox
            soldier.formation_y = oy
            self.soldiers.append(soldier)

    def _compute_formation_offsets(self, count, formation):
        """Compute (ox, oy) offsets for each soldier in the given formation."""
        spacing = SOLDIER_SPACING
        if formation == Formation.LOOSE:
            spacing *= FORMATION_LOOSE_SPACING_MULT

        if formation == Formation.WEDGE:
            return self._wedge_offsets(count, spacing)

        # Grid-based formations
        if formation == Formation.LINE:
            cols = max(1, int(math.sqrt(count * 2)))
        elif formation == Formation.COLUMN:
            cols = max(1, int(math.sqrt(count * 0.3)))
        elif formation == Formation.SQUARE:
            cols = max(1, int(math.sqrt(count)))
        else:  # loose or default
            cols = max(1, int(math.sqrt(count * 2)))

        offsets = []
        rows = math.ceil(count / cols)
        for i in range(count):
            row = i // cols
            col = i % cols
            ox = (col - cols / 2.0 + 0.5) * spacing
            oy = (row - rows / 2.0 + 0.5) * spacing
            offsets.append((ox, oy))
        return offsets

    def _wedge_offsets(self, count, spacing):
        """V-shape wedge formation."""
        offsets = [(0, 0)]  # leader at tip
        row = 1
        placed = 1
        while placed < count:
            for side in [-1, 1]:
                if placed >= count:
                    break
                ox = side * row * spacing * 0.7
                oy = row * spacing * 0.8
                offsets.append((ox, oy))
                placed += 1
            row += 1
        return offsets

    def _reposition_formation(self):
        """Recompute formation offsets for living soldiers."""
        alive = self.alive_soldiers
        offsets = self._compute_formation_offsets(len(alive), self.formation)
        for s, (ox, oy) in zip(alive, offsets):
            s.formation_x = ox
            s.formation_y = oy

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers if s.alive]

    @property
    def alive_count(self):
        return sum(1 for s in self.soldiers if s.alive)

    @property
    def is_destroyed(self):
        return self.alive_count == 0

    @property
    def center(self):
        alive = self.alive_soldiers
        if not alive:
            return (self.x, self.y)
        cx = sum(s.x for s in alive) / len(alive)
        cy = sum(s.y for s in alive) / len(alive)
        return (cx, cy)

    @property
    def exhaustion_display(self):
        if self.exhaustion < 20:
            return "Fresh"
        elif self.exhaustion < 40:
            return "Winded"
        elif self.exhaustion < 60:
            return "Tired"
        elif self.exhaustion < 80:
            return "Exhausted"
        else:
            return "Spent"

    @property
    def formation_mods(self):
        return Formation.MODIFIERS.get(self.formation, (1.0, 1.0, 1.0, 1.0, False))

    @property
    def vision_radius(self):
        """Vision range for fog of war."""
        base = VISION_CAVALRY if self.is_cavalry else VISION_INFANTRY
        if self.is_ranged:
            base = max(base, self.unit_stats.range_distance)
        # Hills grant bonus vision
        if self.terrain_mods.get("terrain_type") == "hill":
            base *= VISION_HILL_BONUS
        return base

    @property
    def movement_speed_mult(self):
        """Speed multiplier from current movement mode."""
        if self.movement_mode == MOVE_MODE_WALK:
            return WALK_SPEED_MULT
        elif self.movement_mode == MOVE_MODE_RUN:
            return RUN_SPEED_MULT_CAVALRY if self.is_cavalry else RUN_SPEED_MULT_INFANTRY
        return MARCH_SPEED_MULT

    @property
    def effective_speed(self):
        """Speed reduced by exhaustion, terrain, formation, and movement mode."""
        penalty = (self.exhaustion / EXHAUSTION_MAX) * EXHAUSTION_SPEED_PENALTY
        base = self.unit_stats.speed * (1.0 - penalty)
        _, _, speed_mult, _, _ = self.formation_mods
        return base * self.terrain_mods.get("speed_mult", 1.0) * speed_mult * self.movement_speed_mult

    def _spawn_slash_effect(self, sx, sy, tx, ty):
        """Add a melee slash visual effect."""
        self.visual_effects.append({
            "type": "slash", "sx": sx, "sy": sy, "tx": tx, "ty": ty,
            "timer": 6, "max_timer": 6,
        })

    def _spawn_projectile_effect(self, sx, sy, tx, ty):
        """Add a ranged projectile visual effect."""
        self.visual_effects.append({
            "type": "projectile", "sx": sx, "sy": sy, "tx": tx, "ty": ty,
            "timer": 12, "max_timer": 12,
        })

    def _update_effects(self):
        """Tick down visual effects and remove expired ones."""
        for e in self.visual_effects:
            e["timer"] -= 1
        self.visual_effects = [e for e in self.visual_effects if e["timer"] > 0]
        # Update dying soldiers
        self._dying_soldiers = [s for s in self._dying_soldiers if s.death_timer > 0]

    def set_formation(self, formation):
        """Change formation and reposition soldiers."""
        self.formation = formation
        self._reposition_formation()

    def compute_flank_multiplier(self, attacker_squad):
        """Determine flank/rear bonus based on angle of attack."""
        if not attacker_squad:
            return 1.0
        _, _, _, _, rear_immune = self.formation_mods
        ax, ay = attacker_squad.center
        mx, my = self.center
        attack_angle = angle_between(mx, my, ax, ay)
        angle_diff = abs(attack_angle - self.facing_angle)
        while angle_diff > math.pi:
            angle_diff = abs(angle_diff - 2 * math.pi)
        if angle_diff >= REAR_ANGLE_THRESHOLD:
            if rear_immune:
                return FLANK_DAMAGE_BONUS  # square downgrades rear to flank
            return REAR_DAMAGE_BONUS
        elif angle_diff >= FLANK_ANGLE_THRESHOLD:
            return FLANK_DAMAGE_BONUS
        return 1.0

    def is_bracing(self):
        """Check if this squad can brace against a charge."""
        return (self.is_spear and
                self.state == SquadState.IDLE and
                self.idle_frames >= BRACE_MIN_IDLE_FRAMES)

    def give_move_order(self, tx, ty, movement_mode=None):
        self.target_x = tx
        self.target_y = ty
        self.target_squad = None
        self.state = SquadState.MOVING
        self.facing_angle = angle_between(self.x, self.y, tx, ty)
        self.idle_frames = 0
        if movement_mode is not None:
            self.movement_mode = movement_mode

    def give_attack_order(self, target_squad):
        self.target_squad = target_squad
        tx, ty = target_squad.center
        self.target_x = tx
        self.target_y = ty
        dist = distance(self.x, self.y, tx, ty)
        if self.is_ranged and dist <= self.unit_stats.range_distance:
            self.state = SquadState.FIRING
        else:
            self.state = SquadState.CHARGING
            self.charging = True
            self.charge_timer = 0
            self.movement_mode = MOVE_MODE_RUN  # charging always runs
        self.idle_frames = 0

    def update(self, all_squads):
        if self.is_destroyed:
            return

        # Update individual soldiers and sync facing angle
        for s in self.alive_soldiers:
            s.update()
            s.facing_angle = self.facing_angle

        # Exhaustion tick
        self._update_exhaustion()

        # Exhaustion morale drain
        if self.exhaustion > EXHAUSTION_MORALE_THRESHOLD:
            over = self.exhaustion - EXHAUSTION_MORALE_THRESHOLD
            drain = EXHAUSTION_MORALE_DRAIN * (over / 20.0)
            self.morale = max(0, self.morale - drain)

        # Morale recovery when idle (reduced by exhaustion)
        if self.state == SquadState.IDLE and self.morale < 100:
            recovery = MORALE_RECOVERY_RATE * (1.0 - self.exhaustion / EXHAUSTION_MAX * 0.5)
            self.morale = min(100, self.morale + recovery)

        # Track idle time for bracing
        if self.state == SquadState.IDLE:
            self.idle_frames += 1
        else:
            self.idle_frames = 0

        # Bracing state
        self.is_braced = self.is_bracing()

        # Reset flanking display flags
        self.being_flanked = False
        self.being_rear_charged = False

        # Handle routing
        if self.state == SquadState.ROUTED:
            self._do_rout()
            return
        if self.morale <= MORALE_ROUT_THRESHOLD:
            self.state = SquadState.ROUTED
            return
        if self.morale <= MORALE_BREAK_THRESHOLD and self.state != SquadState.BROKEN:
            self.state = SquadState.BROKEN
            self.target_x = self.x + math.cos(self.facing_angle + math.pi) * 200
            self.target_y = self.y + math.sin(self.facing_angle + math.pi) * 200

        if self.state == SquadState.BROKEN:
            self._do_movement(speed_mult=0.8)
            if self.morale > MORALE_BREAK_THRESHOLD + 10:
                self.state = SquadState.IDLE
            return

        # Auto-target if we lost our target
        if self.target_squad and self.target_squad.is_destroyed:
            self.target_squad = None
            self.state = SquadState.IDLE

        # Defensive stance: return to anchor if drifted and idle
        if self.defensive_stance and self.state == SquadState.IDLE:
            d = distance(self.x, self.y, self.defensive_anchor_x, self.defensive_anchor_y)
            if d > MELEE_RANGE * 4:
                self.give_move_order(self.defensive_anchor_x, self.defensive_anchor_y,
                                     movement_mode=MOVE_MODE_MARCH)

        # Defensive stance: auto-engage nearby enemies
        if self.defensive_stance and self.state == SquadState.IDLE:
            self._defensive_auto_engage(all_squads)

        # Skirmish stance: retreat from approaching enemies
        if self.skirmish_stance and self.is_ranged and self.state in (
                SquadState.IDLE, SquadState.FIRING):
            self._skirmish_retreat(all_squads)

        # Fire at will
        if self.is_ranged and self.fire_at_will and self.state == SquadState.IDLE:
            self._auto_acquire_ranged_target(all_squads)

        if self.state == SquadState.MOVING:
            self._do_movement()
        elif self.state == SquadState.CHARGING:
            self._do_charge()
        elif self.state == SquadState.FIRING:
            self._do_ranged(all_squads)
        elif self.state == SquadState.FIGHTING:
            self._do_melee()

        # Update visual effects
        self._update_effects()

        # Update squad position to center of living soldiers
        cx, cy = self.center
        self.x, self.y = cx, cy

    def _update_exhaustion(self):
        """Increase exhaustion based on current activity and movement mode."""
        rate = EXHAUSTION_IDLE_RATE
        if self.state == SquadState.MOVING:
            # Movement exhaustion depends on mode
            if self.movement_mode == MOVE_MODE_WALK:
                rate = EXHAUSTION_WALK_RATE
            elif self.movement_mode == MOVE_MODE_MARCH:
                rate = EXHAUSTION_MARCH_RATE
            else:
                rate = EXHAUSTION_MOVE_RATE
        elif self.state == SquadState.CHARGING:
            rate = EXHAUSTION_CHARGE_RATE
        elif self.state == SquadState.FIGHTING:
            rate = EXHAUSTION_FIGHT_RATE
        elif self.state == SquadState.FIRING:
            rate = EXHAUSTION_MARCH_RATE
        elif self.state == SquadState.BROKEN or self.state == SquadState.ROUTED:
            rate = EXHAUSTION_CHARGE_RATE  # fleeing is tiring

        # Apply unit-specific exhaustion rate multiplier and veterancy
        rate *= self.unit_stats.exhaustion_rate * self.vet_exhaustion_mult

        self.exhaustion = min(EXHAUSTION_MAX, self.exhaustion + rate)

        # Sync exhaustion to soldiers
        for s in self.alive_soldiers:
            s.exhaustion = self.exhaustion

    def _do_movement(self, speed_mult=1.0):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 5:
            self.state = SquadState.IDLE
            return
        nx, ny = normalize(dx, dy)
        speed = self.effective_speed * speed_mult
        for s in self.alive_soldiers:
            goal_x = self.target_x + s.formation_x
            goal_y = self.target_y + s.formation_y
            sdx = goal_x - s.x
            sdy = goal_y - s.y
            snx, sny = normalize(sdx, sdy)
            s.x += snx * speed
            s.y += sny * speed

    def _do_charge(self):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            self.charging = False
            return

        tx, ty = self.target_squad.center
        dist = distance(self.x, self.y, tx, ty)

        if dist < MELEE_RANGE * 2:
            # Impact! Check for spear bracing
            if self.target_squad.is_bracing() and self.is_cavalry:
                self._handle_brace_impact()
            else:
                # Apply flank/rear charge morale shock
                flank_mult = self.target_squad.compute_flank_multiplier(self)
                if flank_mult >= REAR_DAMAGE_BONUS:
                    self.target_squad.apply_morale_modifier(-REAR_CHARGE_MORALE_SHOCK)
                    self.target_squad.being_rear_charged = True
                elif flank_mult >= FLANK_DAMAGE_BONUS:
                    self.target_squad.apply_morale_modifier(-FLANK_MORALE_SHOCK)
                    self.target_squad.being_flanked = True

            self.state = SquadState.FIGHTING
            self.charge_timer = 30  # bonus frames
            return

        self.target_x = tx
        self.target_y = ty
        self.facing_angle = angle_between(self.x, self.y, tx, ty)
        charge_terrain = self.terrain_mods.get("charge_mult", 1.0)
        charge_form, _, _, _, _ = self.formation_mods
        speed_mult = (1.5 if self.is_cavalry else 1.2) * charge_terrain * charge_form
        self._do_movement(speed_mult=speed_mult)

    def _handle_brace_impact(self):
        """Spearmen brace deals counter-damage to charging cavalry."""
        bracing_soldiers = self.target_squad.alive_soldiers
        charging_soldiers = self.alive_soldiers

        # Each front-rank bracing soldier strikes a charging soldier
        hits = min(len(bracing_soldiers), len(charging_soldiers))
        for i in range(hits):
            dmg = bracing_soldiers[i].brace_counter_attack(charging_soldiers[i])
            if dmg > 0 and not charging_soldiers[i].alive:
                self.target_squad.kills += 1
                self.on_casualty()

        # Morale shock to the charging unit
        self.apply_morale_modifier(-BRACE_CHARGE_MORALE_SHOCK)

    def _do_melee(self):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            self.charging = False
            return

        is_charge = self.charge_timer > 0
        if self.charge_timer > 0:
            self.charge_timer -= 1

        # Compute flanking bonus for this engagement
        flank_mult = self.target_squad.compute_flank_multiplier(self)
        if flank_mult >= REAR_DAMAGE_BONUS:
            self.target_squad.being_rear_charged = True
        elif flank_mult >= FLANK_DAMAGE_BONUS:
            self.target_squad.being_flanked = True

        # Terrain + formation defense modifiers
        def_mult = self.target_squad.terrain_mods.get("melee_defense_mult", 1.0)
        _, target_def_form, _, _, _ = self.target_squad.formation_mods
        def_mult *= target_def_form

        for s in self.alive_soldiers:
            if s.attack_cooldown > 0:
                continue
            # Find nearest enemy soldier
            best = None
            best_dist = MELEE_RANGE * 3
            for es in self.target_squad.alive_soldiers:
                d = distance(s.x, s.y, es.x, es.y)
                if d < best_dist:
                    best_dist = d
                    best = es
            if best:
                if best_dist <= MELEE_RANGE:
                    vet_flank = flank_mult * self.vet_atk_mult
                    vet_def = def_mult * self.target_squad.vet_def_mult
                    dmg = s.attack(best, is_charging=is_charge,
                                   flank_mult=vet_flank,
                                   defense_terrain_mult=vet_def)
                    if dmg > 0:
                        self._spawn_slash_effect(s.x, s.y, best.x, best.y)
                        if not best.alive:
                            self.kills += 1
                            self.target_squad._dying_soldiers.append(best)
                            self.target_squad.on_casualty()
                else:
                    # Move toward enemy
                    nx, ny = normalize(best.x - s.x, best.y - s.y)
                    s.x += nx * self.effective_speed
                    s.y += ny * self.effective_speed

    def _do_ranged(self, all_squads):
        if not self.target_squad or self.target_squad.is_destroyed:
            self.state = SquadState.IDLE
            return
        tx, ty = self.target_squad.center
        dist = distance(self.x, self.y, tx, ty)
        max_range = self.unit_stats.range_distance
        if dist > max_range * 1.1:
            # Move to max range, not directly on top of the target
            dx, dy = tx - self.x, ty - self.y
            d = max(1, (dx * dx + dy * dy) ** 0.5)
            # Stop at 90% of max range (just within range)
            approach_dist = d - max_range * 0.9
            if approach_dist > 0:
                nx, ny = dx / d, dy / d
                self.target_x = self.x + nx * approach_dist
                self.target_y = self.y + ny * approach_dist
            self._do_movement()
            return
        if dist < MELEE_RANGE * 3:
            self.state = SquadState.FIGHTING
            return
        self.facing_angle = angle_between(self.x, self.y, tx, ty)
        ranged_dmg_mult = self.terrain_mods.get("ranged_damage_mult", 1.0) * self.vet_atk_mult
        ranged_acc_mult = self.terrain_mods.get("ranged_accuracy_mult", 1.0)
        # Target in forest also reduces accuracy
        target_terrain = self.target_squad.terrain_mods.get("terrain_type")
        if target_terrain == "forest":
            ranged_acc_mult *= 0.8  # harder to hit targets in forest
        for s in self.alive_soldiers:
            if s.attack_cooldown > 0:
                continue
            targets = self.target_squad.alive_soldiers
            if targets:
                target = random.choice(targets)
                # Spawn projectile regardless of hit
                self._spawn_projectile_effect(s.x, s.y, target.x, target.y)
                dmg = s.ranged_attack(target, accuracy_mult=ranged_acc_mult,
                                       damage_mult=ranged_dmg_mult)
                if dmg > 0 and not target.alive:
                    self.kills += 1
                    self.target_squad._dying_soldiers.append(target)
                    self.target_squad.on_casualty()

    def _auto_acquire_ranged_target(self, all_squads):
        best = None
        best_dist = self.unit_stats.range_distance
        for sq in all_squads:
            if sq.team == self.team or sq.is_destroyed:
                continue
            # Player squads can only auto-target visible enemies
            if self.team == 0 and not sq.visible:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < best_dist:
                best_dist = d
                best = sq
        if best:
            self.target_squad = best
            self.state = SquadState.FIRING

    def _defensive_auto_engage(self, all_squads):
        """In defensive stance, engage enemies within close range but don't chase far."""
        engage_range = MELEE_RANGE * 3
        for sq in all_squads:
            if sq.team == self.team or sq.is_destroyed:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < engage_range:
                self.give_attack_order(sq)
                return

    def _skirmish_retreat(self, all_squads):
        """Ranged units in skirmish stance retreat from approaching enemies."""
        flee_distance = self.unit_stats.range_distance * 0.7
        closest_enemy = None
        closest_dist = float('inf')
        for sq in all_squads:
            if sq.team == self.team or sq.is_destroyed:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < closest_dist:
                closest_dist = d
                closest_enemy = sq
        if closest_enemy and closest_dist < flee_distance:
            # Retreat away from enemy
            dx = self.x - closest_enemy.x
            dy = self.y - closest_enemy.y
            d = max(1, (dx * dx + dy * dy) ** 0.5)
            retreat_dist = flee_distance - closest_dist + 50
            retreat_x = self.x + (dx / d) * retreat_dist
            retreat_y = self.y + (dy / d) * retreat_dist
            # Clamp to map bounds
            from core.settings import BATTLE_MAP_WIDTH, BATTLE_MAP_HEIGHT
            retreat_x = max(50, min(BATTLE_MAP_WIDTH - 50, retreat_x))
            retreat_y = max(50, min(BATTLE_MAP_HEIGHT - 50, retreat_y))
            self.give_move_order(retreat_x, retreat_y, movement_mode=MOVE_MODE_RUN)
            # Cannot fire while running
            self.target_squad = None

    def _do_rout(self):
        angle = self.facing_angle + math.pi
        speed = self.effective_speed * 1.5
        for s in self.alive_soldiers:
            s.x += math.cos(angle) * speed + random.uniform(-0.5, 0.5)
            s.y += math.sin(angle) * speed + random.uniform(-0.5, 0.5)

    def on_casualty(self):
        ratio = self.alive_count / max(1, self.initial_count)
        self.morale -= MORALE_CASUALTY_LOSS + (1 - ratio) * 3

    def apply_morale_modifier(self, amount):
        self.morale = clamp(self.morale + amount, 0, 100)

    def reduce_exhaustion(self, amount):
        """Reduce exhaustion (used by general abilities)."""
        self.exhaustion = max(0, self.exhaustion - amount)
        for s in self.alive_soldiers:
            s.exhaustion = self.exhaustion

    def get_bounding_box(self):
        alive = self.alive_soldiers
        if not alive:
            return (self.x, self.y, 1, 1)
        min_x = min(s.x for s in alive)
        min_y = min(s.y for s in alive)
        max_x = max(s.x for s in alive)
        max_y = max(s.y for s in alive)
        padding = SOLDIER_SPACING
        return (min_x - padding, min_y - padding,
                max_x - min_x + padding * 2, max_y - min_y + padding * 2)

    def _draw_soldier_shape(self, surface, sx, sy, r, c, facing=None):
        """Draw a soldier with shape based on unit type, rotated by facing angle."""
        r = max(1, int(r))
        fa = facing if facing is not None else self.facing_angle
        if self.is_cavalry:
            # Larger elongated ellipse rotated to facing direction
            r_long = max(2, int(r * 1.6))
            r_short = max(1, int(r * 0.9))
            cos_a, sin_a = math.cos(fa), math.sin(fa)
            # 6-point approximation of an oriented ellipse
            pts = []
            for i in range(8):
                angle = i * math.pi * 2 / 8
                px = math.cos(angle) * r_long
                py = math.sin(angle) * r_short
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                pts.append((int(sx + rx), int(sy + ry)))
            pygame.draw.polygon(surface, c, pts)
        elif self.is_spear:
            # Diamond (rotated square) aligned to facing
            cos_a, sin_a = math.cos(fa), math.sin(fa)
            d = r + 1
            points = [
                (int(sx + cos_a * d), int(sy + sin_a * d)),       # front
                (int(sx - sin_a * d), int(sy + cos_a * d)),       # right
                (int(sx - cos_a * d), int(sy - sin_a * d)),       # back
                (int(sx + sin_a * d), int(sy - cos_a * d)),       # left
            ]
            pygame.draw.polygon(surface, c, points)
        elif self.is_ranged:
            # Triangle pointing toward facing direction
            cos_a, sin_a = math.cos(fa), math.sin(fa)
            tip_x = sx + cos_a * (r + 2)
            tip_y = sy + sin_a * (r + 2)
            left_x = sx + math.cos(fa + 2.4) * r
            left_y = sy + math.sin(fa + 2.4) * r
            right_x = sx + math.cos(fa - 2.4) * r
            right_y = sy + math.sin(fa - 2.4) * r
            points = [(int(tip_x), int(tip_y)),
                       (int(left_x), int(left_y)),
                       (int(right_x), int(right_y))]
            pygame.draw.polygon(surface, c, points)
        else:
            # Filled square for melee infantry, rotated to facing
            cos_a, sin_a = math.cos(fa), math.sin(fa)
            # Corners of a rotated square
            corners = []
            for cx_off, cy_off in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                px = cx_off * r
                py = cy_off * r
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                corners.append((int(sx + rx), int(sy + ry)))
            pygame.draw.polygon(surface, c, corners)

    def draw(self, surface, camera, fog_hidden=False):
        if fog_hidden:
            return
        color = TEAM_COLORS[self.team]
        light_color = TEAM_COLORS_LIGHT[self.team]

        # Draw dying soldiers (fade out)
        for s in self._dying_soldiers:
            sx, sy = camera.world_to_screen(s.x, s.y)
            r = max(1, int(camera.scale(SOLDIER_RADIUS) * s.death_alpha))
            alpha = int(255 * s.death_alpha)
            if r > 0 and alpha > 0:
                c = tuple(int(ch * 0.3) for ch in color)
                death_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(death_surf, (*c, alpha), (r, r), r)
                surface.blit(death_surf, (sx - r, sy - r))

        for s in self.alive_soldiers:
            sx, sy = camera.world_to_screen(s.x, s.y)
            r = camera.scale(SOLDIER_RADIUS)
            hp_ratio = s.health / s.max_health
            if s.hit_flash_timer > 0:
                c = (255, 255, 255)
            else:
                c = tuple(int(ch * (0.4 + 0.6 * hp_ratio)) for ch in color)
            self._draw_soldier_shape(surface, sx, sy, r, c, facing=s.facing_angle)

        # Draw visual effects (slashes and projectiles)
        for e in self.visual_effects:
            progress = 1.0 - e["timer"] / e["max_timer"]
            if e["type"] == "slash":
                # Short slash line from attacker toward target
                sx, sy = camera.world_to_screen(e["sx"], e["sy"])
                tx, ty = camera.world_to_screen(e["tx"], e["ty"])
                dx, dy = tx - sx, ty - sy
                d = max(1, (dx * dx + dy * dy) ** 0.5)
                nx, ny = dx / d, dy / d
                slash_len = camera.scale(12)
                ex = int(sx + nx * slash_len * progress)
                ey = int(sy + ny * slash_len * progress)
                alpha = int(255 * (1 - progress))
                slash_color = (255, 255, 200, alpha)
                slash_surf = pygame.Surface((abs(ex - int(sx)) + 6, abs(ey - int(sy)) + 6), pygame.SRCALPHA)
                # Draw on main surface directly with fading white
                fade = max(0, 255 - int(255 * progress))
                pygame.draw.line(surface, (255, 255, fade),
                                 (int(sx), int(sy)), (ex, ey), max(1, camera.scale(2)))
            elif e["type"] == "projectile":
                # Dot moving from source to target
                sx, sy = camera.world_to_screen(e["sx"], e["sy"])
                tx, ty = camera.world_to_screen(e["tx"], e["ty"])
                cx = int(sx + (tx - sx) * progress)
                cy = int(sy + (ty - sy) * progress)
                pr = max(1, camera.scale(2))
                pygame.draw.circle(surface, (200, 180, 100), (cx, cy), pr)
                # Trail
                trail_x = int(sx + (tx - sx) * max(0, progress - 0.15))
                trail_y = int(sy + (ty - sy) * max(0, progress - 0.15))
                pygame.draw.line(surface, (180, 160, 80),
                                 (trail_x, trail_y), (cx, cy), 1)

        # Braced indicator - spear icon (small lines pointing outward)
        if self.is_braced:
            cx, cy = self.center
            scx, scy = camera.world_to_screen(cx, cy)
            brace_r = camera.scale(30)
            brace_surf = pygame.Surface((brace_r * 2, brace_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(brace_surf, (200, 180, 60, 60), (brace_r, brace_r), brace_r)
            pygame.draw.circle(brace_surf, (200, 180, 60, 120), (brace_r, brace_r), brace_r, 2)
            surface.blit(brace_surf, (scx - brace_r, scy - brace_r))

        # Flanking/rear indicators
        if self.being_rear_charged:
            cx, cy = self.center
            scx, scy = camera.world_to_screen(cx, cy)
            if camera.zoom > 0.4:
                font = pygame.font.SysFont(None, max(12, camera.scale(13)))
                warn = font.render("REAR!", True, (255, 80, 80))
                surface.blit(warn, (scx - warn.get_width() // 2, scy + camera.scale(20)))
        elif self.being_flanked:
            cx, cy = self.center
            scx, scy = camera.world_to_screen(cx, cy)
            if camera.zoom > 0.4:
                font = pygame.font.SysFont(None, max(12, camera.scale(13)))
                warn = font.render("FLANKED!", True, (255, 160, 60))
                surface.blit(warn, (scx - warn.get_width() // 2, scy + camera.scale(20)))

        # Selection highlight
        if self.selected:
            bbox = self.get_bounding_box()
            screen_pos = camera.world_to_screen(bbox[0], bbox[1])
            w = camera.scale(bbox[2])
            h = camera.scale(bbox[3])
            pygame.draw.rect(surface, light_color, (*screen_pos, w, h), 2)

        # Bars above squad: morale + exhaustion
        cx, cy = self.center
        scx, scy = camera.world_to_screen(cx, cy)
        bar_w = camera.scale(40)
        bar_h = max(2, camera.scale(4))
        bar_x = scx - bar_w // 2

        # Exhaustion bar (orange, above morale)
        ex_bar_y = scy - camera.scale(30)
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, ex_bar_y, bar_w, bar_h))
        ex_w = int(bar_w * self.exhaustion / EXHAUSTION_MAX)
        ex_color = (60, 160, 60) if self.exhaustion < 30 else (
            (200, 160, 40) if self.exhaustion < 60 else (200, 80, 30))
        pygame.draw.rect(surface, ex_color, (bar_x, ex_bar_y, ex_w, bar_h))

        # Morale bar
        bar_y = scy - camera.scale(25)
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
        morale_w = int(bar_w * self.morale / 100)
        morale_color = (50, 200, 50) if self.morale > 50 else (
            (220, 200, 50) if self.morale > 25 else (200, 50, 50))
        pygame.draw.rect(surface, morale_color, (bar_x, bar_y, morale_w, bar_h))

        # Squad name and count
        if camera.zoom > 0.5:
            font = pygame.font.SysFont(None, max(12, camera.scale(14)))
            chevrons = ">" * self.vet_rank_index if self.vet_rank_index > 0 else ""
            label = f"{chevrons}{self.unit_stats.name} ({self.alive_count})"
            if self.state == SquadState.ROUTED:
                label += " ROUTED!"
            elif self.state == SquadState.BROKEN:
                label += " WAVERING"
            elif self.is_braced:
                label += " BRACED"
            # Movement mode indicator
            if self.state == SquadState.MOVING:
                mode_labels = {MOVE_MODE_WALK: "WALK", MOVE_MODE_MARCH: "MARCH",
                               MOVE_MODE_RUN: "RUN"}
                label += f" {mode_labels.get(self.movement_mode, '')}"
            # Stance indicators
            if self.defensive_stance:
                label += " [DEF]"
            if self.skirmish_stance:
                label += " [SKIRM]"
            if self.formation != Formation.LINE:
                label += f" <{self.formation.upper()}>"
            terrain_type = self.terrain_mods.get("terrain_type")
            if terrain_type:
                label += f" [{terrain_type.upper()}]"
            text = font.render(label, True, light_color)
            surface.blit(text, (scx - text.get_width() // 2, ex_bar_y - bar_h - 12))

        # Facing direction arrow (when selected)
        if self.selected:
            cx, cy = self.center
            scx, scy = camera.world_to_screen(cx, cy)
            arrow_len = camera.scale(25)
            ax = scx + math.cos(self.facing_angle) * arrow_len
            ay = scy + math.sin(self.facing_angle) * arrow_len
            pygame.draw.line(surface, (200, 200, 255),
                             (int(scx), int(scy)), (int(ax), int(ay)), 2)
            # Arrowhead
            head_len = camera.scale(8)
            for side in [-0.5, 0.5]:
                hx = ax - math.cos(self.facing_angle + side) * head_len
                hy = ay - math.sin(self.facing_angle + side) * head_len
                pygame.draw.line(surface, (200, 200, 255),
                                 (int(ax), int(ay)), (int(hx), int(hy)), 2)

        # Range indicator for ranged units (when selected)
        if self.selected and self.is_ranged:
            r = camera.scale(self.unit_stats.range_distance)
            if self.unit_stats.can_fire_while_moving:
                # Circle range for units that can fire while moving
                range_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(range_surf, (*light_color, 40), (r, r), r)
                pygame.draw.circle(range_surf, (*light_color, 80), (r, r), r, 1)
                surface.blit(range_surf, (scx - r, scy - r))
            else:
                # Cone range for stationary ranged units
                cone_half_angle = 0.5  # ~57 degrees total cone
                cone_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                cx_s, cy_s = r + 2, r + 2
                # Build cone polygon: center -> arc points -> center
                num_pts = 16
                pts = [(int(cx_s), int(cy_s))]
                for i in range(num_pts + 1):
                    a = self.facing_angle - cone_half_angle + (2 * cone_half_angle * i / num_pts)
                    px = cx_s + math.cos(a) * r
                    py = cy_s + math.sin(a) * r
                    pts.append((int(px), int(py)))
                pts.append((int(cx_s), int(cy_s)))
                pygame.draw.polygon(cone_surf, (*light_color, 35), pts)
                pygame.draw.lines(cone_surf, (*light_color, 80), True, pts, 1)
                surface.blit(cone_surf, (int(scx - r - 2), int(scy - r - 2)))
