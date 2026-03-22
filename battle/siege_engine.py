"""Siege engine scaffolding (Patch D).

A minimal interface for siege-specific logic that can be wired into the
CombatEngine in later patches. Right now, it's a no-op scaffold to enable
progressive migration without breaking existing code.
"""

class SiegeEngine:
    def __init__(self):
        pass

    def tick(self):
        # Placeholder for siege tick logic (gate health, tower firing, etc.)
        return None
