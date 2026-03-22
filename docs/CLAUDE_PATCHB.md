Patch B Context: Core CombatEngine Implementation

What Patch B will implement
- Implement CombatEngine.step() to perform a faithful per-tick update by:
  - Gathering all squads (player + enemy) and calling update(all_squads) on each non-destroyed squad
  - Updating player and enemy generals with their respective partner squad sets
  - Optional: placeholder hook to feed AI decisions (without breaking current behavior)
- Make BattleScene call CombatEngine.step() each tick (non-breaking, already wired in Patch A)
- Add a basic, minimal test harness for a tick to validate no exceptions and state progression

Rationale
- The engine scaffold in Patch A enables an incremental, testable transition from a monolithic tick loop to a modular engine, reducing risk and enabling focused tests.

What Claude should implement next (high-level guidance)
- Mirror the existing BattleScene._tick flow inside CombatEngine.step(), then progressively move logic into sub-engines (TerrainEngine, VisionEngine, AIEngine, SiegeEngine) in subsequent patches.
- Ensure no public API surface changes in Patch B beyond the internal CombatEngine step implementation; BattleScene should remain compatible.

Notes for future patches
- Patch C: introduce AIEngine and integrate with CombatEngine
- Patch D: introduce SiegeEngine and tie to CombatEngine
- Patch E: integrate veterancy XP propagation with campaign state
- Patch C: introduce AIEngine and integrate with CombatEngine
- Patch D: introduce SiegeEngine and tie to CombatEngine
- Patch E: integrate veterancy XP propagation with campaign state
