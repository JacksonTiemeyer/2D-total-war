"""AIEngine - pluggable AI surface for battle and campaign decisions.

Scaffolding for future replacement/augmentation of ArmyAI and
BattleScene._enemy_ai(). Mirrors the personality-driven, priority-based
pattern from campaign/ai_controller.py.
"""


class AIEngine:
"""Pluggable AI engine for army decision-making."""

from core.utils import distance

    def __init__(self, army, personality=None):
        """Initialize AI engine for an army.

        Args:
            army: The army this AI controls.
            personality: Optional personality string (e.g. 'aggressive', 'cautious').
        """
        self.army = army
        self.personality = personality
    def update(self, all_squads, player_generals, enemy_generals, terrain=None, weather=None):
        """Evaluate priorities and issue orders.

        This is a pluggable AI engine surface. The default implementation is a
        no-op, but the signature provides the battlefield context for future
        AI policies.
        
        Args:
            all_squads: List of all squads on the battlefield.
            player_generals: Player generals active in this battle.
            enemy_generals: Enemy generals active in this battle.
            terrain: Optional terrain context.
            weather: Optional weather context.
        """
        # Simple, deterministic, non-breaking heuristic for demonstration:
        # Move the nearest friendly squad toward the nearest enemy squad.
        try:
            # Filter out destroyed squads
            enemies = [s for s in all_squads if getattr(s, 'team', 0) != 0 and not getattr(s, 'is_destroyed', False)]
            friends = [s for s in all_squads if getattr(s, 'team', 0) == 0 and not getattr(s, 'is_destroyed', False)]
            if enemies and friends:
                # pick a target enemy closest to any friendly squad's center
                if friends:
                    src = min(friends, key=lambda f: distance(f.x, f.y, enemies[0].x, enemies[0].y))
                    target = min(enemies, key=lambda e: distance(src.x, src.y, e.x, e.y))
                    src.give_move_order(target.x, target.y)
        except Exception:
            pass
        return None
