"""Veterancy and XP propagation scaffolding (Patch E).

This module will centralize veterancy progression, post-battle XP, and how
XP translates into campaign squad and general growth. For Patch E we provide a
minimal interface to attach XP events and query veterancy state.
"""

class VeterancyEngine:
    def __init__(self):
        pass

    def award_xp(self, general, xp_amount: int):
        """Award XP to a general. Placeholder implementation."""
        if hasattr(general, 'gain_xp'):
            general.gain_xp(xp_amount)
        return None
