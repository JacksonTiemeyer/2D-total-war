# Patch C Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Files Modified**:
  - `battle/ai_engine.py` — corrected `update()` to battle-level signature (all_squads, player_generals, enemy_generals, terrain, weather)
  - `battle/engine.py` — added `ai_engine=None` param; `step()` dispatches to `ai_engine.update()` if present
  - `battle/battle_scene.py` — imports AIEngine; creates `_ai_engine` and passes to CombatEngine
  - `docs/CLAUDE_PATCHC.md` — updated API surface, interaction surface, testing notes
- **Files Created** (original):
  - `battle/ai_engine.py`
  - `docs/CLAUDE_PATCHC.md`
  - `docs/claude_patchC_status.md`
- **Tests Passing**: Yes (smoke test `test_ai_engine_called` + import check)
- **Breaking Changes**: None — ai_engine defaults to None; existing callers unaffected
- **Integration**: AIEngine composable into CombatEngine; dispatched per-tick from `step()`
