"""Campaign army - a roaming force on the world map (Mount & Blade style)."""

import math
import random
import pygame
from core.settings import (
    ARMY_ICON_RADIUS, CAMPAIGN_MOVE_SPEED,
    TEAM_COLORS, TEAM_COLORS_LIGHT, WHITE, GOLD, DARK_GREY,
    STARTING_GOLD,
)
from core.utils import distance, normalize
from data.unit_types import (
    SWORDSMEN, ARCHERS, SPEARMEN, MILITIA, LIGHT_CAVALRY,
    GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_ROSTER,
)


class Army:
    def __init__(self, name, team, x, y, is_player=False):
        self.name = name
        self.team = team
        self.x = x
        self.y = y
        self.is_player = is_player
        self.selected = False
        self.target_x = x
        self.target_y = y
        self.moving = False
        self.speed = CAMPAIGN_MOVE_SPEED

        # Army composition: list of (UnitStats, count) - count unused for now,
        # each entry = one squad
        self.squads = []
        self.general_name = name
        self.general_stats = GENERAL_COMMANDER

        # Economy
        self.gold = STARTING_GOLD if is_player else 300

    @property
    def total_soldiers(self):
        return sum(stats.squad_size for stats, _ in self.squads)

    @property
    def army_strength(self):
        """Abstract power rating."""
        strength = 0
        for stats, _ in self.squads:
            strength += stats.squad_size * (stats.melee_attack + stats.ranged_attack +
                                             stats.melee_defense + stats.health / 10)
        return int(strength)

    @property
    def upkeep(self):
        return sum(stats.upkeep for stats, _ in self.squads)

    def add_squad(self, unit_stats):
        self.squads.append((unit_stats, 1))

    def remove_squad(self, index):
        if 0 <= index < len(self.squads):
            self.squads.pop(index)

    def give_move_order(self, tx, ty):
        self.target_x = tx
        self.target_y = ty
        self.moving = True

    def update(self):
        if not self.moving:
            return
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 5:
            self.moving = False
            return
        nx, ny = normalize(dx, dy)
        self.x += nx * self.speed
        self.y += ny * self.speed

    def get_battle_data(self):
        """Convert to battle deployment format."""
        return {
            "squads": list(self.squads),
            "general": {
                "name": self.general_name,
                "stats": self.general_stats,
            },
        }

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        r = camera.scale(ARMY_ICON_RADIUS)
        color = TEAM_COLORS[self.team]
        light = TEAM_COLORS_LIGHT[self.team]

        # Army icon - shield shape
        points = [
            (sx, sy - r),
            (sx + r, sy - r // 2),
            (sx + r, sy + r // 2),
            (sx, sy + r),
            (sx - r, sy + r // 2),
            (sx - r, sy - r // 2),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, WHITE, points, 2)

        if self.is_player:
            pygame.draw.polygon(surface, GOLD, points, 2)

        # Selection
        if self.selected:
            pygame.draw.circle(surface, GOLD, (sx, sy), r + 6, 2)

        # Name and strength
        if camera.zoom > 0.35:
            font = pygame.font.SysFont(None, max(14, camera.scale(15)))
            text = font.render(f"{self.name} ({self.total_soldiers})", True, light)
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 4))

    def draw_info_panel(self, surface, x, y, font, small_font):
        """Draw detailed info panel."""
        texts = [
            (font, f"{self.name}", GOLD),
            (small_font, f"Strength: {self.army_strength}", WHITE),
            (small_font, f"Soldiers: {self.total_soldiers}", WHITE),
            (small_font, f"Gold: {self.gold}", (255, 215, 0)),
            (small_font, f"Upkeep: {self.upkeep}/turn", (200, 150, 100)),
            (small_font, f"General: {self.general_name} ({self.general_stats.name})", WHITE),
            (small_font, "--- Squads ---", (180, 180, 180)),
        ]
        for stats, _ in self.squads:
            texts.append((small_font, f"  {stats.name} ({stats.squad_size} soldiers)", WHITE))

        for fnt, text, color in texts:
            rendered = fnt.render(text, True, color)
            surface.blit(rendered, (x, y))
            y += rendered.get_height() + 2
        return y


def create_default_player_army():
    army = Army("Your Warband", 0, 400, 500, is_player=True)
    army.gold = STARTING_GOLD
    army.general_stats = GENERAL_COMMANDER
    army.add_squad(SWORDSMEN)
    army.add_squad(SWORDSMEN)
    army.add_squad(SPEARMEN)
    army.add_squad(ARCHERS)
    army.add_squad(MILITIA)
    return army


def create_enemy_army(name, team, x, y, difficulty=1):
    army = Army(name, team, x, y)
    army.general_stats = random.choice(GENERAL_ROSTER)
    # Scale army based on difficulty
    base_units = [MILITIA, SWORDSMEN, SPEARMEN, ARCHERS]
    for _ in range(2 + difficulty):
        army.add_squad(random.choice(base_units))
    if difficulty >= 2:
        army.add_squad(LIGHT_CAVALRY)
    return army
