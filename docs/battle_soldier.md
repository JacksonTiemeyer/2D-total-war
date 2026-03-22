Script: Soldier
Path: battle/soldier.py
Purpose: Individual soldier within a squad; handles health, damage, movement, and combat interactions.

Key Classes/Structures
- Soldier

Public API Surface
- __init__(self, x, y, stats, team)
- get_exhaustion_factor(self)
- effective_weapon_strength(self)
- effective_ranged_strength(self)
- effective_cooldown(self, base_cooldown)
- take_damage(self, amount, armor_penetration=0, damage_type=DMG_PHYSICAL, attacker_stats=None)
- attack(self, target_soldier, is_charging=False, flank_mult=1.0, defense_terrain_mult=1.0)
- ranged_attack(self, target_soldier, accuracy_mult=1.0, damage_mult=1.0)
- brace_counter_attack(self, charging_soldier)
- update(self)

Core Data Structures
- x, y, stats, team
- health, max_health, alive
- target, attack_cooldown
- formation_x, formation_y, facing_angle
- exhaustion, poison_timer, poison_dps

Notable Algorithms or Patterns
- Damage calculation pipeline with type multipliers and armor interactions
- Evasion checks and poison DOT handling
- Melee and ranged attack routines with randomized factors for realism
- Debuffs and buffs applied via traits (frenzy, poison, shield, aura interactions)

Interaction Surface
- Consumes: stats, terrain, and attacker/defender context
- Produces: updated health/kill state and possibly poison/dot effects on targets

Design Notes and Tradeoffs
- Rich combat micro-logic; a future refactor could extract a dedicated DamageModel and combat-resolution engine.

Testing Notes
- Tests for damage calculation across gear/armor, poison application, and exhaustion interactions.

Performance Considerations
- Per-soldier math is lightweight but scales with squad size; consider batching or vectorization if battles explode in size.

Migration / Extension Notes
- If new traits or damage types are added, update data.traits integration points in this module.

References
- core.settings, core.utils, data.traits, battle.squad
