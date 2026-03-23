# Architecture Guardrails

This refactor establishes a few source-of-truth boundaries so future features do not keep expanding the scene classes.

## Allowed dependency shape
- `main.py`: state orchestration, scene switching, save/load entrypoints, post-battle routing
- `campaign/`: campaign rules, map interactions, campaign-only UI, handoff to battle
- `battle/`: tactical rules, battle-only UI, battle simulation, post-battle statistics production
- `core/`: shared contracts, settings, camera, utilities, save/load
- `data/`: unit/content definitions and other static design data

## Guardrails
- New gameplay rules should live in service/system modules, not directly inside large scene draw methods.
- New balance knobs should be named constants in `core/settings.py`.
- New battle/campaign crossovers should use typed contracts from `core/contracts.py`.
- Scene classes should coordinate subsystems and own transient UI state, not become the primary home for rules.
- Save/load should serialize campaign state through `core/save_system.py`, with version handling staying centralized there.

## Current source-of-truth modules
- Balance and global constants: `core/settings.py`
- Unit definitions and roster content: `data/unit_types.py`
- Campaign persistence and restoration: `core/save_system.py`
- Battle handoff and summary contracts: `core/contracts.py`
