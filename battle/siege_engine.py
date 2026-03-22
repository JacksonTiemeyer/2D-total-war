"""SiegeEngine - centralized siege battle logic scaffold.

Future home for wall/gate/tower tick logic currently in siege_scene.py.
Aligns with Gate, WallSegment, Tower objects from battle/siege_scene.py.
"""


class SiegeEngine:
    """Engine for siege-specific combat mechanics."""

    def __init__(self, walls=None, gates=None, towers=None):
        """Initialize siege engine with structural elements.

        Args:
            walls: List of WallSegment instances.
            gates: List of Gate instances.
            towers: List of Tower instances.
        """
        self.walls = walls or []
        self.gates = gates or []
        self.towers = towers or []

    def step(self):
        """One tick of siege-specific logic.

        No-op placeholder — future patches will migrate wall collision,
        gate destruction, and tower firing from SiegeScene._tick().
        """
        pass
