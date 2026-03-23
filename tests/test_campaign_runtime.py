"""Regression tests for extracted campaign runtime helpers."""

import unittest
from types import SimpleNamespace

from campaign.runtime import consume_pending_battle, queue_pending_battle
from core.contracts import PendingBattle


class CampaignRuntimeTests(unittest.TestCase):
    def test_queue_and_consume_pending_battle(self):
        scene = SimpleNamespace(player_army="player", pending_battle=None)
        queue_pending_battle(scene, enemy_army="enemy", terrain_type="plains")
        self.assertIsInstance(scene.pending_battle, PendingBattle)
        consumed = consume_pending_battle(scene)
        self.assertEqual(consumed.enemy_army, "enemy")
        self.assertIsNone(scene.pending_battle)


if __name__ == "__main__":
    unittest.main()
