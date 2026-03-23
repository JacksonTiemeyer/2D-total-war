# Patch B — CombatEngine Core

## Script
- **Name**: CombatEngine
- **Path**: `battle/engine.py`

## Purpose
Centralized per-tick combat orchestration engine that mirrors BattleScene._tick() squad/general update flow.

## Key Classes/Structures
- `CombatEngine` — Main engine class holding references to player/enemy squads and generals.

## Public API Surface
```python
CombatEngine.__init__(self, player_squads, enemy_squads, player_generals, enemy_generals,
                      terrain=None, weather=None,
                      ai_engine=None, siege_engine=None, veterancy_engine=None)
CombatEngine.step(self) -> None
```

## How to Verify
```bash
# Engine initializes without error (terrain/weather now accepted)
python -c "from battle.engine import CombatEngine; e = CombatEngine([],[],[],[],terrain=[],weather='clear'); print('init OK')"

# Smoke tests (no pygame required)
python tests/patchb_smoke_run.py

# Full game import still clean
python -c "import main; print('import OK')"
```

## Core Data Structures
- `player_squads`, `enemy_squads` — Lists of Squad instances (from `battle/squad.py`)
- `player_generals`, `enemy_generals` — Lists of General instances (from `battle/general.py`)

## Notable Algorithms/Patterns
- `step()` iterates all squads, skipping destroyed ones, then updates all generals
- Non-breaking: BattleScene._tick() continues to run its own logic; engine is additive
- Guard pattern: `if self._combat_engine is not None: self._combat_engine.step()`

## Interaction Surface
- **Reads from**: Squad.is_destroyed, Squad.update(), General.update()
- **Modified by**: BattleScene.__init__ (sets `_combat_engine = None`)
- **Called from**: BattleScene._tick() (guarded, after _enemy_ai())

## Design Notes and Tradeoffs
- Engine holds list references (not copies), so BattleScene list mutations are reflected
- `step()` currently duplicates work if called alongside _tick() squad updates — this is intentional for the bridge phase; future patches will migrate _tick() logic into the engine
- Returns None to maintain API compatibility

## Testing Notes
- `tests/patchb_smoke_test.py` — 5 tests using MockSquad/MockGeneral (no pygame)
- `tests/patchb_smoke_run.py` — Standalone runner

## Performance Considerations
- No additional overhead when `_combat_engine is None` (default)
- When wired, adds O(n) squad + O(m) general iterations per tick

## Migration/Extension Notes
- Future: wire engine in __init__ after _deploy_armies()
- Future: move terrain mods, collision, water-push, sound triggers into engine
- Future: add spell resolution hook after general updates

## References
- `battle/battle_scene.py` lines 987-1074 (_tick method)
- `battle/squad.py` Squad.update() signature
- `battle/general.py` General.update() signature
