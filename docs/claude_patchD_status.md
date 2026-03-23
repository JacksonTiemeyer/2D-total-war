# Patch D Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Files Modified**:
  - `battle/engine.py` — added `siege_engine=None` param; `step()` delegates to `siege_engine.step()` if present
  - `docs/CLAUDE_PATCHD.md` — added CombatEngine integration notes
- **Files Created** (original):
  - `battle/siege_engine.py`
  - `docs/CLAUDE_PATCHD.md`
  - `docs/claude_patchD_status.md`
- **Tests Passing**: Yes (Patch B smoke tests + import checks)
- **Breaking Changes**: None — `siege_engine` defaults to None; existing callers unaffected
- **Integration**: SiegeEngine is composable into CombatEngine via optional kwarg; future patches wire SiegeScene to pass it
