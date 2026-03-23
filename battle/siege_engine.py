"""SiegeEngine - centralized siege battle logic.

Handles wall/gate/tower tick logic migrated from siege_scene.py.
Operates on Gate, WallSegment, Tower objects from battle/siege_scene.py.
"""

from core.utils import distance
from battle.squad import SquadState


class SiegeEngine:
    """Engine for siege-specific combat mechanics."""

    def __init__(self, walls=None, gates=None, towers=None,
                 player_squads=None, enemy_squads=None,
                 all_squads=None, player_is_attacker=True):
        """Initialize siege engine with structural elements and squad refs.

        Args:
            walls: List of WallSegment instances.
            gates: List of Gate instances (or single Gate).
            towers: List of Tower instances.
            player_squads: Reference to player squad list.
            enemy_squads: Reference to enemy squad list.
            all_squads: Reference to combined squad list.
            player_is_attacker: Whether the player is the attacker.
        """
        self.walls = walls or []
        self.gates = gates if isinstance(gates, list) else ([gates] if gates else [])
        self.towers = towers or []
        self.player_squads = player_squads or []
        self.enemy_squads = enemy_squads or []
        self.all_squads = all_squads or []
        self.player_is_attacker = player_is_attacker

    def step(self):
        """One tick of siege-specific logic.

        Handles tower firing, gate damage, and wall/gate collision.
        """
        self._update_towers()
        self._update_gate_damage()
        self._resolve_wall_collisions()
        self._resolve_gate_collisions()
        return None

    def tick(self, *args, **kwargs):
        """Compatibility alias — delegates to step()."""
        return self.step()

    def _update_towers(self):
        """Towers fire at enemy squads."""
        for tower in self.towers:
            targets = self.player_squads if tower.team != 0 else self.enemy_squads
            tower.update(targets)

    def _update_gate_damage(self):
        """Gate takes damage from nearby attacking melee units."""
        for gate in self.gates:
            if gate is None or gate.destroyed:
                continue
            attacker_squads = (self.player_squads if self.player_is_attacker
                               else self.enemy_squads)
            for sq in attacker_squads:
                if sq.is_destroyed or sq.state != SquadState.FIGHTING:
                    continue
                cx, cy = sq.center
                gx = gate.x
                gy = gate.y + gate.height // 2
                if distance(cx, cy, gx, gy) < 80:
                    dps = sq.alive_count * 0.3
                    gate.take_damage(dps)

    def _resolve_wall_collisions(self):
        """Push soldiers out of wall segments."""
        for sq in self.all_squads:
            if sq.is_destroyed:
                continue
            for s in sq.alive_soldiers:
                for wall in self.walls:
                    if wall.contains(s.x, s.y):
                        left_dist = abs(s.x - wall.x)
                        right_dist = abs(s.x - (wall.x + wall.width))
                        if left_dist < right_dist:
                            s.x = wall.x - 2
                        else:
                            s.x = wall.x + wall.width + 2

    def _resolve_gate_collisions(self):
        """Push soldiers out of intact gates."""
        for gate in self.gates:
            if gate is None or gate.destroyed:
                continue
            gx, gy, gw, gh = gate.rect
            for sq in self.all_squads:
                if sq.is_destroyed:
                    continue
                for s in sq.alive_soldiers:
                    if gx <= s.x <= gx + gw and gy <= s.y <= gy + gh:
                        left_dist = abs(s.x - gx)
                        right_dist = abs(s.x - (gx + gw))
                        if left_dist < right_dist:
                            s.x = gx - 2
                        else:
                            s.x = gx + gw + 2
