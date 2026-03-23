# Patch D Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Migration Complete**: Siege logic (towers, gates, walls) now lives in SiegeEngine
- **Files Modified**:
  - `battle/siege_engine.py` — full siege logic: tower firing, gate damage, wall/gate collision
  - `battle/siege_scene.py` — __init__() wires SiegeEngine into CombatEngine; _tick() delegates to engine
  - `battle/engine.py` — siege_engine dispatched from step()
- **Tests Passing**: Yes (test_siege_engine_tick_compat, test_siege_engine_tower_firing, test_siege_engine_gate_damage, test_siege_engine_wall_collision)
- **Breaking Changes**: None — SiegeEngine accepts optional params; fallback in SiegeScene._tick()
- **Integration**: SiegeEngine runs as part of CombatEngine.step() after AI dispatch
