"""Smoke tests for CombatEngine (Patch B).

Uses lightweight mocks — no pygame dependency required.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from battle.engine import CombatEngine
from battle.ai_engine import AIEngine
from battle.siege_engine import SiegeEngine
from battle.veterancy_engine import VeterancyEngine


class MockSquad:
    """Minimal squad mock for engine testing."""

    def __init__(self, destroyed=False):
        self.is_destroyed = destroyed
        self.update_count = 0
        self.terrain_mods = None
        self._mods_at_update = None
        self.alive_soldiers = []  # for siege collision compat

    def update(self, all_squads):
        self.update_count += 1
        # Capture terrain_mods state at update time
        self._mods_at_update = self.terrain_mods


class MockGeneral:
    """Minimal general mock for engine testing."""

    def __init__(self):
        self.update_count = 0

    def update(self, friendly_squads, enemy_squads):
        self.update_count += 1


def test_step_updates_squads():
    """Verify step() calls update on all non-destroyed squads."""
    p1 = MockSquad()
    p2 = MockSquad()
    e1 = MockSquad()
    engine = CombatEngine([p1, p2], [e1], [], [])

    engine.step()

    assert p1.update_count == 1, f"Expected 1, got {p1.update_count}"
    assert p2.update_count == 1, f"Expected 1, got {p2.update_count}"
    assert e1.update_count == 1, f"Expected 1, got {e1.update_count}"


def test_step_skips_destroyed():
    """Verify step() skips destroyed squads."""
    alive = MockSquad()
    dead = MockSquad(destroyed=True)
    engine = CombatEngine([alive], [dead], [], [])

    engine.step()

    assert alive.update_count == 1
    assert dead.update_count == 0, f"Destroyed squad should not update, got {dead.update_count}"


def test_step_updates_generals():
    """Verify step() calls update on all generals."""
    pg = MockGeneral()
    eg = MockGeneral()
    engine = CombatEngine([], [], [pg], [eg])

    engine.step()

    assert pg.update_count == 1
    assert eg.update_count == 1


def test_step_returns_none():
    """Verify step() returns None."""
    engine = CombatEngine([], [], [], [])
    result = engine.step()
    assert result is None, f"Expected None, got {result}"


def test_multiple_ticks():
    """Verify multiple step() calls accumulate correctly."""
    sq = MockSquad()
    gen = MockGeneral()
    engine = CombatEngine([sq], [], [gen], [])

    for _ in range(5):
        engine.step()

    assert sq.update_count == 5, f"Expected 5, got {sq.update_count}"
    assert gen.update_count == 5, f"Expected 5, got {gen.update_count}"


def test_ai_engine_called():
    """Verify step() calls ai_engine.update() when wired."""
    ai = AIEngine(army=[], personality='aggressive')
    ai._called = False
    _orig = ai.update

    def _track(*a, **kw):
        ai._called = True
        return _orig(*a, **kw)

    ai.update = _track
    engine = CombatEngine([], [], [], [], ai_engine=ai)
    engine.step()
    assert ai._called, "AIEngine.update() should have been called"


def test_siege_engine_tick_compat():
    """Verify SiegeEngine.tick() delegates to step()."""
    se = SiegeEngine()
    se._stepped = False
    _orig = se.step

    def _track():
        se._stepped = True
        return _orig()

    se.step = _track
    se.tick()
    assert se._stepped, "tick() should delegate to step()"


def test_full_composition():
    """Verify CombatEngine accepts all sub-engines without error."""
    ai = AIEngine(army=[], personality=None)
    se = SiegeEngine()
    ve = VeterancyEngine()
    sq = MockSquad()
    gen = MockGeneral()
    engine = CombatEngine([sq], [], [gen], [],
                          ai_engine=ai, siege_engine=se,
                          veterancy_engine=ve, terrain=[], weather='clear')
    engine.step()
    assert sq.update_count == 1
    assert gen.update_count == 1

    # Post-battle XP hook
    class MockGen:
        xp = 0
    mg = MockGen()
    engine.award_battle_xp(mg, 5)
    assert mg.xp == 5, f"Expected 5, got {mg.xp}"


def test_terrain_mods_before_update():
    """Verify terrain_mods are available when update() is called."""
    sq = MockSquad()
    sq.terrain_mods = {"speed": 0.8, "exhaustion_mult": 1.0}
    engine = CombatEngine([sq], [], [], [])
    engine.step()
    assert sq._mods_at_update is not None, "terrain_mods should be set before update()"
    assert sq._mods_at_update["speed"] == 0.8


def test_single_update_per_tick():
    """Verify squads/generals are updated exactly once per step (no duplication)."""
    sq = MockSquad()
    gen = MockGeneral()
    engine = CombatEngine([sq], [], [gen], [])
    engine.step()
    assert sq.update_count == 1, f"Squad should update once, got {sq.update_count}"
    assert gen.update_count == 1, f"General should update once, got {gen.update_count}"


class MockAISquad:
    """Squad mock with role attributes for AI testing."""
    def __init__(self, team=1, is_ranged=False, is_cavalry=False, is_spear=False,
                 state="idle", morale=80, destroyed=False):
        self.team = team
        self.is_ranged = is_ranged
        self.is_cavalry = is_cavalry
        self.is_spear = is_spear
        self.is_braced = False
        self.is_destroyed = destroyed
        self.state = state
        self.morale = morale
        self.x = 100
        self.y = 100
        self.center = (100, 100)
        self.alive_count = 10
        self.exhaustion = 0
        self.attack_target = None
        self.move_target = None
        self.update_count = 0
        self.terrain_mods = None
        self.alive_soldiers = []

        # Minimal unit_stats mock
        class _Stats:
            range_distance = 200
            armor = 20
        self.unit_stats = _Stats()

    def give_attack_order(self, target):
        self.attack_target = target

    def give_move_order(self, x, y):
        self.move_target = (x, y)

    def update(self, all_squads):
        self.update_count += 1


def test_ai_role_classification():
    """Verify AIEngine classifies melee/cavalry/ranged and issues orders."""
    from battle.squad import SquadState as _SS

    # Enemy melee squad (idle) should attack player squad
    enemy_melee = MockAISquad(team=1, state=_SS.IDLE)
    enemy_melee.x, enemy_melee.y = 500, 500

    # Player squad as target
    player_sq = MockAISquad(team=0, state=_SS.IDLE)
    player_sq.x, player_sq.y = 200, 200

    ai = AIEngine(army=[enemy_melee], personality=None)
    ai.update([player_sq, enemy_melee], [], [], terrain=None, weather=None)

    assert enemy_melee.attack_target is player_sq, \
        "Melee squad should have been given attack order on player squad"


def test_ai_no_crash_empty():
    """Verify AIEngine handles empty squads gracefully."""
    ai = AIEngine(army=[], personality=None)
    # Should not raise
    ai.update([], [], [])


def test_siege_engine_tower_firing():
    """Verify SiegeEngine calls tower.update() with correct targets."""
    class MockTower:
        def __init__(self, team):
            self.team = team
            self.updated_with = None
        def update(self, targets):
            self.updated_with = targets

    tower = MockTower(team=1)
    p_sq = MockSquad()
    e_sq = MockSquad()
    se = SiegeEngine(towers=[tower], player_squads=[p_sq], enemy_squads=[e_sq],
                     all_squads=[p_sq, e_sq])
    se.step()
    # team=1 tower should fire at player squads (team != 0 check)
    assert tower.updated_with is not None, "Tower should have been updated"
    assert p_sq in tower.updated_with, "Tower team=1 should target player squads"


def test_siege_engine_gate_damage():
    """Verify SiegeEngine applies gate damage from nearby attacking squads."""
    from battle.squad import SquadState as _SS

    class MockGate:
        def __init__(self):
            self.x = 100
            self.y = 100
            self.width = 30
            self.height = 80
            self.hp = 500
            self.destroyed = False
            self.damage_taken = 0
        @property
        def rect(self):
            return (self.x, self.y, self.width, self.height)
        def take_damage(self, amount):
            self.damage_taken += amount

    gate = MockGate()
    # Attacking squad near the gate
    atk = MockAISquad(team=0, state=_SS.FIGHTING)
    atk.x, atk.y = 105, 140  # close to gate center
    atk.center = (105, 140)
    atk.alive_count = 10

    se = SiegeEngine(gates=gate, player_squads=[atk], enemy_squads=[],
                     all_squads=[atk], player_is_attacker=True)
    se.step()
    assert gate.damage_taken > 0, f"Gate should have taken damage, got {gate.damage_taken}"


def test_siege_engine_wall_collision():
    """Verify SiegeEngine pushes soldiers out of walls."""
    class MockWall:
        def __init__(self, x, y, w, h):
            self.x = x
            self.y = y
            self.width = w
            self.height = h
        def contains(self, sx, sy):
            return (self.x <= sx <= self.x + self.width and
                    self.y <= sy <= self.y + self.height)

    class MockSoldier:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.alive = True

    class MockSquadWithSoldiers:
        def __init__(self):
            self.is_destroyed = False
            self.soldiers = [MockSoldier(115, 50)]  # inside wall at x=100, w=30
            self.alive_soldiers = self.soldiers
            self.update_count = 0
        def update(self, all_squads):
            self.update_count += 1

    wall = MockWall(100, 0, 30, 200)
    sq = MockSquadWithSoldiers()

    se = SiegeEngine(walls=[wall], all_squads=[sq])
    se.step()
    # Soldier at x=115 is 15 from left (100) and 15 from right (130)
    # Should be pushed to one side
    s = sq.soldiers[0]
    assert s.x < 100 or s.x > 130, f"Soldier should be pushed out of wall, got x={s.x}"


ALL_TESTS = [
    test_step_updates_squads,
    test_step_skips_destroyed,
    test_step_updates_generals,
    test_step_returns_none,
    test_multiple_ticks,
    test_ai_engine_called,
    test_siege_engine_tick_compat,
    test_full_composition,
    test_terrain_mods_before_update,
    test_single_update_per_tick,
    test_ai_role_classification,
    test_ai_no_crash_empty,
    test_siege_engine_tower_firing,
    test_siege_engine_gate_damage,
    test_siege_engine_wall_collision,
]


def run_all():
    passed = 0
    failed = 0
    for test in ALL_TESTS:
        try:
            test()
            passed += 1
            print(f"  PASS: {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test.__name__} — {e}")
    print(f"\n{passed} passed, {failed} failed out of {len(ALL_TESTS)} tests")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
