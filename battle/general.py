"""General/Hero system with Three Kingdoms-style dueling and abilities."""

import math
import random
import pygame
from core.settings import (
    GENERAL_RADIUS, GENERAL_HEALTH_MULTIPLIER,
    DUEL_RANGE, DUEL_CIRCLE_RADIUS, DUEL_DURATION_MAX,
    MELEE_RANGE, MORALE_GENERAL_AURA, MORALE_GENERAL_DEATH_PENALTY,
    TEAM_COLORS, GOLD, WHITE, BLACK, YELLOW, ORANGE,
    FPS, SPELL_ICON_SIZE, SPELL_RANGE_INDICATOR_COLOR,
    SPELL_AOE_DEFAULT_RADIUS, MANA_BAR_COLOR, MANA_BAR_LOW_COLOR,
)
from core.utils import distance, angle_between, normalize, clamp, get_font
from battle.soldier import Soldier
from battle.abilities import (
    get_abilities_for_type, level_from_xp, xp_for_level,
)


class DuelState:
    NONE = "none"
    CHALLENGED = "challenged"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"


class General:
    """A hero unit that leads an army and can engage in duels."""

    def __init__(self, name, unit_stats, team, x, y, player_class=None, health_mult=1.0):
        self.name = name
        self.unit_stats = unit_stats
        self.team = team
        self.x = x
        self.y = y
        self.health = unit_stats.health * GENERAL_HEALTH_MULTIPLIER * health_mult
        self.max_health = self.health
        self.alive = True
        self.speed = unit_stats.speed
        self.target_x = x
        self.target_y = y
        self.selected = False
        self.attached_squad = None
        self.target_squad = None  # squad this general is actively attacking

        # Combat
        self.attack_cooldown = 0
        self.melee_attack = unit_stats.melee_attack
        self.melee_defense = unit_stats.melee_defense
        self.charge_bonus = unit_stats.charge_bonus
        self.armor = unit_stats.armor

        # Duel system
        self.duel_state = DuelState.NONE
        self.duel_opponent = None
        self.duel_timer = 0
        self.duel_clashes = []
        self.duel_score = 0

        # Type and aura
        self.general_type = unit_stats.name  # Commander, Champion, Strategist
        self.aura_radius = 150 if self.general_type == "Commander" else 100
        self.morale_aura = MORALE_GENERAL_AURA
        if self.general_type == "Commander":
            self.morale_aura *= 1.5

        # Stats tracking
        self.kills = 0
        self.duels_won = 0

        # Leveling
        self.xp = 0
        self.level = 1

        # Abilities
        self.abilities = get_abilities_for_type(self.general_type)

        # Buff flags (set by abilities)
        self._bloodlust_active = False
        self._sapping_fire = False
        self._scout_active = False
        self._all_enemy_generals = []  # set by battle scene
        self.visible = True  # fog of war
        self._in_combat_zone = None    # CombatZone reference (set by zone)
        self._attack_effects = []      # visual effects for melee attacks

        # Player class abilities (overrides type-based if provided)
        self.player_class = None
        if player_class:
            self.player_class = player_class
            from battle.abilities import get_abilities_for_class
            self.abilities = get_abilities_for_class(player_class)

        # Warlord class gets commander-style aura bonuses
        if self.player_class == "warlord":
            self.aura_radius = 150
            self.morale_aura = MORALE_GENERAL_AURA * 1.5

        # New buff flags from class abilities (Batch 10)
        self._mana_shield_active = False
        self._enchant_weapons_active = False
        self._death_aura_active = False
        self._soul_harvest_active = False
        self._lich_transform_active = False
        self._unstoppable_active = False
        self._slayer_active = False
        self._one_man_army_active = False
        self._avatar_active = False
        self._sabotage_active = False
        self._shadow_war_active = False
        self._iron_discipline_active = False
        self._cooldown_reduction = 0  # percentage reduction from passives (Mage Lord, Master Engineer)

        # Mana / Spellcasting
        self.max_mana = getattr(unit_stats, 'max_mana', 0)
        self.mana = self.max_mana
        self.mana_regen = getattr(unit_stats, 'mana_regen', 0.0)
        self.spell_cooldowns = {}  # {spell.name: remaining_frames}
        self._spell_targeting = False
        self._spell_targeting_spell = None
        self._selected_spell_index = 0

    @property
    def available_spells(self):
        """Return Spell objects from unit_stats.spell_list."""
        return list(getattr(self.unit_stats, 'spell_list', ()))

    @property
    def available_abilities(self):
        """Return abilities unlocked at current level."""
        return [a for a in self.abilities if a.level_required <= self.level]

    @property
    def xp_to_next(self):
        next_level = self.level + 1
        return max(0, xp_for_level(next_level) - self.xp)

    def gain_xp(self, amount):
        self.xp += amount
        new_level = level_from_xp(self.xp)
        if new_level > self.level:
            self.level = new_level

    def activate_ability(self, index, friendly_squads, enemy_squads):
        """Activate ability by index (0-based among available abilities)."""
        avail = self.available_abilities
        if index >= len(avail):
            return False
        return avail[index].activate(self, friendly_squads, enemy_squads)

    def give_move_order(self, tx, ty):
        self.target_x = tx
        self.target_y = ty
        self.target_squad = None  # clear squad target on manual move

    def give_attack_order(self, squad):
        """Order this general to attack a specific enemy squad."""
        self.target_squad = squad
        self.target_x = squad.x
        self.target_y = squad.y

    def challenge_duel(self, other_general):
        """Initiate a duel challenge (Three Kingdoms style)."""
        if not other_general.alive or not self.alive:
            return False
        if self.duel_state != DuelState.NONE or other_general.duel_state != DuelState.NONE:
            return False
        dist_val = distance(self.x, self.y, other_general.x, other_general.y)
        if dist_val > DUEL_RANGE * 3:
            return False
        self.duel_state = DuelState.ACTIVE
        self.duel_opponent = other_general
        self.duel_timer = 0
        self.duel_score = 0
        other_general.duel_state = DuelState.ACTIVE
        other_general.duel_opponent = self
        other_general.duel_timer = 0
        other_general.duel_score = 0
        return True

    def update(self, friendly_squads, enemy_squads):
        if not self.alive:
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # Mana regeneration
        if self.max_mana > 0 and self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen / FPS)

        # Tick spell cooldowns
        for sname in list(self.spell_cooldowns):
            self.spell_cooldowns[sname] = max(0, self.spell_cooldowns[sname] - 1)
            if self.spell_cooldowns[sname] <= 0:
                del self.spell_cooldowns[sname]

        # Tick all abilities
        for a in self.abilities:
            a.tick()

        # Clear timed buff flags
        bloodlust_ability = next(
            (a for a in self.abilities if a.name == "Bloodlust"), None)
        if bloodlust_ability and hasattr(bloodlust_ability, 'active_timer'):
            if bloodlust_ability.active_timer <= 0:
                self._bloodlust_active = False

        sapping = next(
            (a for a in self.abilities if a.name == "Sapping Fire"), None)
        if sapping and hasattr(sapping, 'active_timer'):
            if sapping.active_timer <= 0:
                self._sapping_fire = False

        scout = next(
            (a for a in self.abilities if a.name == "Scout Report"), None)
        if scout and hasattr(scout, 'active_timer'):
            if scout.active_timer <= 0:
                self._scout_active = False

        # Clear timed class ability buff flags
        for a in self.abilities:
            if hasattr(a, 'active_timer') and a.active_timer <= 0:
                # Each ability is responsible for clearing its own flags via tick()
                pass

        # Duel takes priority
        if self.duel_state == DuelState.ACTIVE:
            self._update_duel()
            return

        # Track target squad - update position if still alive
        if self.target_squad:
            if self.target_squad.is_destroyed:
                self.target_squad = None
            else:
                self.target_x = self.target_squad.x
                self.target_y = self.target_squad.y

        # Movement
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist_val = math.sqrt(dx * dx + dy * dy)
        if dist_val > 5:
            nx, ny = normalize(dx, dy)
            self.x += nx * self.speed
            self.y += ny * self.speed

        # If attached to a squad, follow slightly behind it
        if self.attached_squad and not self.attached_squad.is_destroyed:
            cx, cy = self.attached_squad.center
            offset = 15
            self.target_x = cx - math.cos(self.attached_squad.facing_angle) * offset
            self.target_y = cy - math.sin(self.attached_squad.facing_angle) * offset

        # Auto-challenge nearby enemy generals for a duel
        if self.duel_state == DuelState.NONE:
            for eg in getattr(self, '_all_enemy_generals', []):
                if (eg.alive and eg.duel_state == DuelState.NONE
                        and distance(self.x, self.y, eg.x, eg.y) < DUEL_RANGE):
                    self.challenge_duel(eg)
                    break

        # If in a combat zone, skip normal melee (zone handles general combat)
        if getattr(self, '_in_combat_zone', None) is not None:
            return

        # General melee combat: attack nearby enemy soldiers
        if self.attack_cooldown == 0:
            best_target = None
            best_dist = MELEE_RANGE * 2  # generals have slightly longer reach
            for sq in enemy_squads:
                if sq.is_destroyed:
                    continue
                for s in sq.alive_soldiers:
                    d = distance(self.x, self.y, s.x, s.y)
                    if d < best_dist:
                        best_dist = d
                        best_target = (s, sq)
            if best_target:
                soldier, squad = best_target
                attack_power = self.melee_attack
                if self._bloodlust_active:
                    attack_power *= 1.5
                if self._one_man_army_active:
                    attack_power *= 2.0
                if self._avatar_active:
                    attack_power *= 2.5
                # Soldier stores armor on its UnitStats (soldier.stats.armor),
                # not as a direct attribute.
                effective_armor = soldier.stats.armor * random.uniform(0.5, 1.0)
                damage = max(1, attack_power * random.uniform(0.8, 1.2) - effective_armor * 0.3)
                soldier.health -= damage
                soldier.hit_flash_timer = 6
                # Spawn attack visual effect (slash arc)
                self._attack_effects.append({
                    "type": "slash",
                    "x": soldier.x, "y": soldier.y,
                    "angle": math.atan2(soldier.y - self.y, soldier.x - self.x),
                    "timer": 8,
                })
                if soldier.health <= 0:
                    soldier.alive = False
                    soldier.death_timer = 15
                    soldier.death_alpha = 1.0
                    squad._dying_soldiers.append(soldier)
                    squad.on_casualty()
                    self.kills += 1
                    # Soul Harvest: restore ability charges
                    if self._soul_harvest_active:
                        for a in self.abilities:
                            if hasattr(a, 'current_cooldown') and a.current_cooldown > 0:
                                a.current_cooldown = max(0, a.current_cooldown - 60)
                self.attack_cooldown = 30

        # Apply morale aura to friendly squads
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            d = distance(self.x, self.y, sq.x, sq.y)
            if d < self.aura_radius:
                sq.apply_morale_modifier(self.morale_aura * 0.01)

        # Death Aura: DOT to nearby enemies (every 30 frames = 0.5s)
        self._frame_counter = getattr(self, '_frame_counter', 0) + 1
        if self._death_aura_active and self._frame_counter % 30 == 0:
            for sq in enemy_squads:
                if sq.is_destroyed:
                    continue
                d = distance(self.x, self.y, sq.x, sq.y)
                if d < 150:
                    for s in sq.alive_soldiers[:3]:  # damage up to 3 soldiers
                        s.health -= 2
                        if s.health <= 0:
                            s.alive = False
                            sq.on_casualty()

        # Unstoppable: immune to exhaustion effects (reset speed penalty)
        if self._unstoppable_active:
            self.speed = self.unit_stats.speed  # override any speed debuff

    def _update_duel(self):
        """Process one frame of a duel."""
        if not self.duel_opponent or not self.duel_opponent.alive:
            self.duel_state = DuelState.WON
            self.duels_won += 1
            # XP awarded post-battle, not during battle
            return

        opp = self.duel_opponent
        self.duel_timer += 1

        d = distance(self.x, self.y, opp.x, opp.y)
        if d > DUEL_RANGE:
            nx, ny = normalize(opp.x - self.x, opp.y - self.y)
            self.x += nx * self.speed * 0.8
            self.y += ny * self.speed * 0.8

        if self.duel_timer % 40 == 0 and self.attack_cooldown == 0:
            self._duel_clash(opp)

        if self.duel_timer >= DUEL_DURATION_MAX:
            if self.duel_score > opp.duel_score:
                opp.take_damage(self.melee_attack * 3)
            elif opp.duel_score > self.duel_score:
                self.take_damage(opp.melee_attack * 3)
            else:
                # Tie: both take reduced damage
                self.take_damage(opp.melee_attack)
                opp.take_damage(self.melee_attack)
            self._end_duel()

    def _duel_clash(self, opponent):
        """A single clash exchange in a duel."""
        my_attack = self.melee_attack
        opp_attack = opponent.melee_attack

        # Bloodlust buff
        if self._bloodlust_active:
            my_attack *= 1.5
        if opponent._bloodlust_active:
            opp_attack *= 1.5

        # One-Man Army: +100% attack
        if self._one_man_army_active:
            my_attack *= 2.0
        if opponent._one_man_army_active:
            opp_attack *= 2.0

        # Avatar of War: +150% attack
        if self._avatar_active:
            my_attack *= 2.5
        if opponent._avatar_active:
            opp_attack *= 2.5

        # Slayer: bonus damage vs high-level opponents
        if self._slayer_active and opponent.level >= 5:
            my_attack *= 1.5
        if opponent._slayer_active and self.level >= 5:
            opp_attack *= 1.5

        my_roll = my_attack * random.uniform(0.6, 1.4)
        opp_roll = opp_attack * random.uniform(0.6, 1.4)

        # Champion type gets duel bonus
        if self.general_type == "Champion":
            my_roll *= 1.3
        if opponent.general_type == "Champion":
            opp_roll *= 1.3

        # Champion player class also gets duel bonus
        if self.player_class == "champion":
            my_roll *= 1.3
        if opponent.player_class == "champion":
            opp_roll *= 1.3

        if my_roll > opp_roll:
            # Use weapon strength for damage
            damage = max(5, self.unit_stats.weapon_strength *
                         random.uniform(0.8, 1.2) -
                         opponent.melee_defense * 0.3)
            opponent.take_damage(damage)
            self.duel_score += 1
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            self.duel_clashes.append((mid_x, mid_y, 15))
        else:
            damage = max(5, opponent.unit_stats.weapon_strength *
                         random.uniform(0.8, 1.2) -
                         self.melee_defense * 0.3)
            self.take_damage(damage)
            opponent.duel_score += 1
            mid_x = (self.x + opponent.x) / 2
            mid_y = (self.y + opponent.y) / 2
            opponent.duel_clashes.append((mid_x, mid_y, 15))

        self.attack_cooldown = 20

        if not opponent.alive:
            self.duel_state = DuelState.WON
            self.duels_won += 1
            self.kills += 1
            # XP awarded post-battle, not during battle
            opponent.duel_state = DuelState.LOST
        elif not self.alive:
            opponent.duel_state = DuelState.WON
            opponent.duels_won += 1
            opponent.kills += 1
            # A6: XP awarded post-battle only, not during battle
            self.duel_state = DuelState.LOST

    def _end_duel(self):
        if self.duel_opponent:
            self.duel_opponent.duel_state = DuelState.NONE
            self.duel_opponent.duel_opponent = None
        self.duel_state = DuelState.NONE
        self.duel_opponent = None

    def take_damage(self, amount):
        effective_armor = self.armor * random.uniform(0.5, 1.0)
        damage = max(1, amount - effective_armor)
        # Mana Shield: 40% damage reduction
        if self._mana_shield_active:
            damage = int(damage * 0.6)
        # Avatar of War: 50% damage reduction
        if self._avatar_active:
            damage = int(damage * 0.5)
        # One-Man Army: 30% damage reduction
        if self._one_man_army_active:
            damage = int(damage * 0.7)
        # Lich Transform: passive regen (heal 1 per hit taken)
        if self._lich_transform_active:
            self.health = min(self.max_health, self.health + 1)
        damage = max(1, damage)
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return damage

    # ── Spellcasting ────────────────────────────────────────────────

    def can_cast(self, spell):
        """Check if the general can cast this spell right now."""
        if self.max_mana <= 0 or not self.alive:
            return False
        if self.mana < spell.mana_cost:
            return False
        if self.spell_cooldowns.get(spell.name, 0) > 0:
            return False
        return True

    def cast_spell(self, spell, target_squad=None, target_pos=None,
                   friendly_squads=None, enemy_squads=None):
        """Attempt to cast a spell. Returns True if successful."""
        if not self.can_cast(spell):
            return False
        self.mana -= spell.mana_cost
        self.spell_cooldowns[spell.name] = int(spell.cooldown_seconds * FPS)

        if spell.effect_type == "damage":
            targets = []
            if spell.targeting == "area" and target_pos and enemy_squads:
                radius = spell.aoe_radius or SPELL_AOE_DEFAULT_RADIUS
                for sq in enemy_squads:
                    if sq.is_destroyed:
                        continue
                    d = distance(self.x, self.y if not target_pos else target_pos[1],
                                 sq.x, sq.y)
                    if target_pos:
                        d = distance(target_pos[0], target_pos[1], sq.x, sq.y)
                    if d < radius:
                        targets.append(sq)
            elif target_squad and not target_squad.is_destroyed:
                targets.append(target_squad)
            for sq in targets:
                for s in sq.alive_soldiers[:min(8, len(sq.alive_soldiers))]:
                    s.take_damage(spell.damage, armor_penetration=80,
                                  damage_type=spell.damage_type)
                    if not s.alive:
                        sq._dying_soldiers.append(s)
                        sq.on_casualty()
                        self.kills += 1
        elif spell.effect_type == "buff" and friendly_squads:
            # Buff nearest friendly squad
            best = None
            best_d = 999999
            for sq in friendly_squads:
                if sq.is_destroyed:
                    continue
                d = distance(self.x, self.y, sq.x, sq.y)
                if d < best_d:
                    best_d = d
                    best = sq
            if best:
                duration = int(spell.duration_seconds * FPS) if spell.duration_seconds else 300
                best.active_buffs[spell.name] = duration
                if spell.heal > 0:
                    for s in best.alive_soldiers:
                        s.health = min(s.max_health, s.health + spell.heal)
        elif spell.effect_type == "debuff" and target_squad:
            duration = int(spell.duration_seconds * FPS) if spell.duration_seconds else 300
            target_squad.active_buffs[spell.name] = duration
            if "Dread" in spell.name or "Curse" in spell.name:
                target_squad.apply_morale_modifier(-15)
        return True

    def on_death(self, friendly_squads):
        """Apply morale penalty when a general dies."""
        for sq in friendly_squads:
            if sq.is_destroyed:
                continue
            sq.apply_morale_modifier(-MORALE_GENERAL_DEATH_PENALTY)

    def draw(self, surface, camera, fog_hidden=False):
        if not self.alive or fog_hidden:
            return

        sx, sy = camera.world_to_screen(self.x, self.y)
        r = camera.scale(GENERAL_RADIUS)
        color = TEAM_COLORS[self.team]

        # Duel circle
        if self.duel_state == DuelState.ACTIVE:
            duel_r = camera.scale(DUEL_CIRCLE_RADIUS)
            duel_surf = pygame.Surface((duel_r * 2, duel_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(duel_surf, (255, 215, 0, 50), (duel_r, duel_r), duel_r)
            pygame.draw.circle(duel_surf, GOLD, (duel_r, duel_r), duel_r, 2)
            surface.blit(duel_surf, (sx - duel_r, sy - duel_r))

        # Bloodlust glow
        if self._bloodlust_active:
            glow_r = camera.scale(GENERAL_RADIUS + 6)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 50, 30, 80), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Mana Shield glow (blue)
        if self._mana_shield_active:
            glow_r = camera.scale(GENERAL_RADIUS + 8)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (50, 100, 255, 60), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Avatar of War glow (golden, large)
        if self._avatar_active:
            glow_r = camera.scale(GENERAL_RADIUS + 12)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 200, 50, 80), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Death Aura glow (purple)
        if self._death_aura_active:
            glow_r = camera.scale(GENERAL_RADIUS + 8)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (120, 0, 200, 60), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # Combat zone glow (subtle gold ring when in a zone)
        if getattr(self, '_in_combat_zone', None) is not None:
            zone_r = camera.scale(GENERAL_RADIUS + 5)
            zone_surf = pygame.Surface((zone_r * 2, zone_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(zone_surf, (255, 215, 0, 50), (zone_r, zone_r), zone_r)
            surface.blit(zone_surf, (sx - zone_r, sy - zone_r))

        # Attack visual effects (slash arcs, impact rings)
        effects = getattr(self, '_attack_effects', [])
        for eff in effects:
            if eff["timer"] <= 0:
                continue
            esx, esy = camera.world_to_screen(eff["x"], eff["y"])
            progress = 1.0 - eff["timer"] / 8.0
            if eff["type"] == "slash":
                # Slash arc from general toward target
                arc_len = camera.scale(12) * progress
                angle = eff["angle"]
                ex = int(esx + math.cos(angle) * arc_len)
                ey = int(esy + math.sin(angle) * arc_len)
                fade = max(0, 255 - int(255 * progress))
                pygame.draw.line(surface, (255, 255, fade),
                                 (int(sx), int(sy)), (ex, ey),
                                 max(1, camera.scale(2)))
                # Impact ring at target
                ring_r = int(camera.scale(6) * progress)
                if ring_r > 0:
                    ring_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
                    ring_alpha = max(0, int(180 * (1.0 - progress)))
                    pygame.draw.circle(ring_surf, (255, 200, 60, ring_alpha),
                                       (ring_r, ring_r), ring_r, 1)
                    surface.blit(ring_surf, (esx - ring_r, esy - ring_r))
        # Tick attack effect timers
        self._attack_effects = [e for e in effects if e["timer"] > 0]
        for e in self._attack_effects:
            e["timer"] -= 1

        # General body - circle with outer ring + gold accent
        inner_r = max(1, int(r))
        outer_r = max(2, int(r + 3))
        pygame.draw.circle(surface, GOLD, (int(sx), int(sy)), outer_r, 2)
        pygame.draw.circle(surface, color, (int(sx), int(sy)), inner_r)

        # Level indicator (small number)
        if camera.zoom > 0.4:
            lvl_font = get_font(max(10, camera.scale(11)))
            lvl_text = lvl_font.render(str(self.level), True, WHITE)
            surface.blit(lvl_text, (sx - lvl_text.get_width() // 2,
                                     sy - lvl_text.get_height() // 2))

        # Health bar
        bar_w = camera.scale(30)
        bar_h = max(2, camera.scale(4))
        bar_x = sx - bar_w // 2
        bar_y = sy - r - camera.scale(12)
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
        hp_w = int(bar_w * self.health / self.max_health)
        hp_color = (50, 220, 50) if self.health / self.max_health > 0.5 else (
            (220, 200, 50) if self.health / self.max_health > 0.25 else (220, 50, 50))
        pygame.draw.rect(surface, hp_color, (bar_x, bar_y, hp_w, bar_h))

        # XP bar (thin, below health)
        xp_y = bar_y + bar_h + 1
        xp_h = max(1, camera.scale(2))
        pygame.draw.rect(surface, (30, 30, 30), (bar_x, xp_y, bar_w, xp_h))
        next_threshold = xp_for_level(self.level + 1)
        prev_threshold = xp_for_level(self.level)
        range_xp = max(1, next_threshold - prev_threshold)
        progress = (self.xp - prev_threshold) / range_xp
        xp_w = int(bar_w * min(1.0, progress))
        pygame.draw.rect(surface, (100, 180, 255), (bar_x, xp_y, xp_w, xp_h))

        # Mana bar (below XP, if caster)
        if self.max_mana > 0:
            mana_y = xp_y + xp_h + 1
            mana_h = max(1, camera.scale(2))
            pygame.draw.rect(surface, (30, 30, 60), (bar_x, mana_y, bar_w, mana_h))
            mana_w = int(bar_w * self.mana / self.max_mana)
            mc = MANA_BAR_COLOR if self.mana / self.max_mana > 0.3 else MANA_BAR_LOW_COLOR
            pygame.draw.rect(surface, mc, (bar_x, mana_y, mana_w, mana_h))

        # Name label
        if camera.zoom > 0.4:
            font = get_font(max(14, camera.scale(16)))
            display_type = self.player_class.capitalize() if self.player_class else self.general_type
            label = f"{self.name} ({display_type}) Lv{self.level}"
            text = font.render(label, True, GOLD)
            surface.blit(text, (sx - text.get_width() // 2, bar_y - 16))

        # Selection circle
        if self.selected:
            pygame.draw.circle(surface, GOLD, (sx, sy), r + 4, 2)

        # Spell icons (when selected and has spells)
        spells = self.available_spells
        if self.selected and spells and camera.zoom > 0.35:
            icon_s = SPELL_ICON_SIZE
            total_w = len(spells) * (icon_s + 2)
            ix = int(sx - total_w // 2)
            iy = int(sy + camera.scale(20))
            for i, spell in enumerate(spells):
                school_colors = {
                    "fire": (180, 60, 20), "ice": (60, 120, 200),
                    "heavens": (100, 100, 200), "shadow": (80, 0, 120),
                    "death": (30, 120, 30), "life": (60, 180, 60),
                    "beasts": (140, 110, 40), "metal": (160, 160, 120),
                }
                bg = school_colors.get(spell.school, (80, 80, 120))
                rect = pygame.Rect(ix + i * (icon_s + 2), iy, icon_s, icon_s)
                pygame.draw.rect(surface, bg, rect)
                border_c = GOLD if i == self._selected_spell_index else (120, 120, 140)
                pygame.draw.rect(surface, border_c, rect, 2)
                cd = self.spell_cooldowns.get(spell.name, 0)
                if cd > 0:
                    cd_h = int(icon_s * cd / (spell.cooldown_seconds * FPS))
                    cd_surf = pygame.Surface((icon_s, cd_h), pygame.SRCALPHA)
                    cd_surf.fill((0, 0, 0, 140))
                    surface.blit(cd_surf, (rect.x, rect.bottom - cd_h))
                sfont = get_font(max(9, int(icon_s * 0.45)))
                cost_t = sfont.render(str(spell.mana_cost), True,
                                      (200, 200, 255) if self.mana >= spell.mana_cost
                                      else (255, 80, 80))
                surface.blit(cost_t, (rect.right - cost_t.get_width() - 1,
                                      rect.bottom - cost_t.get_height()))
                letter = sfont.render(spell.name[0], True, (255, 255, 255))
                surface.blit(letter, (rect.x + 2, rect.y + 1))

        # Spell targeting range indicator
        if self._spell_targeting and self._spell_targeting_spell:
            sp = self._spell_targeting_spell
            r_range = int(camera.scale(sp.range_distance))
            if r_range > 0:
                range_surf = pygame.Surface((r_range * 2, r_range * 2), pygame.SRCALPHA)
                pygame.draw.circle(range_surf, SPELL_RANGE_INDICATOR_COLOR,
                                   (r_range, r_range), r_range)
                surface.blit(range_surf, (int(sx - r_range), int(sy - r_range)))

        # Draw duel clash effects
        new_clashes = []
        for cx, cy, frames in self.duel_clashes:
            if frames > 0:
                scx, scy = camera.world_to_screen(cx, cy)
                spark_r = camera.scale(8 + (15 - frames))
                alpha = int(255 * frames / 15)
                spark_surf = pygame.Surface((spark_r * 2, spark_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(spark_surf, (255, 255, 100, alpha),
                                   (spark_r, spark_r), spark_r)
                surface.blit(spark_surf, (scx - spark_r, scy - spark_r))
                new_clashes.append((cx, cy, frames - 1))
        self.duel_clashes = new_clashes

        # Aura radius (when selected)
        if self.selected:
            aura_r = camera.scale(self.aura_radius)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*GOLD, 25), (aura_r, aura_r), aura_r)
            pygame.draw.circle(aura_surf, (*GOLD, 60), (aura_r, aura_r), aura_r, 1)
            surface.blit(aura_surf, (sx - aura_r, sy - aura_r))
