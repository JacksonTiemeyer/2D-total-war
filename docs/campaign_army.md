Script: Campaign Army
Path: campaign/army.py
Purpose: Represents roaming armies on the world map; manages veterancy, squad composition, gold, and integration points with battles.

Key Classes/Structures
- CampaignSquad
- Army

Public API Surface
- CampaignSquad(unit_stats, current_count=None)
- CampaignSquad.veterancy_rank, rank_name, rank_index
- Army(name, team, x, y, is_player=False)
- Army.total_soldiers, Army.army_strength, Army.upkeep, Army.army_size_limit
- Army.get_battle_data(self, player_class=None)
- Army.add_squad(self, unit_stats)
- Army.remove_squad(self, index)
- Army.give_move_order(self, tx, ty)

Core Data Structures
- self.squads (list of CampaignSquad)
- veterancy tracking: battles_survived, total_kills
- economy: gold
- general: general_name, general_stats, general_xp, general_level

Notable Algorithms or Patterns
- get_battle_data translates campaign state to battle deployment payload
- apply_battle_results updates campaign squads after a battle via battle_scene results

Interaction Surface
- Consumes: unit_stats definitions, veterancy data; battle data from BattleScene
- Produces: battle-suitable deployment payloads, per-squad current_count updates post-battle

Design Notes and Tradeoffs
- Maintains persistence across battles; interacts with post-battle XP handling in main game flow

Testing Notes
- Tests for veterancy progression, squad strength aggregation, and data translation accuracy

Performance Considerations
- Simple aggregation; primary work happens in battle engine

Migration / Extension Notes
- Could be extended with more campaign economy hooks and diplomacy interactions

References
- battle/battle_scene.py, data.unit_types
