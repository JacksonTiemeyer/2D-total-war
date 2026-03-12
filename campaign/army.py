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


class CampaignSquad:
    """A squad on the campaign map with mutable soldier count and veterancy."""

    def __init__(self, unit_stats, current_count=None):
        self.unit_stats = unit_stats
        self.max_count = unit_stats.squad_size
        self.current_count = current_count if current_count is not None else self.max_count
        self.battles_survived = 0
        self.total_kills = 0

    @property
    def is_understrength(self):
        return self.current_count < self.max_count

    @property
    def is_destroyed(self):
        return self.current_count <= 0

    @property
    def strength(self):
        s = self.unit_stats
        return int(self.current_count * (s.melee_attack + s.ranged_attack +
                                          s.melee_defense + s.health / 10))

    def apply_battle_results(self, alive_count, kills):
        """Update squad after a battle."""
        self.current_count = alive_count
        self.total_kills += kills
        if alive_count > 0:
            self.battles_survived += 1

    def replenish(self, count):
        """Restore soldiers up to max."""
        self.current_count = min(self.max_count, self.current_count + count)


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

        self.squads = []  # list of CampaignSquad
        self.general_name = name
        self.general_stats = GENERAL_COMMANDER
        self.general_xp = 0
        self.general_level = 1

        # Economy
        self.gold = STARTING_GOLD if is_player else 300

    @property
    def total_soldiers(self):
        return sum(sq.current_count for sq in self.squads)

    @property
    def army_strength(self):
        return sum(sq.strength for sq in self.squads)

    @property
    def upkeep(self):
        return sum(sq.unit_stats.upkeep for sq in self.squads)

    def add_squad(self, unit_stats):
        self.squads.append(CampaignSquad(unit_stats))

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
        """Convert to battle deployment format.

        Uses current_count instead of max squad_size for understrength squads.
        """
        squad_list = []
        for sq in self.squads:
            if sq.current_count > 0:
                squad_list.append((sq.unit_stats, sq.current_count))
        return {
            "squads": squad_list,
            "general": {
                "name": self.general_name,
                "stats": self.general_stats,
                "xp": self.general_xp,
                "level": self.general_level,
            },
        }

    def apply_battle_results(self, battle_scene):
        """Read battle results and update campaign squads."""
        # Map battle squads back to campaign squads by index
        battle_squads = [sq for sq in battle_scene.player_squads
                         if battle_scene.player_squads[0].team == self.squads[0].unit_stats.squad_size
                         ] if False else []  # placeholder - use team matching

        # Match by order: campaign squad i -> battle squad i
        team = 0 if self.is_player else 1
        battle_team_squads = [sq for sq in (
            battle_scene.player_squads if team == 0 else battle_scene.enemy_squads
        )]

        for i, csq in enumerate(self.squads):
            if i < len(battle_team_squads):
                bsq = battle_team_squads[i]
                csq.apply_battle_results(bsq.alive_count, bsq.kills)

        # Remove destroyed squads
        self.squads = [sq for sq in self.squads if not sq.is_destroyed]

        # Update general XP/level
        all_generals = battle_scene.all_generals + getattr(battle_scene, '_dead_generals', [])
        for g in all_generals:
            if g.team == team:
                self.general_xp = g.xp
                self.general_level = g.level
                break

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

        if self.selected:
            pygame.draw.circle(surface, GOLD, (sx, sy), r + 6, 2)

        if camera.zoom > 0.35:
            font = pygame.font.SysFont(None, max(14, camera.scale(15)))
            text = font.render(f"{self.name} ({self.total_soldiers})", True, light)
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 4))

    def draw_info_panel(self, surface, x, y, font, small_font):
        texts = [
            (font, f"{self.name}", GOLD),
            (small_font, f"Strength: {self.army_strength}", WHITE),
            (small_font, f"Soldiers: {self.total_soldiers}", WHITE),
            (small_font, f"Gold: {self.gold}", (255, 215, 0)),
            (small_font, f"Upkeep: {self.upkeep}/turn", (200, 150, 100)),
            (small_font, f"General: {self.general_name} ({self.general_stats.name}) Lv{self.general_level}", WHITE),
            (small_font, "--- Squads ---", (180, 180, 180)),
        ]
        for sq in self.squads:
            status = ""
            if sq.is_understrength:
                status = f" [Wounded {sq.current_count}/{sq.max_count}]"
            elif sq.battles_survived > 0:
                status = f" [Vet x{sq.battles_survived}]"
            texts.append((small_font,
                          f"  {sq.unit_stats.name} ({sq.current_count}) K:{sq.total_kills}{status}",
                          WHITE))

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
    base_units = [MILITIA, SWORDSMEN, SPEARMEN, ARCHERS]
    for _ in range(2 + difficulty):
        army.add_squad(random.choice(base_units))
    if difficulty >= 2:
        army.add_squad(LIGHT_CAVALRY)
    return army
