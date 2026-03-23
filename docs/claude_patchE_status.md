# Patch E Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Files Modified**:
  - `battle/engine.py` — added `veterancy_engine=None` param and `award_battle_xp()` convenience method
  - `docs/CLAUDE_PATCHE.md` — added CombatEngine integration notes
- **Files Created** (original):
  - `battle/veterancy_engine.py`
  - `docs/CLAUDE_PATCHE.md`
  - `docs/claude_patchE_status.md`
- **Tests Passing**: Yes (Patch B smoke tests + import checks)
- **Breaking Changes**: None — `veterancy_engine` defaults to None; existing callers unaffected
- **Integration**: VeterancyEngine composable into CombatEngine; `award_battle_xp()` available for post-battle resolution
