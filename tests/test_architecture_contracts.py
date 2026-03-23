"""Regression tests for architecture handoff contracts."""

import unittest
from types import SimpleNamespace

from core.contracts import ArmyBattlePayload, BattleStats, GeneralBattlePayload, PendingBattle
from core.game_flow import collect_battle_stats


class ContractTests(unittest.TestCase):
    def test_army_payload_round_trip_to_legacy_dict(self):
        payload = ArmyBattlePayload(
            squads=[("unit", 10, {"rank_name": "Raw"})],
            general=GeneralBattlePayload(name="A", stats="hero", xp=3, level=2),
        )
        legacy = payload.to_legacy_dict()
        self.assertEqual(legacy["squads"][0][1], 10)
        self.assertEqual(legacy["general"]["name"], "A")
        self.assertEqual(legacy["general"]["level"], 2)

    def test_pending_battle_legacy_tuple(self):
        pending = PendingBattle(player_army="player", enemy_army="enemy", terrain_type="forest")
        self.assertEqual(pending.to_legacy_tuple(), ("player", "enemy", "forest"))

    def test_collect_battle_stats_returns_structured_result(self):
        squad = SimpleNamespace(
            unit_stats=SimpleNamespace(name="Infantry"),
            initial_count=20,
            alive_count=15,
            kills=4,
            exhaustion_display="Fresh",
        )
        general = SimpleNamespace(
            name="General",
            general_type="Commander",
            kills=2,
            duels_won=1,
            level=3,
            alive=True,
            team=0,
        )
        battle = SimpleNamespace(
            result="player_win",
            battle_timer=120,
            player_squads=[squad],
            enemy_squads=[],
            player_generals=[general],
            enemy_generals=[],
            _dead_generals=[],
        )
        current_enemy = SimpleNamespace(army_strength=100, squads=[1, 2])
        stats = collect_battle_stats(battle, current_enemy)
        self.assertIsInstance(stats, BattleStats)
        self.assertEqual(stats.total_player_kills, 4)
        self.assertEqual(stats.loot_gold, 100)


if __name__ == "__main__":
    unittest.main()
