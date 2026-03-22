Script: Skirmish Setup
Path: battle/skirmish_setup.py
Purpose: Lightweight army builder and quick-start battlefield for standalone skirmishes.

Key Classes/Structures
- SkirmishSetup

Public API Surface
- __init__(self)
- handle_event(self, event)
- _start_battle(self)
- _generate_enemy(self)
- draw(self, surface)

Core Data Structures
- budget, budget_index, player_squads, general_index, scroll_offset, spent
- BUDGET_OPTIONS, GENERAL_OPTIONS, GENERAL_NAMES

Notable Algorithms or Patterns
- Simple budget-based unit selection; keyboard and mouse input to add/remove units
- Random enemy generation aligned to budget target

Interaction Surface
- Used by standalone battle launcher; converts UI selections into battle deployment data

Design Notes and Tradeoffs
- Focuses on ease of use and quick setup; not intended to replace the full campaign battle setup

Testing Notes
- Tests for budget trimming and enemy generation balance

Performance Considerations
- Lightweight; no heavy per-frame logic

Migration / Extension Notes
- Could be extended with save/import/export of setups

References
- battle/skirmish_setup.py, data.unit_types
