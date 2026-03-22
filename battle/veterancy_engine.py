"""VeterancyEngine - centralized veterancy and post-battle XP propagation.

Future home for XP formula, level-up checks, and squad veterancy
progression currently spread across main.py and campaign/army.py.
"""


class VeterancyEngine:
    """Engine for veterancy tracking and XP distribution."""

    def __init__(self):
        pass

    def award_xp(self, general, amount):
        """Award XP to a general.

        Args:
            general: General instance with an xp attribute.
            amount: XP amount to award.
        """
        if hasattr(general, 'xp'):
            general.xp += amount
