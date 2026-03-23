"""AIEngine - pluggable AI surface for battle and campaign decisions.

Scaffolding for future replacement/augmentation of ArmyAI and
BattleScene._enemy_ai(). Mirrors the personality-driven, priority-based
pattern from campaign/ai_controller.py.
"""

from core.utils import distance


class AIEngine:
    """Pluggable AI engine for army decision-making."""

    def __init__(self, army, personality=None):
        """Initialize AI engine for an army.

        Args:
            army: The army this AI controls.
            personality: Optional personality string (e.g. 'aggressive', 'cautious').
        """
        self.army = army
        self.personality = personality

    def update(self, all_squads, player_generals, enemy_generals,
               terrain=None, weather=None):
        """Evaluate priorities and issue orders (battle-level AI).

        This is a pluggable AI engine surface. The default implementation is a
        simple deterministic heuristic, but the signature provides the
        battlefield context for future AI policies.

        Args:
            all_squads: Combined list of all squads on the battlefield.
            player_generals: List of player General instances.
            enemy_generals: List of enemy General instances.
            terrain: Optional terrain data.
            weather: Optional weather string.
        """
        # Simple, deterministic, non-breaking heuristic for demonstration:
        # Move the nearest friendly squad toward the nearest enemy squad.
        try:
            enemies = [s for s in all_squads if getattr(s, 'team', 0) != 0 and not getattr(s, 'is_destroyed', False)]
            friends = [s for s in all_squads if getattr(s, 'team', 0) == 0 and not getattr(s, 'is_destroyed', False)]
            if enemies and friends:
                src = min(friends, key=lambda f: distance(f.x, f.y, enemies[0].x, enemies[0].y))
                target = min(enemies, key=lambda e: distance(src.x, src.y, e.x, e.y))
                src.give_move_order(target.x, target.y)
        except Exception:
            pass
        return None
