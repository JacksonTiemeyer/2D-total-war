Script: Squad
Path: battle/squad.py
Purpose: Manages a group of soldiers moving and fighting as a unit; handles formations, morale, exhaustion, engagement logic, and per-frame updates.

Key Classes/Structures
- Squad
- Formation
- SquadState

Public API Surface
- __init__(self, unit_stats, team, x, y, facing_angle=0.0, soldier_count=None, vet_data=None)
- set_formation(self, formation)
- give_move_order(self, tx, ty, movement_mode=None)
- give_attack_order(self, target_squad)
- update(self, all_squads)
- get_bounding_box(self)
- draw(self, surface, camera, fog_hidden=False)

Core Data Structures
- soldiers (list of Soldier)
- veterancy fields: vet_data, current_count, max_count, battles_survived, total_kills
- formation, morale, exhaustion, engaged_with, center (for rendering/alignment)

Notable Algorithms or Patterns
- Formation offsets computation for LINE, WEDGE, SQUARE, etc.
- Engagement logic: frontlines, flanking checks, morale effects, and pursuit behavior
- Morale management and exhaustion interplay with sustained combat

Interaction Surface
- Consumes: unit_stats, vet_data, terrain_mods, and allied/enemy squads for engagement
- Produces: updated soldier positions and per-soldier state; squad-wide stats

Design Notes and Tradeoffs
- High cohesion within Squad; potential future extraction into a FormationEngine for testability.

Testing Notes
- Tests for formation offset calculations, pathing to target squads, and morale changes under sustained combat.

Performance Considerations
- Frequent per-soldier updates; consider pruning or batching for large battles.

Migration / Extension Notes
- Potentially split formation logic into its own engine in a future patch.

References
- battle/soldier.py, battle/battle_scene.py
