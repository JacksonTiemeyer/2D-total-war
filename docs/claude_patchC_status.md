# Patch C Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Migration Complete**: All _enemy_ai() logic now lives in AIEngine
- **Files Modified**:
  - `battle/ai_engine.py` — full role-based AI: melee advance, cavalry flank, ranged stay-back, general abilities, targeting helpers
  - `battle/engine.py` — ai_engine dispatched from step()
  - `battle/battle_scene.py` — _enemy_ai() delegates to AIEngine; helper methods removed (~240 lines)
- **Tests Passing**: Yes (test_ai_engine_called, test_ai_role_classification, test_ai_no_crash_empty)
- **Breaking Changes**: None — AIEngine is wired into CombatEngine; fallback preserves behavior
- **Integration**: AIEngine runs as part of CombatEngine.step() after squad/general updates
