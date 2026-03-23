"""Movement engine: orchestrates smart formation moves for multiple squads.

This is a minimal, opt-in component that can be wired behind a feature flag.
It computes formation-guided destinations for a set of squads heading toward a
destination and applies per-squad move orders accordingly.
"""
from battle.formation_engine import compute_line_formation_for_squads


class MovementEngine:
    def __init__(self):
        pass

    def arrange_formation(self, squads, destination, spacing=50):
        """Return a mapping { squad: (tx, ty, facing) } for a line formation move."""
        return compute_line_formation_for_squads(squads, destination, spacing)
