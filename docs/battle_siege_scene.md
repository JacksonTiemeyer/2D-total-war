Script: Siege Scene
Path: battle/siege_scene.py
Purpose: Siege battle variant with castle walls, gates, towers; extends BattleScene with siege-specific structures and behavior.

Key Classes/Structures
- Gate
- WallSegment
- Tower
- SiegeScene

Public API Surface
- Gate(x, y, width, height): take_damage(amount); draw(surface, camera)
- WallSegment(x, y, width, height): contains(px, py); draw(surface, camera)
- Tower(x, y, team): update(enemy_squads); draw(surface, camera)
- SiegeScene(player_army, enemy_army, player_is_attacker=True): _generate_terrain(), _deploy_armies(), _tick(), draw(surface)

Core Data Structures
- walls: list of WallSegment
- gate: Gate
- towers: list of Tower
- terrain: list of terrain patches

Notable Algorithms or Patterns
- Gate health-based destruction; tower auto-fire targeting enemies in range; gate collision handling with soldiers
- Wall collision to push soldiers to sides when intersecting wall segments
- Siege-aware deployment to place attackers/defenders around walls

Interaction Surface
- Inputs: armies, siege map configuration
- Outputs: updated unit positions, gate HP, tower cooldowns, siege visuals

Design Notes and Tradeoffs
- Adds a dedicated siege subsystem scaffold; aims for minimal breaking changes with future feature expansion (ladder assaults, siege weapons, breaching mechanics).

Testing Notes
- Tests for gate damage application, tower targeting within range, and collision handling with walls.

Performance Considerations
- Visuals may be heavy; ensure rendering remains within target frame budget; rely on culling for off-screen towers/walls.

Migration / Extension Notes
- Introduce a SiegeEngine interface in a follow-up patch; adapt SiegeScene to use it for future enhancements.

References
- battle/battle_scene.py, battle/squad.py
