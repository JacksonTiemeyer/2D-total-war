# Patch B Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Files Modified**:
  - `battle/engine.py` — full constructor with `terrain`, `weather`, `siege_engine`, `veterancy_engine`, `ai_engine`; `step()` dispatches to ai_engine and siege_engine; `award_battle_xp()` for veterancy
  - `battle/battle_scene.py` — imports AIEngine; wires `_ai_engine` and passes to CombatEngine constructor; guarded `step()` call in `_tick()`
  - `tests/patchb_smoke_test.py` — 8 tests covering core engine, ai_engine dispatch, siege tick() compat, full composition
  - `docs/CLAUDE_PATCHB.md` — updated API surface and test notes
- **Files Created** (Patch A/B original):
  - `tests/patchb_smoke_test.py`
  - `tests/patchb_smoke_run.py`
  - `docs/CLAUDE_PATCHB.md`
  - `docs/INDEX.md`
- **Tests Passing**: Yes (8/8 smoke tests pass without pygame)
- **Breaking Changes**: None — all new params default to None
- **Engine Live**: Yes — `_combat_engine` initializes with `_ai_engine`; `step()` called once per tick
- **Next Steps**: Future patches migrate `_tick()` squad/general updates into the engine and remove the parallel native loop
