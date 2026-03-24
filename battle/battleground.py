"""CombatZone: dynamic melee engagement zone between opposing squads.

Replaces the old Battleground with a system that pairs individual soldiers
in 1v1 duels, animates attack cycles, and implements assist/reinforcement
mechanics for a living, reactive skirmish line.
"""

import math
import random
import pygame
from core.utils import distance
from core.settings import (
    MELEE_RANGE, SOLDIER_SPACING,
    COMBAT_READY_FRAMES, COMBAT_SWING_FRAMES, COMBAT_SWING_HIT_FRAME,
    COMBAT_RECOVER_FRAMES, COMBAT_VICTORY_PAUSE_FRAMES,
    COMBAT_ZONE_SEPARATION, COMBAT_ASSIST_FLANK_BONUS,
    COMBAT_ASSIST_RECOVERY_PENALTY, COMBAT_REINFORCEMENT_MORALE_SHOCK,
    FLANK_DAMAGE_BONUS,
    RETREAT_MORALE_PENALTY, GENERAL_ZONE_SPLASH_RADIUS,
    COMBAT_MICRO_MOVE_SPEED, COMBAT_MICRO_MOVE_THRESHOLD,
    COMBAT_ADVANCE_SPEED, COMBAT_SPARK_TIMER, COMBAT_HIT_FLASH_TIMER,
    COMBAT_DEATH_TIMER, COMBAT_SPLASH_DAMAGE_MULT,
    COMBAT_MAX_SQUADS_PER_SIDE, COMBAT_ASSIST_MAX_DISTANCE,
    GENERAL_ATTACK_COOLDOWN,
)


