# Patch B Status

- **Applied**: Yes
- **Date**: 2026-03-23
- **Migration Complete**: Squad/general updates now flow exclusively through CombatEngine.step()
- **Files Modified**:
  - `battle/engine.py` — full constructor with terrain, weather, siege_engine, veterancy_engine, ai_engine; step() dispatches to all sub-engines
  - `battle/battle_scene.py` — _tick() delegates squad/general updates to CombatEngine (with fallback); _enemy_ai() delegates to AIEngine
  - `tests/patchb_smoke_test.py` — 19 tests covering engine core, AI, siege, and veterancy
  - `docs/CLAUDE_PATCHB.md` — updated API surface and test notes
- **Tests Passing**: Yes (19/19 smoke tests pass without pygame)
- **Breaking Changes**: None — fallback paths preserve behavior when engine is None
- **Engine Live**: Yes — single update path per tick, no duplication
