"""Battleground: localized micro-battle zone between two squads.

This module implements a simplified, localized combat sandbox between two
squads. Within the battleground, soldiers are locked to their squad's
formation offsets but engage in micro-melee and pushing within a bounded zone.
"""

import math
from core.utils import distance
from core.settings import MELEE_RANGE


class Battleground:
    def __init__(self, squad_a, squad_b):
        self.a = squad_a
        self.b = squad_b
        # Link back
        self.a.battleground = self
        self.b.battleground = self
        self.active = True
        # Initial center between squads
        self.center_x = (self.a.center[0] + self.b.center[0]) * 0.5
        self.center_y = (self.a.center[1] + self.b.center[1]) * 0.5
        self.heading = 0.0  # direction squads feel like they're pushing toward

    def update(self):
        if not self.active:
            return
        if self.a.is_destroyed or self.b.is_destroyed:
            self.terminate()
            return

        # Determine battleground heading from current centers
        ax, ay = self.a.center
        bx, by = self.b.center
        dx = bx - ax
        dy = by - ay
        if dx == 0 and dy == 0:
            self.heading = 0.0
        else:
            self.heading = math.atan2(dy, dx)

        # Battleground center as the midpoint between squad centers
        self.center_x = (ax + bx) * 0.5
        self.center_y = (ay + by) * 0.5

        # Per-soldier positioning: keep squad in formation around battleground center
        # and keep facing aligned with heading.
        cos_a = math.cos(self.heading)
        sin_a = math.sin(self.heading)

        # Helper to rotate formation offset around center
        def rotate_off(xo, yo):
            return (xo * cos_a - yo * sin_a, xo * sin_a + yo * cos_a)

        # Reposition all soldiers in A
        for s in self.a.alive_soldiers:
            rox, roy = rotate_off(s.formation_x, s.formation_y)
            s.x = self.center_x + rox
            s.y = self.center_y + roy
            s.facing_angle = self.heading

        # Reposition all soldiers in B
        for s in self.b.alive_soldiers:
            rox, roy = rotate_off(s.formation_x, s.formation_y)
            s.x = self.center_x + rox
            s.y = self.center_y + roy
            s.facing_angle = self.heading

        # Lightweight micro-melee inside battleground: any close pairs engage
        for sa in self.a.alive_soldiers:
            if sa.attack_cooldown > 0:
                continue
            target = None
            best = None
            best_dist = MELEE_RANGE * 1.5
            for sb in self.b.alive_soldiers:
                d = distance(sa.x, sa.y, sb.x, sb.y)
                if d < best_dist:
                    best_dist = d
                    best = sb
            if best and best_dist <= MELEE_RANGE:
                dmg = sa.attack(best, is_charging=False)
                if dmg > 0 and not best.alive:
                    self.b.kills += 1
                    self.b._dying_soldiers.append(best)
                    self.b.on_casualty()

        # End condition: terminate if one side is all dead
        if self.a.alive_count == 0 or self.b.alive_count == 0:
            self.terminate()

    def terminate(self):
        self.active = False
        # Clear links back to battlegrounds
        if self.a and self.a.battleground is self:
            self.a.battleground = None
        if self.b and self.b.battleground is self:
            self.b.battleground = None
        self.a = None
        self.b = None
