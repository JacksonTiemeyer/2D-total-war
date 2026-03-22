Script: Battle Scene Engine
Path: battle/battle_scene.py
Purpose: Real-time tactical combat orchestrator between player and enemy squads; handles deployment, movement, terrain effects, fog of war, and post-battle state reporting.

Key Classes/Structures
- BattleScene
- BattleResult
- (Supporting data structures: Squad, General, Terrain entries used by the scene)

Public API Surface
- __init__(self, player_army, enemy_army, terrain_type=None, season=None, companions=None)
- handle_event(self, event)
- update(self)
- _tick(self)
- _enemy_ai(self)
- get_terrain_modifiers(), _compute_visibility()

Core Data Structures
- player_squads, enemy_squads
- player_generals, enemy_generals
- all_squads, all_generals
- terrain, weather, fog_enabled, deployment_phase

Notable Algorithms or Patterns
- Visibility / fog of war with scout and weather modifiers
- Terrain and weather modifiers propagate to squads and affect stats
- Formation-aware engagement and melee/ranged interactions
- Morale and exhaustion interplay affecting unit persistence
- AoE targeting and chain/area effects
- Siege or wall interactions integrated in related scenes

Interaction Surface
- Consumes: player_army, enemy_army, terrain/weather configuration, and UI input events
- Produces: updated unit states, visibility state, and a BattleResult indicating outcome

Design Notes and Tradeoffs
- Currently a large, monolithic tick loop. The long-term plan is to extract a CombatEngine and sub-engines (TerrainEngine, AIEngine) to improve testability.
- This doc outlines the intended interfaces and contracts for that migration, while preserving current behavior in this patch.

Testing Notes
- Plan unit tests around visibility computation, terrain modifiers, and basic melee/ranged resolution paths.
- Include regression tests for post-battle XP propagation path later.

Performance Considerations
- Per-frame state updates are extensive; consider caching for LOS checks and optimizing collision handling.

Migration / Extension Notes
- Introduce CombatEngine interface in a follow-up patch; gradually migrate battle logic behind the interface.
- Keep existing BattleScene API surface stable to avoid breaking existing game flows.

References
- battle/squad.py, battle/soldier.py, battle/general.py, battle/abilities.py
