Patch A Status: Combat Engine scaffolding and BattleScene bridge (Non-breaking)

- Added battle/engine.py with CombatEngine scaffold and light sub-engines (TerrainEngine, VisionEngine, SiegeEngine)
- Wired BattleScene to instantiate CombatEngine after armies generation and to invoke CombatEngine.step() every tick (no-op for now)
- Added non-breaking integration in battle/battle_scene.py (imports and guarded calls)
- Created docs/INDEX.md to point Claude Code to context files
- Created initial Markdown docs for key scripts (BattleScene, Squad, Soldier, General, Abilities, SiegeScene, Skirmish, Campaign Army/Generals/AI Controller)

What Claude should pick up next:
- The CombatEngine scaffold is in place; next you will implement the core tick logic inside CombatEngine.step() in Patch B, and progressively migrate theBattleScene into sub-engines (TerrainEngine, VisionEngine, AIEngine, SiegeEngine).
- Ensure that the BattleScene tick continues to call CombatEngine.step() even as behavior is migrated; keep backwards compatibility by not altering return values.

What to tell Claude for Patch B:
- Implement the core per-tick logic inside CombatEngine.step() using the existing BattleScene tick as a reference, then progressively pull per-type logic into sub-engines (Terrain, AI, Siege).
- Expand unit tests around the new engine interface, focusing on deterministic reproduction of key scenarios (formation, morale, and engagement outcomes).
- Maintain backward-compatible API: if the existing BattleScene relies on per-soldier and per-squad state, keep the shape of objects the same and only refactor internals.
