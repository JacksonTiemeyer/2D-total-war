# Patch D Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Files Modified**:
  - `battle/siege_engine.py` — added `tick()` compatibility method delegating to `step()`
  - `battle/engine.py` — `siege_engine=None` param; `step()` delegates to `siege_engine.step()` if present
  - `docs/CLAUDE_PATCHD.md` — added tick() to API surface, updated testing notes
- **Files Created** (original):
  - `battle/siege_engine.py`
  - `docs/CLAUDE_PATCHD.md`
  - `docs/claude_patchD_status.md`
- **Tests Passing**: Yes (smoke test `test_siege_engine_tick_compat` + Patch B tests + import checks)
- **Breaking Changes**: None — `siege_engine` defaults to None; existing callers unaffected
- **Integration**: SiegeEngine composable into CombatEngine; `tick()` compat for legacy callers
