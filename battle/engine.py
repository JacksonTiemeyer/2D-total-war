"""CombatEngine - centralized per-tick combat orchestration.

Provides a modular engine that mirrors BattleScene._tick() flow for
squad and general updates. Non-breaking: BattleScene continues to
work independently; the engine is an opt-in bridge for future migration.
"""


class CombatEngine:
    """Core combat engine that steps squads and generals each tick."""

    def __init__(self, player_squads, enemy_squads, player_generals, enemy_generals,
                 terrain=None, weather=None):
        self.player_squads = player_squads
        self.enemy_squads = enemy_squads
        self.player_generals = player_generals
        self.enemy_generals = enemy_generals
        self.terrain = terrain
        self.weather = weather

    def step(self):
        """Execute one tick of combat updates.

        Updates all non-destroyed squads, then all generals.
        Returns None (no change to BattleScene API).
        """
        all_squads = self.player_squads + self.enemy_squads

        for sq in all_squads:
            if not sq.is_destroyed:
                sq.update(all_squads)

        for g in self.player_generals:
            g.update(self.player_squads, self.enemy_squads)

        for g in self.enemy_generals:
            g.update(self.enemy_squads, self.player_squads)

        # Hook: future AI-driven decisions and spell resolution go here

        return None
