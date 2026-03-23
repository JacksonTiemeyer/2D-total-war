"""CombatEngine - centralized per-tick combat orchestration.

Provides a modular engine that mirrors BattleScene._tick() flow for
squad and general updates. Non-breaking: BattleScene continues to
work independently; the engine is an opt-in bridge for future migration.
"""


class CombatEngine:
    """Core combat engine that steps squads and generals each tick."""

    def __init__(self, player_squads, enemy_squads, player_generals, enemy_generals,
                 terrain=None, weather=None, siege_engine=None,
                 veterancy_engine=None, ai_engine=None):
        self.player_squads = player_squads
        self.enemy_squads = enemy_squads
        self.player_generals = player_generals
        self.enemy_generals = enemy_generals
        self.terrain = terrain
        self.weather = weather
        self.siege_engine = siege_engine
        self.veterancy_engine = veterancy_engine
        self.ai_engine = ai_engine

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

        # AI engine hook (Patch C) — delegate AI decisions if wired
        if self.ai_engine is not None:
            try:
                self.ai_engine.update(all_squads, self.player_generals,
                                      self.enemy_generals, terrain=self.terrain,
                                      weather=self.weather)
            except Exception:
                pass

        # Siege engine hook (Patch D) — delegate siege tick if wired
        if self.siege_engine is not None:
            try:
                if hasattr(self.siege_engine, 'step'):
                    self.siege_engine.step()
                elif hasattr(self.siege_engine, 'tick'):
                    self.siege_engine.tick()
            except Exception:
                pass

        return None

    def award_battle_xp(self, general, amount):
        """Delegate XP award to veterancy engine if wired (Patch E).

        Called post-battle, not per-tick.
        """
        if self.veterancy_engine is not None:
            self.veterancy_engine.award_xp(general, amount)
