# Patch E — VeterancyEngine Scaffolding

## Script
- **Name**: VeterancyEngine
- **Path**: `battle/veterancy_engine.py`

## Purpose
Centralized veterancy and post-battle XP propagation engine.

## Key Classes/Structures
- `VeterancyEngine` — XP distribution and veterancy tracking engine.

## Public API Surface
```python
VeterancyEngine.__init__(self)
VeterancyEngine.award_xp(self, general, amount) -> None
```

## Core Data Structures
- Operates on General instances with `xp` attribute

## Notable Algorithms/Patterns
- `award_xp()` uses `hasattr` guard for safety with different general types
- Simple additive XP — future patches will add formula-based calculation

## Interaction Surface
- **Will replace**: `main.py._award_post_battle_xp()` (lines 411-459)
- **References**: `campaign/army.py` CampaignSquad veterancy ranks

## Design Notes and Tradeoffs
- Minimal scaffold — only the XP hook, not the full formula
- Full formula (base_xp * strength_ratio * win_mult * casualty_factor) stays in main.py until migration
- Squad veterancy (battles_survived, rank progression) not yet covered

## Testing Notes
- Import test: `python -c "from battle.veterancy_engine import VeterancyEngine"`

## Migration/Extension Notes
- Future: move full XP formula from main.py._award_post_battle_xp()
- Future: add squad veterancy progression (battles_survived, rank table)
- Future: add companion XP distribution

## References
- `main.py` lines 411-459 (_award_post_battle_xp)
- `campaign/army.py` CampaignSquad.VETERANCY_RANKS table
- `battle/general.py` General.xp attribute
