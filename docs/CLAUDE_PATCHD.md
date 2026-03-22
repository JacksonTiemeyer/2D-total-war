# Patch D — SiegeEngine Scaffolding

## Script
- **Name**: SiegeEngine
- **Path**: `battle/siege_engine.py`

## Purpose
Centralized siege battle logic scaffold for walls, gates, and towers.

## Key Classes/Structures
- `SiegeEngine` — Siege-specific combat mechanics engine.

## Public API Surface
```python
SiegeEngine.__init__(self, walls=None, gates=None, towers=None)
SiegeEngine.step(self) -> None
```

## Core Data Structures
- `walls` — List of WallSegment instances
- `gates` — List of Gate instances
- `towers` — List of Tower instances

## Notable Algorithms/Patterns
- `step()` naming matches CombatEngine convention
- Constructor accepts optional lists for incremental wiring

## Interaction Surface
- **Will replace**: Siege logic in `battle/siege_scene.py` _tick() override
- **References**: Gate, WallSegment, Tower classes from siege_scene.py

## Design Notes and Tradeoffs
- Kept as separate engine (not subclass of CombatEngine) for composition flexibility
- Gate/Wall/Tower objects remain in siege_scene.py; engine only orchestrates their tick logic

## Testing Notes
- Import test: `python -c "from battle.siege_engine import SiegeEngine"`

## Migration/Extension Notes
- Future: move wall collision, gate HP, tower auto-fire from SiegeScene._tick()
- Future: add breach detection, siege equipment (rams, ladders)

## References
- `battle/siege_scene.py` — Gate, WallSegment, Tower classes (438 lines)
