# Patch C — AIEngine Scaffolding

## Script
- **Name**: AIEngine
- **Path**: `battle/ai_engine.py`

## Purpose
Pluggable AI surface to replace/augment ArmyAI and BattleScene._enemy_ai() in future patches.

## Key Classes/Structures
- `AIEngine` — Army-level AI decision maker with personality support.

## Public API Surface
```python
AIEngine.__init__(self, army, personality=None)
AIEngine.update(self, all_squads, player_generals, enemy_generals, terrain=None, weather=None) -> None
```

## Core Data Structures
- `army` — Reference to the army this AI controls
- `personality` — Optional string ('aggressive', 'cautious', etc.)

## Notable Algorithms/Patterns
- Battle-level signature: `update(all_squads, player_generals, enemy_generals, terrain, weather)`
- Mirrors personality-driven pattern from `campaign/ai_controller.py`
- No-op placeholder — future patches fill in priority evaluation

## Interaction Surface
- **Wired into**: `CombatEngine.__init__(ai_engine=None)` — optional composition
- **Called from**: `CombatEngine.step()` dispatches to `ai_engine.update()` if present
- **Instantiated by**: `BattleScene.__init__()` — creates `_ai_engine` for enemy squads
- **Will replace**: `BattleScene._enemy_ai()` (battle_scene.py lines 1075+)
- **Will augment**: `campaign/ai_controller.py` ArmyAI class

## Design Notes and Tradeoffs
- Kept separate from campaign ArmyAI to allow battle-specific vs campaign-specific AI
- Personality parameter aligns with existing 5-trait system in ai_controller.py
- Battle-level update() signature differs from campaign ArmyAI (squads/generals vs armies/settlements)

## Testing Notes
- Import test: `python -c "from battle.ai_engine import AIEngine"`
- Smoke test: `test_ai_engine_called` in `tests/patchb_smoke_test.py`

## Migration/Extension Notes
- Future: move _enemy_ai() role-based logic into AIEngine.update()
- Future: add battle-specific methods (evaluate_threat, issue_charge, etc.)

## References
- `campaign/ai_controller.py` — Existing ArmyAI (321 lines)
- `battle/battle_scene.py` — _enemy_ai() method
