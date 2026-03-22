Patch B Status: Core engine implementation scaffolding

- Added battle/engine.py (CombatEngine scaffold) and lightweight sub-engines (TerrainEngine, VisionEngine, SiegeEngine)
- BattleScene updated to instantiate CombatEngine with current battle data and call step() per tick
- Created Patch B documentation: CLAUDE_PATCHB.md and a status summary
- Patch B does not yet implement the full per-tick logic; that will be added in Patch B proper implementation of CombatEngine.step()

- Implement CombatEngine.step() to mirror BattleScene._tick() logic using all_squads and generals
- Wire terrain/vision/ai engines progressively in subsequent patches
- Add a tiny tick-based test harness to validate basic step execution
 
- Implement CombatEngine.step() to mirror BattleScene._tick() logic using all_squads and generals
- Wire terrain/vision/a i engines progressively in subsequent patches
- Add a tiny tick-based test harness to validate basic step execution
