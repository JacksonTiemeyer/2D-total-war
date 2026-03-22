Patch D Context: SiegeEngine scaffolding and integration

What Patch D will implement
- Introduce battle/siege_engine.py with a minimal SiegeEngine interface
- Wire SiegeEngine into CombatEngine scaffolding for future integration
- Preserve existing BattleScene behavior (non-breaking)

Rationale
- Siege mechanics add depth; patching behind a dedicated engine makes it easier to evolve without breaking the core loop

What Claude should implement next (high-level)
- Implement siege-specific updates (gate damage, tower firing, wall collisions) inside SiegeEngine
- Connect CombatEngine to call SiegeEngine.step() or tick() during per-frame updates in a future patch
