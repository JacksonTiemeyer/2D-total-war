Claude Context: Patch A — Combat Engine scaffolding and BattleScene bridge

What was implemented
- Added battle/engine.py with CombatEngine scaffold and small sub-engines (TerrainEngine, VisionEngine, SiegeEngine) as no-ops placeholders.
- BattleScene now imports CombatEngine and initializes a non-breaking scaffold self._combat_engine after armies/generals are deployed.
- BattleScene._tick now calls CombatEngine.step() at the start of the tick (wrapped in a try/except to keep behavior stable if the engine isn’t wired yet).
- Added a docs/INDEX.md for navigation and a Patch A status doc to summarize changes.

What Claude should pick up next (Patch B)
- Implement the core per-tick logic inside CombatEngine.step(), basing on the existing BattleScene tick flow (current code reference).
- Begin migrating concerns into sub-engines (TerrainEngine, AIEngine, SiegeEngine) without breaking existing interfaces.
- Add unit tests to cover formation/engagement basics and ensure stable behavior with deterministic seeds.

What to tell Claude (one-liner prompts you can use)
- Read Patch A changes: CombatEngine scaffold introduced; BattleScene bridging non-breaking; new docs index; Claude should use CombatEngine as the primary hook for the per-frame tick in Patch B.
- Implement CombatEngine.step() core logic mirroring the current BattleScene _tick flow, then progressively move responsibilities into TerrainEngine, VisionEngine, AIEngine, and SiegeEngine.
- Keep BattleScene API stable; do not alter inputs/outputs outside engine refactor until next milestone.
- Add tests for engine path: deterministic tick results for simple battle setups; ensure no regression in baseline gameplay.
