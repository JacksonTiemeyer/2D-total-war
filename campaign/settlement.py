"""Settlements on the campaign map."""

import pygame
from core.settings import (
    SETTLEMENT_RADIUS, TEAM_COLORS, INCOME_PER_SETTLEMENT,
    WHITE, GREY, DARK_GREY, BROWN, GOLD,
)
from data.unit_types import ALL_RECRUITABLE, FACTION_SPECIALTY_UNITS


class SettlementType:
    VILLAGE = "village"
    TOWN = "town"
    CASTLE = "castle"


class Settlement:
    def __init__(self, name, x, y, owner=None,
                 settlement_type=SettlementType.TOWN):
        self.name = name
        self.x = x
        self.y = y
        self.owner = owner  # team index or None
        self.settlement_type = settlement_type
        self.garrison_strength = 50  # abstract defense value
        self.income = INCOME_PER_SETTLEMENT
        self.selected = False

        # Recruitment pool - refreshes each turn
        if settlement_type == SettlementType.CASTLE:
            self.income = int(INCOME_PER_SETTLEMENT * 0.5)
            self.garrison_strength = 120
            self.recruitment_slots = 4
        elif settlement_type == SettlementType.TOWN:
            self.income = int(INCOME_PER_SETTLEMENT * 1.5)
            self.garrison_strength = 60
            self.recruitment_slots = 3
        else:  # village
            self.income = int(INCOME_PER_SETTLEMENT * 0.7)
            self.garrison_strength = 30
            self.recruitment_slots = 2

        self.available_recruits = []
        self.refresh_recruits()

    def refresh_recruits(self):
        """Refresh the available recruitment pool.

        Faction-owned settlements include that faction's specialty units
        in the pool. Castles guarantee at least one specialty unit.
        """
        import random
        pool = ALL_RECRUITABLE[:]
        specialty = FACTION_SPECIALTY_UNITS.get(self.owner, [])
        if specialty:
            pool = pool + specialty
        random.shuffle(pool)
        picks = pool[:self.recruitment_slots]
        # Castles guarantee a faction specialty unit if available
        if (self.settlement_type == SettlementType.CASTLE
                and specialty
                and not any(u in specialty for u in picks)):
            picks[-1] = random.choice(specialty)
        self.available_recruits = picks

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        r = camera.scale(SETTLEMENT_RADIUS)

        # Different shapes for different types
        if self.settlement_type == SettlementType.CASTLE:
            # Square with battlements
            color = TEAM_COLORS.get(self.owner, GREY)
            rect = (sx - r, sy - r, r * 2, r * 2)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, WHITE, rect, 2)
            # Battlements
            bsize = max(2, r // 3)
            for bx in range(sx - r, sx + r, bsize * 2):
                pygame.draw.rect(surface, WHITE, (bx, sy - r - bsize, bsize, bsize))
        elif self.settlement_type == SettlementType.TOWN:
            # Circle
            color = TEAM_COLORS.get(self.owner, GREY)
            pygame.draw.circle(surface, color, (sx, sy), r)
            pygame.draw.circle(surface, WHITE, (sx, sy), r, 2)
        else:
            # Small circle for village
            color = TEAM_COLORS.get(self.owner, GREY)
            pygame.draw.circle(surface, color, (sx, sy), r // 2 + 2)
            pygame.draw.circle(surface, WHITE, (sx, sy), r // 2 + 2, 1)

        # Selection
        if self.selected:
            pygame.draw.circle(surface, GOLD, (sx, sy), r + 6, 2)

        # Name
        if camera.zoom > 0.4:
            font = pygame.font.SysFont(None, max(14, camera.scale(16)))
            text = font.render(self.name, True, WHITE)
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 4))
