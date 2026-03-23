"""AIEngine - pluggable AI surface for battle decisions.

Replaces BattleScene._enemy_ai() with a standalone, testable engine.
Implements role-based AI: melee advances, cavalry flanks, ranged stays back.
"""

from core.utils import distance
from battle.squad import SquadState
from battle.general import DuelState


class AIEngine:
    """Pluggable AI engine for army decision-making."""

    def __init__(self, army, personality=None):
        """Initialize AI engine for an army.

        Args:
            army: The army (squad list) this AI controls.
            personality: Optional personality string (e.g. 'aggressive', 'cautious').
        """
        self.army = army
        self.personality = personality

    def update(self, all_squads, player_generals, enemy_generals,
               terrain=None, weather=None):
        """Evaluate priorities and issue orders (battle-level AI).

        Implements role-based AI migrated from BattleScene._enemy_ai().

        Args:
            all_squads: Combined list of all squads on the battlefield.
            player_generals: List of player General instances.
            enemy_generals: List of enemy General instances.
            terrain: Optional terrain data.
            weather: Optional weather string.
        """
        self._run_role_ai(all_squads, player_generals, enemy_generals)

    def _run_role_ai(self, all_squads, player_generals, enemy_generals):
        """Role-based AI: melee advances, cavalry flanks, ranged stays back."""
        # Determine which side we control: enemy squads are self.army
        alive_own = [sq for sq in self.army
                     if not sq.is_destroyed and
                     sq.state not in (SquadState.ROUTED, SquadState.BROKEN)]

        # Opponents are all squads not in our army
        own_ids = {id(sq) for sq in self.army}
        alive_opponents = [sq for sq in all_squads
                           if id(sq) not in own_ids and not sq.is_destroyed]

        if not alive_own or not alive_opponents:
            return

        # Classify our squads by role
        melee = [sq for sq in alive_own if not sq.is_ranged and not sq.is_cavalry]
        cavalry = [sq for sq in alive_own if sq.is_cavalry]
        ranged = [sq for sq in alive_own if sq.is_ranged and not sq.is_cavalry]

        # Detect battle phase
        engaged_count = sum(1 for sq in alive_own if sq.state == SquadState.FIGHTING)
        phase = "opening" if engaged_count == 0 else "engaged"

        # --- Melee infantry: advance toward nearest enemy ---
        for sq in melee:
            if sq.state != SquadState.IDLE:
                continue
            best = self._find_best_target(sq, alive_opponents, prefer_melee=True)
            if best:
                sq.give_attack_order(best)

        # --- Spearmen: hold position when cavalry is near ---
        for sq in melee:
            if sq.is_spear and sq.state == SquadState.IDLE:
                enemy_cav = [p for p in alive_opponents if p.is_cavalry]
                for cav in enemy_cav:
                    d = distance(sq.x, sq.y, cav.x, cav.y)
                    if d < 300:
                        break

        # --- Cavalry: wait for engagement, then flank ---
        for sq in cavalry:
            if sq.state != SquadState.IDLE:
                continue
            if phase == "opening" and melee:
                continue
            target = self._find_flank_target(sq, alive_opponents)
            if target:
                sq.give_attack_order(target)

        # --- Ranged: stay behind melee line, pick high-value targets ---
        for sq in ranged:
            if sq.state != SquadState.IDLE:
                continue
            target = self._find_ranged_target(sq, alive_opponents)
            if target:
                d = distance(sq.x, sq.y, target.x, target.y)
                if d <= sq.unit_stats.range_distance:
                    sq.give_attack_order(target)
                else:
                    tx, ty = target.center
                    dx, dy = tx - sq.x, ty - sq.y
                    dist = max(1, (dx**2 + dy**2)**0.5)
                    approach_dist = dist - sq.unit_stats.range_distance * 0.8
                    if approach_dist > 0:
                        nx, ny = dx / dist, dy / dist
                        sq.give_move_order(sq.x + nx * approach_dist,
                                           sq.y + ny * approach_dist)

        # --- Spellcaster squads: cast spells when able ---
        for sq in alive_own:
            if sq.max_mana > 0 and sq.available_spells:
                self._ai_use_spells_squad(sq, alive_opponents, all_squads)

        # --- General AI ---
        # enemy_generals here are the generals controlled by this AI
        for g in enemy_generals:
            if not g.alive or g.duel_state == DuelState.ACTIVE:
                continue

            self._use_general_abilities(g, self.army, alive_opponents)
            self._ai_use_spells_general(g, self.army, alive_opponents)

            # Champion: seek duels
            if g.general_type == "Champion":
                for pg in player_generals:
                    if pg.alive and pg.duel_state == DuelState.NONE:
                        d = distance(g.x, g.y, pg.x, pg.y)
                        if d < 200:
                            g.challenge_duel(pg)
                            break

            # General attacks nearest enemy squad
            if alive_opponents:
                targets = [sq for sq in alive_opponents
                           if sq.state == SquadState.FIGHTING]
                if not targets:
                    targets = alive_opponents
                if targets:
                    t = min(targets, key=lambda s: distance(g.x, g.y, s.x, s.y))
                    g.give_attack_order(t)

    # --- Targeting helpers ---

    def _find_best_target(self, sq, enemies, prefer_melee=False):
        """Find best target for a melee unit."""
        best = None
        best_score = -float("inf")
        for e in enemies:
            d = distance(sq.x, sq.y, e.x, e.y)
            score = -d * 0.1
            if e.morale < 40:
                score += 50
            if e.state == SquadState.FIGHTING:
                score += 30
            if prefer_melee and e.is_ranged:
                score += 20
            if score > best_score:
                best_score = score
                best = e
        return best

    def _find_flank_target(self, cavalry_sq, enemies):
        """Find best target for cavalry to flank."""
        best = None
        best_score = -float("inf")
        for e in enemies:
            d = distance(cavalry_sq.x, cavalry_sq.y, e.x, e.y)
            score = -d * 0.05
            if e.state == SquadState.FIGHTING:
                score += 100
            if e.is_braced or (e.is_spear and e.state == SquadState.IDLE):
                score -= 200
            if e.morale < 50:
                score += 40
            if e.is_ranged:
                score += 30
            if score > best_score:
                best_score = score
                best = e
        return best

    def _find_ranged_target(self, ranged_sq, enemies):
        """Find best target for ranged units."""
        in_range = [e for e in enemies
                    if distance(ranged_sq.x, ranged_sq.y, e.x, e.y)
                    <= ranged_sq.unit_stats.range_distance * 1.2]
        if not in_range:
            return min(enemies, key=lambda e: distance(ranged_sq.x, ranged_sq.y, e.x, e.y))

        best = None
        best_score = -float("inf")
        for e in in_range:
            score = 0
            if e.is_ranged:
                score += 40
            if e.is_cavalry:
                score += 20
            if e.unit_stats.armor < 15:
                score += 30
            if e.morale < 50:
                score += 25
            score += e.alive_count * 2
            if score > best_score:
                best_score = score
                best = e
        return best

    def _use_general_abilities(self, general, friendly, enemy):
        """Smart ability usage for enemy generals."""
        avail = general.available_abilities
        ready = [(i, a) for i, a in enumerate(avail) if a.ready]
        if not ready:
            return

        for idx, ability in ready:
            name = ability.name

            # Commander abilities
            if name == "Rally the Troops":
                low_morale = [sq for sq in friendly if not sq.is_destroyed and sq.morale < 40]
                if low_morale:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Second Wind":
                tired = [sq for sq in friendly if not sq.is_destroyed and sq.exhaustion > 60]
                if tired:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Hold the Line":
                breaking = [sq for sq in friendly if not sq.is_destroyed and sq.morale < 30]
                if len(breaking) >= 2:
                    general.activate_ability(idx, friendly, enemy)
                    return

            # Champion abilities
            elif name == "Bloodlust":
                if general.duel_state == DuelState.ACTIVE or any(
                    distance(general.x, general.y, e.x, e.y) < 100
                    for e in enemy if not e.is_destroyed
                ):
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Intimidate":
                nearby_enemy = [e for e in enemy if not e.is_destroyed and
                                distance(general.x, general.y, e.x, e.y) < ability.radius]
                if len(nearby_enemy) >= 2:
                    general.activate_ability(idx, friendly, enemy)
                    return

            # Strategist abilities
            elif name == "Precision Volley":
                ranged_firing = [sq for sq in friendly if sq.is_ranged and
                                 sq.state == SquadState.FIRING and not sq.is_destroyed]
                if ranged_firing:
                    general.activate_ability(idx, friendly, enemy)
                    return
            elif name == "Weaken Resolve":
                targets = [e for e in enemy if not e.is_destroyed and e.morale < 50]
                if targets:
                    general.activate_ability(idx, friendly, enemy)
                    return

    def _ai_use_spells_squad(self, squad, enemies, all_squads):
        """AI spell usage for spellcaster squads."""
        for spell in squad.available_spells:
            if not squad.can_cast(spell):
                continue

            if spell.effect_type == "damage":
                # Find best enemy target in range
                best = None
                best_count = 0
                for e in enemies:
                    if e.is_destroyed:
                        continue
                    d = distance(squad.x, squad.y, e.x, e.y)
                    if d < spell.range_distance:
                        count = e.alive_count
                        if count > best_count:
                            best_count = count
                            best = e
                if best:
                    squad.cast_spell(spell, target_squad=best,
                                     target_pos=(best.x, best.y),
                                     all_squads=all_squads)
                    return

            elif spell.effect_type == "buff" and spell.targeting == "self":
                # Self-buff: cast when in combat or low health
                if squad.state == SquadState.FIGHTING or squad.morale < 50:
                    squad.cast_spell(spell, all_squads=all_squads)
                    return

            elif spell.effect_type == "debuff":
                # Debuff nearest enemy
                for e in enemies:
                    if e.is_destroyed:
                        continue
                    d = distance(squad.x, squad.y, e.x, e.y)
                    if d < spell.range_distance:
                        squad.cast_spell(spell, target_squad=e,
                                         all_squads=all_squads)
                        return

    def _ai_use_spells_general(self, general, friendly, enemy):
        """AI spell usage for spellcaster generals."""
        for spell in general.available_spells:
            if not general.can_cast(spell):
                continue

            if spell.effect_type == "damage":
                best = None
                best_count = 0
                for e in enemy:
                    if e.is_destroyed:
                        continue
                    d = distance(general.x, general.y, e.x, e.y)
                    if d < spell.range_distance:
                        count = e.alive_count
                        if count > best_count:
                            best_count = count
                            best = e
                if best:
                    general.cast_spell(spell, target_squad=best,
                                       target_pos=(best.x, best.y),
                                       friendly_squads=friendly,
                                       enemy_squads=enemy)
                    return

            elif spell.effect_type == "buff":
                # Buff nearest friendly squad that's fighting
                for sq in friendly:
                    if sq.is_destroyed:
                        continue
                    if sq.state == SquadState.FIGHTING:
                        d = distance(general.x, general.y, sq.x, sq.y)
                        if d < spell.range_distance:
                            general.cast_spell(spell, target_squad=sq,
                                               friendly_squads=friendly,
                                               enemy_squads=enemy)
                            return

            elif spell.effect_type == "debuff":
                for e in enemy:
                    if e.is_destroyed:
                        continue
                    d = distance(general.x, general.y, e.x, e.y)
                    if d < spell.range_distance:
                        general.cast_spell(spell, target_squad=e,
                                           friendly_squads=friendly,
                                           enemy_squads=enemy)
                        return
