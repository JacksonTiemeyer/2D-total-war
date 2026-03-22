Script: Abilities
Path: battle/abilities.py
Purpose: General ability system with level-locked trees and cooldown-based activations tied to general types (Commander, Champion, Strategist, Warlord), plus battlemage/rogue subsets.

Key Classes/Structures
- Ability (base class)
- RallyTheTroops, SecondWind, HoldTheLine, InspiringPresence, Bloodlust, Intimidate, DuelChallenge, Rampage, PrecisionVolley, WeakenResolve, SappingFire, ScoutReport, WarlordRally, ForcedMarch, etc.
- ArcaneBolt, ManaShield, ElementalBlast, EnchantWeapons, SummonElemental, ChainLightning, ArcaneStorm, MassTeleport, Mage Lord, Cataclysm, etc.
- Primitives for Per-Ability state: duration, active_timer, cooldown, radius, etc.

Public API Surface (examples)
- class Ability:
  - __init__(self, name, description, cooldown_seconds, level_required, radius=150)
  - @property ready(self)
  - tick(self)
  - activate(self, general, friendly_squads, enemy_squads)
  - _squads_in_range(self, general, squads)

- Specific abilities implement activate(...) with domain logic and set cooldowns.

Core Data Structures
- Targets, ranges, cooldown timers; per-squad flags set on activation (e.g., _precision_volley, _bloodlust_active)
- Buff state flags on General and on units (e.g., _mana_shield_active, _enchanted_weapons)

Notable Algorithms or Patterns
- Cooldown management per-ability; duration-based buffs with tick cleanup
- Range checks for allied/enemy squads; area of effect handling
- Interaction with general stats and unit stats (armor, damage multipliers, etc.)

Interaction Surface
- Consumes: general, friendly_squads, enemy_squads
- Produces: buff flags on generals and squads; cooldown reset

Design Notes and Tradeoffs
- Very feature-rich; centralizes many combat buff/nerf effects; potential for cross-ability interactions that require careful testing.

Testing Notes
- Tests for cooldown resets, duration expiration, and effects on sample units (e.g., Bloodlust boosts, Sapping Fire DOT behavior).

Performance Considerations
- Tick() invoked every frame for all abilities; ensure tick paths are efficient and lazy where possible.

Migration / Extension Notes
- As new abilities are added, consider a registry-driven approach to reduce duplication in activate() across classes.

References
- battle/general.py, battle/soldier.py
