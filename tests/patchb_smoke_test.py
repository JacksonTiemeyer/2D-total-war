from types import SimpleNamespace

from battle.engine import CombatEngine


class DummyStats:
    squad_size = 1
    name = "Dummy"
    health = 10
    speed = 1
    ranged_attack = 0
    range_distance = 0
    armor = 0
    weapon_strength = 5
    melee_attack = 5
    melee_defense = 5
    armor_penetration = 0
    exhaustion_rate = 1
    traits = ()


def test_patchb_combat_engine_step_runs_without_error(monkeypatch):
    # Use lightweight mock squads to avoid pygame dependency in tests
    class MockSquad:
        def __init__(self, team):
            self.team = team
            self._destroyed = False
        @property
        def is_destroyed(self):
            return self._destroyed
        def update(self, all_squads):  # no-op for smoke test
            pass
    s1 = MockSquad(team=0)
    s2 = MockSquad(team=1)

    engine = CombatEngine(
        player_squads=[s1],
        enemy_squads=[s2],
        player_generals=[],
        enemy_generals=[],
        terrain=None,
        weather=None,
    )

    # Run a few steps to ensure no crashes
    for _ in range(3):
        engine.step()
