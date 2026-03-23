# Patch E Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Migration Complete**: XP formula and distribution logic now in VeterancyEngine
- **Files Modified**:
  - `battle/veterancy_engine.py` — calculate_xp(), award_xp(), distribute_battle_xp()
  - `main.py` — _award_post_battle_xp() delegates to VeterancyEngine
  - `battle/engine.py` — award_battle_xp() convenience method
- **Tests Passing**: Yes (test_veterancy_calculate_xp_win, test_veterancy_calculate_xp_loss, test_veterancy_award_xp_with_levelup, test_veterancy_calculate_xp_empty)
- **Breaking Changes**: None — VeterancyEngine is instantiated on-demand in main.py
- **Integration**: Full XP distribution (general, player character, companions) centralized
