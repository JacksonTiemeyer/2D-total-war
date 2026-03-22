"""AIEngine - pluggable AI surface for battle and campaign decisions.

Scaffolding for future replacement/augmentation of ArmyAI and
BattleScene._enemy_ai(). Mirrors the personality-driven, priority-based
pattern from campaign/ai_controller.py.
"""


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

    def update(self, armies, settlements, diplomacy):
        """Evaluate priorities and issue orders.

        Args:
            armies: List of all armies on the map.
            settlements: List of all settlements.
            diplomacy: Diplomacy state object.

        No-op placeholder — future patches will implement priority evaluation.
        """
        pass
