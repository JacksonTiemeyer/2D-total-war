# Lightweight runnable smoke test for Patch B combat engine without test framework
from battle.engine import CombatEngine

class MockSquad:
    def __init__(self, team):
        self.team = team
        self._destroyed = False
    @property
    def is_destroyed(self):
        return self._destroyed
    def update(self, all_squads):
        pass

def run():
    s1 = MockSquad(0)
    s2 = MockSquad(1)
    engine = CombatEngine(player_squads=[s1], enemy_squads=[s2], player_generals=[], enemy_generals=[], terrain=None, weather=None)
    for _ in range(3):
        engine.step()
    print("Patch B smoke run complete")

if __name__ == '__main__':
    run()
