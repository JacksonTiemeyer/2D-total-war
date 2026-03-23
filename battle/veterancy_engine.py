"""VeterancyEngine - centralized veterancy and post-battle XP propagation.

Future home for XP formula, level-up checks, and squad veterancy
progression currently spread across main.py and campaign/army.py.
"""


class VeterancyEngine:
    """Engine for veterancy tracking and XP distribution."""

    def __init__(self):
        pass

    def award_xp(self, general, amount):
        """Award XP to a general and handle level ups if XP thresholds are crossed."""
        if not hasattr(general, 'xp'):
            return
        general.xp += amount
        # Optional: auto level up if helper exists
        try:
            from battle.general import xp_for_level, level_from_xp  # lazy import to avoid cycle in some setups
            next_level = level_from_xp(general.xp)
            if hasattr(general, 'level') and next_level > general.level:
                general.level = next_level
        except Exception:
            pass