class CombatZone:
    """Manages a melee engagement zone between one or more squads per side."""

    # Shared dust surface cache across all zones: (radius, alpha) -> Surface
    _dust_cache = {}

    @classmethod
    def _get_dust_surface(cls, dr, alpha):
        """Return a cached dust circle surface for the given radius and alpha."""
        key = (dr, alpha)
        surf = cls._dust_cache.get(key)
        if surf is None:
            surf = pygame.Surface((dr * 2, dr * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (180, 155, 110, alpha), (dr, dr), dr)
            cls._dust_cache[key] = surf
        return surf

    def __init__(self, squad_a, squad_b):
        self.squads_a = [squad_a]
        self.squads_b = [squad_b]
        self.active = True

        # Link squads back to this zone and save pre-zone positions
        squad_a.battleground = self
        squad_b.battleground = self
        squad_a._pre_zone_x, squad_a._pre_zone_y = squad_a.x, squad_a.y
        squad_b._pre_zone_x, squad_b._pre_zone_y = squad_b.x, squad_b.y

        # Compute heading (A toward B) and zone center
        ax, ay = squad_a.center
        bx, by = squad_b.center
        dx, dy = bx - ax, by - ay
        self.heading = math.atan2(dy, dx) if (dx != 0 or dy != 0) else 0.0
        self.zone_center_x = (ax + bx) * 0.5
        self.zone_center_y = (ay + by) * 0.5
        self.separation = COMBAT_ZONE_SEPARATION

        # Combat state
        self.pairs = []           # list of (soldier_a, soldier_b) active duels
        self.assists = []         # list of (helper, ally, enemy) 2v1 engagements
        self.spark_events = []    # [{x, y, timer, angles}]
        self._dust_frame = 0
        self._updated_this_tick = False

        # Generals participating in this zone
        self.generals_a = []
        self.generals_b = []

        # Per-tick caches (cleared in reset_tick_guard)
        self._cached_alive_a = None
        self._cached_alive_b = None
        self._soldier_to_squad = {}
        self._rebuild_soldier_map()

        # Position squads facing each other, then compute initial pairings
        self._position_squads()
        self._compute_pairs()

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def _position_squads(self):
        """Place squads on opposite sides of the contact line, facing each other."""
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        half_sep = self.separation * 0.5

        # Anchors: offset from zone center along heading axis
        anchor_ax = self.zone_center_x - cos_h * half_sep
        anchor_ay = self.zone_center_y - sin_h * half_sep
        anchor_bx = self.zone_center_x + cos_h * half_sep
        anchor_by = self.zone_center_y + sin_h * half_sep

        facing_a = self.heading              # A faces toward B
        facing_b = self.heading + math.pi    # B faces toward A

        for sq in self.squads_a:
            self._place_squad(sq, anchor_ax, anchor_ay, facing_a)
        for sq in self.squads_b:
            self._place_squad(sq, anchor_bx, anchor_by, facing_b)

    def _place_squad(self, squad, anchor_x, anchor_y, facing):
        """Position a squad's soldiers around an anchor point with given facing."""
        cos_f = math.cos(facing)
        sin_f = math.sin(facing)
        squad.facing_angle = facing
        for s in squad.alive_soldiers:
            rox = s.formation_x * cos_f - s.formation_y * sin_f
            roy = s.formation_x * sin_f + s.formation_y * cos_f
            s.x = anchor_x + rox
            s.y = anchor_y + roy
            s.facing_angle = facing

    # ------------------------------------------------------------------
    # Pairing
    # ------------------------------------------------------------------

    def _rebuild_soldier_map(self):
        """Rebuild the soldier-to-squad lookup dict."""
        self._soldier_to_squad = {}
        for sq in self.squads_a + self.squads_b:
            for s in sq.soldiers:
                self._soldier_to_squad[id(s)] = sq

    def _all_alive_a(self):
        if self._cached_alive_a is not None:
            return self._cached_alive_a
        soldiers = []
        for sq in self.squads_a:
            soldiers.extend(sq.alive_soldiers)
        self._cached_alive_a = soldiers
        return soldiers

    def _all_alive_b(self):
        if self._cached_alive_b is not None:
            return self._cached_alive_b
        soldiers = []
        for sq in self.squads_b:
            soldiers.extend(sq.alive_soldiers)
        self._cached_alive_b = soldiers
        return soldiers

    def _squad_for_soldier(self, soldier):
        """Find the squad that owns a soldier (O(1) lookup)."""
        return self._soldier_to_squad.get(id(soldier))

    def _side_for_soldier(self, soldier):
        """Return 'a' or 'b' based on which side owns the soldier."""
        for sq in self.squads_a:
            if soldier in sq.soldiers:
                return 'a'
        return 'b'

    def _lateral_key(self, soldier):
        """Project soldier position onto axis perpendicular to heading."""
        perp_x = -math.sin(self.heading)
        perp_y = math.cos(self.heading)
        return soldier.x * perp_x + soldier.y * perp_y

    def _compute_pairs(self):
        """Match soldiers 1:1 along the front line by lateral position."""
        # Clear old pairing state
        for s in self._all_alive_a() + self._all_alive_b():
            s.paired_opponent = None
            s.combat_state = "IDLE"
            s.combat_timer = 0

        alive_a = self._all_alive_a()
        alive_b = self._all_alive_b()

        sorted_a = sorted(alive_a, key=self._lateral_key)
        sorted_b = sorted(alive_b, key=self._lateral_key)

        n = min(len(sorted_a), len(sorted_b))
        self.pairs = []
        for i in range(n):
            sa, sb = sorted_a[i], sorted_b[i]
            sa.paired_opponent = sb
            sb.paired_opponent = sa
            sa.combat_state = "READY"
            sa.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)
            sb.combat_state = "READY"
            sb.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)
            self.pairs.append((sa, sb))

        self.assists = []

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(self):
        """Tick one frame of combat zone logic. Called once per frame from runtime."""
        if not self.active:
            return

        # Guard against double-update (both squads call update via their own update())
        if self._updated_this_tick:
            return
        self._updated_this_tick = True

        # Check for termination
        alive_a = self._all_alive_a()
        alive_b = self._all_alive_b()
        if not alive_a or not alive_b:
            self.terminate()
            return

        # Tick animation counter
        self._dust_frame += 1

        # Tick spark events
        self.spark_events = [e for e in self.spark_events if e["timer"] > 0]
        for e in self.spark_events:
            e["timer"] -= 1

        # Remove dead soldiers from pairs; reset surviving partner's state
        new_pairs = []
        for a, b in self.pairs:
            if a.alive and b.alive:
                new_pairs.append((a, b))
            else:
                # Reset surviving soldier so they can be re-paired
                for s in (a, b):
                    if s.alive and s.combat_state not in ("VICTORY_PAUSE", "IDLE"):
                        s.combat_state = "IDLE"
                        s.combat_timer = 0
                    s.paired_opponent = None
        self.pairs = new_pairs
        # Clean up assists with dead participants or excessive distance
        max_assist_dist = MELEE_RANGE * COMBAT_ASSIST_MAX_DISTANCE
        new_assists = []
        for h, ally, enemy in self.assists:
            if h.alive and enemy.alive and distance(h.x, h.y, enemy.x, enemy.y) < max_assist_dist:
                new_assists.append((h, ally, enemy))
            else:
                if h.alive and h.combat_state not in ("VICTORY_PAUSE", "IDLE"):
                    h.combat_state = "IDLE"
                    h.combat_timer = 0
        self.assists = new_assists

        # Tick each active pair
        for sa, sb in list(self.pairs):
            self._tick_pair(sa, sb)

        # Tick assists (2v1)
        for helper, ally, enemy in list(self.assists):
            self._tick_assist(helper, enemy)

        # Build paired_ids once for reassignment and advance
        paired_ids = set()
        for a, b in self.pairs:
            paired_ids.add(id(a))
            paired_ids.add(id(b))
        for h, ally, enemy in self.assists:
            paired_ids.add(id(h))

        # Reassign unpaired soldiers
        self._reassign_unpaired(paired_ids)

        # Move unpaired soldiers toward the enemy line
        self._advance_unpaired(paired_ids)

        # Tick general combat (splash damage)
        self._tick_generals()

        # Update zone center from current squad positions
        all_a_center = self._avg_center(alive_a)
        all_b_center = self._avg_center(alive_b)
        if all_a_center and all_b_center:
            self.zone_center_x = (all_a_center[0] + all_b_center[0]) * 0.5
            self.zone_center_y = (all_a_center[1] + all_b_center[1]) * 0.5

    def reset_tick_guard(self):
        """Called at start of each tick to allow the next update."""
        self._updated_this_tick = False
        self._cached_alive_a = None
        self._cached_alive_b = None

    def _avg_center(self, soldiers):
        if not soldiers:
            return None
        cx = sum(s.x for s in soldiers) / len(soldiers)
        cy = sum(s.y for s in soldiers) / len(soldiers)
        return (cx, cy)

    # ------------------------------------------------------------------
    # Combat tick
    # ------------------------------------------------------------------

    def _tick_pair(self, sa, sb):
        """Tick one frame of a 1v1 duel between sa and sb."""
        # Face each other
        sa.facing_angle = math.atan2(sb.y - sa.y, sb.x - sa.x)
        sb.facing_angle = math.atan2(sa.y - sb.y, sa.x - sb.x)

        # Micro-move: close distance if too far for melee
        d = distance(sa.x, sa.y, sb.x, sb.y)
        if d > MELEE_RANGE * COMBAT_MICRO_MOVE_THRESHOLD:
            speed = COMBAT_MICRO_MOVE_SPEED
            dx, dy = sb.x - sa.x, sb.y - sa.y
            norm = max(0.01, math.hypot(dx, dy))
            move = min(speed, d * 0.5 - MELEE_RANGE * 0.3)
            if move > 0:
                sa.x += (dx / norm) * move * 0.5
                sa.y += (dy / norm) * move * 0.5
                sb.x -= (dx / norm) * move * 0.5
                sb.y -= (dy / norm) * move * 0.5

        # Tick each soldier's combat state
        for attacker, defender in [(sa, sb), (sb, sa)]:
            self._tick_combat_state(attacker, defender)

    def _tick_combat_state(self, attacker, defender):
        """Advance one soldier's combat animation state machine."""
        if attacker.combat_state == "READY":
            attacker.combat_timer -= 1
            if attacker.combat_timer <= 0:
                attacker.combat_state = "SWINGING"
                attacker.combat_timer = COMBAT_SWING_FRAMES

        elif attacker.combat_state == "SWINGING":
            attacker.combat_timer -= 1
            # Damage lands at the hit frame
            if attacker.combat_timer == COMBAT_SWING_FRAMES - COMBAT_SWING_HIT_FRAME:
                self._resolve_hit(attacker, defender, flank_mult=1.0)
            if attacker.combat_timer <= 0:
                if not defender.alive:
                    attacker.combat_state = "VICTORY_PAUSE"
                    attacker.combat_timer = COMBAT_VICTORY_PAUSE_FRAMES
                    attacker.paired_opponent = None
                else:
                    attacker.combat_state = "RECOVERING"
                    attacker.combat_timer = COMBAT_RECOVER_FRAMES

        elif attacker.combat_state == "RECOVERING":
            attacker.combat_timer -= 1
            if attacker.combat_timer <= 0:
                attacker.combat_state = "READY"
                attacker.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)

        elif attacker.combat_state == "VICTORY_PAUSE":
            attacker.combat_timer -= 1
            if attacker.combat_timer <= 0:
                attacker.combat_state = "IDLE"
                attacker.paired_opponent = None

    def _tick_assist(self, helper, enemy):
        """Tick a 2v1 assist attack."""
        # Face the enemy
        helper.facing_angle = math.atan2(enemy.y - helper.y, enemy.x - helper.x)

        # Move toward the enemy
        d = distance(helper.x, helper.y, enemy.x, enemy.y)
        if d > MELEE_RANGE:
            dx, dy = enemy.x - helper.x, enemy.y - helper.y
            norm = max(0.01, math.hypot(dx, dy))
            speed = min(0.8, d - MELEE_RANGE)
            helper.x += (dx / norm) * speed
            helper.y += (dy / norm) * speed

        self._tick_combat_state(helper, enemy)

    def _handle_kill(self, victim, killer_squad=None, killer_general=None):
        """Handle soldier death: set death state, notify squad, track kills."""
        victim.health = 0
        victim.alive = False
        victim.death_timer = COMBAT_DEATH_TIMER
        victim.death_alpha = 1.0
        victim_squad = self._squad_for_soldier(victim)
        if victim_squad:
            victim_squad._dying_soldiers.append(victim)
            victim_squad.on_casualty()
        if killer_squad:
            killer_squad.kills += 1
        if killer_general:
            killer_general.kills += 1

    def _resolve_hit(self, attacker, defender, flank_mult=1.0):
        """Resolve a melee hit using existing soldier.attack() math."""
        # Apply terrain defense modifier from the defender's squad
        defender_squad = self._squad_for_soldier(defender)
        defense_terrain_mult = 1.0
        if defender_squad:
            defense_terrain_mult = defender_squad.terrain_mods.get("melee_defense_mult", 1.0)
        dmg = attacker.attack(defender, is_charging=False, flank_mult=flank_mult,
                              defense_terrain_mult=defense_terrain_mult)
        if dmg > 0:
            # Spawn spark at hit position
            self.spark_events.append({
                "x": (attacker.x + defender.x) * 0.5,
                "y": (attacker.y + defender.y) * 0.5,
                "timer": COMBAT_SPARK_TIMER,
                "angles": [random.uniform(0, math.pi * 2) for _ in range(3)],
            })
        if dmg > 0 and not defender.alive:
            attacker_squad = self._squad_for_soldier(attacker)
            self._handle_kill(defender, killer_squad=attacker_squad)

    # ------------------------------------------------------------------
    # Reassignment: winners help neighbors
    # ------------------------------------------------------------------

    def _reassign_unpaired(self, paired_ids):
        """Match unpaired soldiers to new opponents or ally-assist slots."""
        free_a = [s for s in self._all_alive_a()
                  if id(s) not in paired_ids and s.combat_state not in ("VICTORY_PAUSE", "SWINGING")]
        free_b = [s for s in self._all_alive_b()
                  if id(s) not in paired_ids and s.combat_state not in ("VICTORY_PAUSE", "SWINGING")]

        # Priority 1: pair free soldiers with each other
        n = min(len(free_a), len(free_b))
        for i in range(n):
            sa, sb = free_a[i], free_b[i]
            sa.paired_opponent = sb
            sb.paired_opponent = sa
            sa.combat_state = "READY"
            sa.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)
            sb.combat_state = "READY"
            sb.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)
            self.pairs.append((sa, sb))

        # Priority 2: surplus soldiers assist allies (2v1)
        if len(free_a) > len(free_b):
            surplus = free_a[n:]
            surplus_is_a = True
        else:
            surplus = free_b[n:]
            surplus_is_a = False

        for s in surplus:
            # Find nearest active pair where we can assist
            best_pair = None
            best_dist = 999999
            for a, b in self.pairs:
                ally = a if surplus_is_a else b
                d = distance(s.x, s.y, ally.x, ally.y)
                if d < best_dist:
                    best_dist = d
                    best_pair = (a, b)
            if best_pair and best_dist < MELEE_RANGE * COMBAT_ASSIST_MAX_DISTANCE:
                enemy = best_pair[1] if surplus_is_a else best_pair[0]
                ally = best_pair[0] if surplus_is_a else best_pair[1]
                self.assists.append((s, ally, enemy))
                s.combat_state = "READY"
                s.combat_timer = COMBAT_READY_FRAMES + random.randint(-2, 2)

    def _advance_unpaired(self, paired_ids):
        """Move unpaired IDLE soldiers toward the enemy line."""
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)

        for s in self._all_alive_a():
            if id(s) not in paired_ids and s.combat_state == "IDLE":
                s.x += cos_h * COMBAT_ADVANCE_SPEED
                s.y += sin_h * COMBAT_ADVANCE_SPEED
        for s in self._all_alive_b():
            if id(s) not in paired_ids and s.combat_state == "IDLE":
                s.x -= cos_h * COMBAT_ADVANCE_SPEED
                s.y -= sin_h * COMBAT_ADVANCE_SPEED

    # ------------------------------------------------------------------
    # Reinforcements
    # ------------------------------------------------------------------

    def add_reinforcement(self, squad, side):
        """Add a reinforcing squad to the combat zone.

        Args:
            squad: The Squad joining the fight.
            side: 'a' or 'b' — which side they join.

        Returns:
            True if the squad was added, False if the zone is full on that side.
        """
        # Enforce max squads per side
        side_list = self.squads_a if side == 'a' else self.squads_b
        if len(side_list) >= COMBAT_MAX_SQUADS_PER_SIDE:
            return False

        squad.battleground = self
        squad._pre_zone_x, squad._pre_zone_y = squad.x, squad.y
        if side == 'a':
            self.squads_a.append(squad)
            facing = self.heading
        else:
            self.squads_b.append(squad)
            facing = self.heading + math.pi

        # Position the reinforcing squad at the flank of the existing line
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        perp_x = -sin_h
        perp_y = cos_h

        # Find lateral extent of existing soldiers and place on less crowded flank
        existing = self._all_alive_a() if side == 'a' else self._all_alive_b()
        if existing:
            laterals = [s.x * perp_x + s.y * perp_y for s in existing]
            min_lateral = min(laterals)
            max_lateral = max(laterals)
            center_lateral = (min_lateral + max_lateral) * 0.5
            # Place on the flank farther from zone center lateral
            squad_lateral = squad.x * perp_x + squad.y * perp_y
            if squad_lateral < center_lateral:
                flank_offset = min_lateral - SOLDIER_SPACING * 3
            else:
                flank_offset = max_lateral + SOLDIER_SPACING * 3
        else:
            flank_offset = 0

        half_sep = self.separation * 0.5
        sign = -1 if side == 'a' else 1
        anchor_x = self.zone_center_x + cos_h * half_sep * sign + perp_x * flank_offset
        anchor_y = self.zone_center_y + sin_h * half_sep * sign + perp_y * flank_offset

        self._place_squad(squad, anchor_x, anchor_y, facing)

        # Rebuild soldier lookup and invalidate alive caches
        self._rebuild_soldier_map()
        self._cached_alive_a = None
        self._cached_alive_b = None

        # Morale shock to the opposing side
        for sq in (self.squads_b if side == 'a' else self.squads_a):
            sq.apply_morale_modifier(COMBAT_REINFORCEMENT_MORALE_SHOCK)
        return True

    # ------------------------------------------------------------------
    # Squad extraction (retreat)
    # ------------------------------------------------------------------

    def extract_squad(self, squad):
        """Remove a squad from the combat zone (voluntary retreat).

        Clears combat state, reforms the squad at its pre-zone position,
        and applies a morale penalty.
        """
        # Clear combat state for this squad's soldiers only
        squad_soldier_ids = {id(s) for s in squad.soldiers}
        for s in squad.soldiers:
            s.paired_opponent = None
            s.combat_state = "IDLE"
            s.combat_timer = 0

        # Remove from pairs/assists involving this squad's soldiers
        self.pairs = [(a, b) for a, b in self.pairs
                      if id(a) not in squad_soldier_ids and id(b) not in squad_soldier_ids]
        self.assists = [(h, a, e) for h, a, e in self.assists
                        if id(h) not in squad_soldier_ids]

        # Remove from side lists
        if squad in self.squads_a:
            self.squads_a.remove(squad)
        if squad in self.squads_b:
            self.squads_b.remove(squad)
        squad.battleground = None

        # Reform at pre-zone position
        cx = getattr(squad, '_pre_zone_x', squad.x)
        cy = getattr(squad, '_pre_zone_y', squad.y)
        squad.x, squad.y = cx, cy
        squad._reposition_formation()
        for s in squad.alive_soldiers:
            rox, roy = squad._rotate_offset(s.formation_x, s.formation_y)
            s.x = cx + rox
            s.y = cy + roy

        # Morale penalty for retreating
        squad.apply_morale_modifier(RETREAT_MORALE_PENALTY)

        # If one side is now empty, terminate zone
        if not self.squads_a or not self.squads_b:
            self.terminate()

    # ------------------------------------------------------------------
    # Generals
    # ------------------------------------------------------------------

    def add_general(self, general, side):
        """Add a general to the combat zone on the given side."""
        if side == 'a':
            self.generals_a.append(general)
        else:
            self.generals_b.append(general)
        general._in_combat_zone = self

        # Position general behind the line
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        sign = -1 if side == 'a' else 1
        offset = self.separation * 1.5  # behind the front line
        general.x = self.zone_center_x + cos_h * offset * sign
        general.y = self.zone_center_y + sin_h * offset * sign

    def _tick_generals(self):
        """Tick general combat actions in the zone (splash damage)."""
        for gen_list, enemy_soldiers_fn in [
            (self.generals_a, self._all_alive_b),
            (self.generals_b, self._all_alive_a),
        ]:
            enemies = enemy_soldiers_fn()
            if not enemies:
                continue
            for g in list(gen_list):
                if not g.alive:
                    gen_list.remove(g)
                    g._in_combat_zone = None
                    continue
                if g.attack_cooldown > 0:
                    continue

                # Pick a random enemy from active pairs
                target = random.choice(enemies)
                attack_power = g.melee_attack * (1.0 + g.level * 0.15)

                # Apply ability buffs
                if getattr(g, '_bloodlust_active', False):
                    attack_power *= 1.5
                if getattr(g, '_one_man_army_active', False):
                    attack_power *= 2.0
                if getattr(g, '_avatar_active', False):
                    attack_power *= 2.5

                # Primary hit
                effective_armor = target.stats.armor * random.uniform(0.5, 1.0)
                damage = max(1, attack_power * random.uniform(0.8, 1.2) - effective_armor * 0.3)
                target.health -= damage
                target.hit_flash_timer = COMBAT_HIT_FLASH_TIMER

                # Spawn spark
                self.spark_events.append({
                    "x": target.x, "y": target.y,
                    "timer": COMBAT_SPARK_TIMER,
                    "angles": [random.uniform(0, math.pi * 2) for _ in range(3)],
                })

                # General attack visual effect
                if not hasattr(g, '_attack_effects'):
                    g._attack_effects = []
                g._attack_effects.append({
                    "type": "slash",
                    "x": target.x, "y": target.y,
                    "angle": math.atan2(target.y - g.y, target.x - g.x),
                    "timer": COMBAT_SPARK_TIMER,
                })

                if target.health <= 0:
                    self._handle_kill(target, killer_general=g)

                # Splash: hit 1-2 nearby enemies
                splash_count = 0
                splash_dmg = damage * COMBAT_SPLASH_DAMAGE_MULT
                for es in enemies:
                    if es is target or not es.alive:
                        continue
                    if distance(target.x, target.y, es.x, es.y) < GENERAL_ZONE_SPLASH_RADIUS:
                        es_armor = es.stats.armor * random.uniform(0.5, 1.0)
                        s_dmg = max(1, splash_dmg - es_armor * 0.3)
                        es.health -= s_dmg
                        es.hit_flash_timer = COMBAT_HIT_FLASH_TIMER
                        if es.health <= 0:
                            self._handle_kill(es, killer_general=g)
                        splash_count += 1
                        if splash_count >= 2:
                            break

                g.attack_cooldown = GENERAL_ATTACK_COOLDOWN

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface, camera):
        """Render combat zone visual effects: dust, sparks, swing arcs."""
        if not self.active:
            return

        # Distributed dust: one puff per 3 active pairs
        for i, (a, b) in enumerate(self.pairs):
            if (self._dust_frame + i * 7) % 9 != 0:
                continue
            mx = (a.x + b.x) * 0.5
            my = (a.y + b.y) * 0.5
            sx, sy = camera.world_to_screen(mx, my)
            phase = ((self._dust_frame + i * 7) % 30) / 30.0
            dr = int(camera.scale(5 + 8 * phase))
            alpha = int(40 * (1.0 - phase))
            if dr > 0 and alpha > 0:
                dust_surf = self._get_dust_surface(dr, alpha)
                surface.blit(dust_surf, (sx - dr, sy - dr))

        # Clash sparks at individual hit positions
        for e in self.spark_events:
            if e["timer"] <= 0:
                continue
            sx, sy = camera.world_to_screen(e["x"], e["y"])
            progress = e["timer"] / float(COMBAT_SPARK_TIMER)
            for angle in e["angles"]:
                spark_len = camera.scale(8) * progress
                ex = int(sx + math.cos(angle) * spark_len)
                ey = int(sy + math.sin(angle) * spark_len)
                pygame.draw.line(surface, (255, 220, 60), (sx, sy), (ex, ey), 2)

        # Swing arcs for soldiers currently in SWINGING state
        all_soldiers = self._all_alive_a() + self._all_alive_b()
        for s in all_soldiers:
            if s.combat_state == "SWINGING" and s.paired_opponent and s.paired_opponent.alive:
                ax, ay = camera.world_to_screen(s.x, s.y)
                bx, by = camera.world_to_screen(
                    s.paired_opponent.x, s.paired_opponent.y)
                progress = 1.0 - s.combat_timer / COMBAT_SWING_FRAMES
                arc_len = camera.scale(10) * progress
                angle = math.atan2(by - ay, bx - ax)
                ex = int(ax + math.cos(angle) * arc_len)
                ey = int(ay + math.sin(angle) * arc_len)
                fade = max(0, 255 - int(255 * progress))
                pygame.draw.line(surface, (255, 255, fade),
                                 (int(ax), int(ay)), (ex, ey),
                                 max(1, camera.scale(2)))

    # ------------------------------------------------------------------
    # Termination
    # ------------------------------------------------------------------

    def terminate(self):
        """Deactivate this combat zone, unlink squads, and reform formations.

        Winners hold the ground (reform at current center), losers reform at
        their pre-zone position so squads don't appear to teleport.
        """
        self.active = False

        # Determine which side has survivors
        alive_a = any(s.alive for sq in self.squads_a for s in sq.soldiers)
        alive_b = any(s.alive for sq in self.squads_b for s in sq.soldiers)

        for sq in self.squads_a + self.squads_b:
            if not sq:
                continue
            if sq.battleground is self:
                sq.battleground = None
            # Clear combat state on all soldiers
            for s in sq.soldiers:
                s.paired_opponent = None
                s.combat_state = "IDLE"
                s.combat_timer = 0

            # Determine if this squad's side won
            is_winner = (sq in self.squads_a and alive_a and not alive_b) or \
                        (sq in self.squads_b and alive_b and not alive_a)

            if is_winner:
                # Winners hold the ground — reform around current center
                cx, cy = sq.center
            else:
                # Losers/draws reform at pre-zone position
                cx = getattr(sq, '_pre_zone_x', sq.x)
                cy = getattr(sq, '_pre_zone_y', sq.y)

            sq.x, sq.y = cx, cy
            sq._reposition_formation()
            for s in sq.alive_soldiers:
                rox, roy = sq._rotate_offset(s.formation_x, s.formation_y)
                s.x = cx + rox
                s.y = cy + roy

        # Clear general zone references
        for g in getattr(self, 'generals_a', []) + getattr(self, 'generals_b', []):
            g._in_combat_zone = None

        self.squads_a = []
        self.squads_b = []
        self.generals_a = []
        self.generals_b = []
        self.pairs = []
        self.assists = []


# Legacy alias for backwards compatibility with existing imports
Battleground = CombatZone
