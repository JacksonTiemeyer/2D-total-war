"""AI engine scaffolding (Patch C).

This module defines a pluggable AI engine interface that can drive a
combat/ battle's AI decisions. Patch C will evolve ArmyAI into a full AI
engine, but for now this provides a stable, testable surface for Claude
Code to implement and swap in later patches.
"""

from typing import List, Optional


class AIEngine:
    def __init__(self, army, personality: Optional[str] = None):
        self.army = army
        self.personality = personality or "balanced"

    def update(self, armies: List[object], settlements: List[object], diplomacy: object):
        """Compute and emit orders for this AI army.

        Currently a no-op placeholder to establish a contract for future patches.
        Return value is intentionally None to preserve backward compatibility.
        """
        return None
