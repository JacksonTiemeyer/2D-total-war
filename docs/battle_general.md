Script: General
Path: battle/general.py
Purpose: Hero unit with dueling, aura effects, and ability management that drives army leadership decisions in battle.

Key Classes/Structures
- General
- DuelState

Public API Surface
- __init__(self, name, unit_stats, team, x, y, player_class=None, health_mult=1.0)
- gain_xp(self, amount)
- activate_ability(self, index, friendly_squads, enemy_squads)
- give_move_order(self, tx, ty)
- give_attack_order(self, squad)
- challenge_duel(self, other_general)
- update(self, friendly_squads, enemy_squads)
- take_damage(self, amount)
- on_death(self, friendly_squads)
- draw(self, surface, camera, fog_hidden=False)

Core Data Structures
- self.x, self.y, self.team, self.speed
- self.attack_cooldown, self.melee_attack, self.melee_defense, self.armor
- self.duel_state, self.duel_opponent, self.duel_timer, self.duel_score
- self.abilities, self._bloodlust_active, self._sapping_fire, self._scout_active
- self.xp, self.level, self.kills, self.duels_won
- self.player_class, self.aura_radius, self.morale_aura
- self.visible, self._mana_shield_active, self._avatar_active, etc. buff flags

Notable Algorithms or Patterns
- Dueling workflow with ACTIVE/CHALLENGED/WON/LOST states
- Ability system integration: activate, tick, and per-buff flags
- Aura management for morale and combat buffs/debuffs
- Player-class overrides for abilities and aura adjustments

Interaction Surface
- Consumes: allied/enemy squads for targeting and ability evaluation
- Produces: updated position, cooldowns, and buff state; duel outcomes affect XP later

Design Notes and Tradeoffs
- The General class centralizes hero behavior; future work should extract a dedicated HeroEngine to separate battle vs. campaign concerns.

Testing Notes
- Tests for duel resolution, aura application, and ability activation under varying XP/level states.

Performance Considerations
- Frequent per-frame checks for aura propagation and duel state; ensure tests cover worst-case tick loads.

Migration / Extension Notes
- Introduce a HeroEngine abstraction to decouple hero logic from the main battle loop in a future patch.

References
- battle/soldier.py, battle/abilities.py, battle/battle_scene.py
