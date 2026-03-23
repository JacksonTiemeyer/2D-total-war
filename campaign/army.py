"""Campaign army - a roaming force on the world map (Mount & Blade style)."""

import math
import random
import pygame
from core.contracts import ArmyBattlePayload, GeneralBattlePayload
from core.settings import (
    ARMY_ICON_RADIUS, CAMPAIGN_MOVE_SPEED,
    TEAM_COLORS, TEAM_COLORS_LIGHT, WHITE, GOLD, DARK_GREY,
    STARTING_GOLD,
    ARMY_SIZE_BASE, ARMY_SIZE_PER_LEVEL, ARMY_SIZE_MAX,
)
from core.utils import distance, normalize
from data.unit_types import (
    SWORDSMEN, ARCHERS, SPEARMEN, MILITIA, LIGHT_CAVALRY,
    GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_ROSTER,
    RACE_ROSTER, RACE_HEROES,
)


class CampaignSquad:
    """A squad on the campaign map with mutable soldier count and veterancy."""

    # Veterancy ranks: (name, min_battles, atk_mult, def_mult, morale_bonus, exhaustion_mult)
    VETERANCY_RANKS = [
        ("Raw",       0,  1.0,  1.0,  0,  1.0),
        ("Trained",   1,  1.05, 1.05, 0,  1.0),
        ("Veteran",   3,  1.10, 1.10, 5,  1.0),
        ("Elite",     6,  1.15, 1.15, 10, 0.9),
        ("Legendary", 10, 1.25, 1.25, 15, 0.8),
    ]

    def __init__(self, unit_stats, current_count=None):
        self.unit_stats = unit_stats
        self.max_count = unit_stats.squad_size
        self.current_count = current_count if current_count is not None else self.max_count
        self.battles_survived = 0
        self.total_kills = 0

    @property
    def veterancy_rank(self):
        """Return (name, atk_mult, def_mult, morale_bonus, exhaustion_mult)."""
        rank = self.VETERANCY_RANKS[0]
        for r in self.VETERANCY_RANKS:
            if self.battles_survived >= r[1]:
                rank = r
        return rank

    @property
    def rank_name(self):
        return self.veterancy_rank[0]

    @property
    def rank_index(self):
        """0-4 index for chevron display."""
        for i, r in enumerate(self.VETERANCY_RANKS):
            if self.battles_survived < r[1]:
                return max(0, i - 1)
        return len(self.VETERANCY_RANKS) - 1

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
        self.current_status = "Idle"
        self.current_location = "Unknown"
        self.current_region = "Wilderness"

    @property
    def total_soldiers(self):
        return sum(sq.current_count for sq in self.squads)

    @property
    def army_strength(self):
        return sum(sq.strength for sq in self.squads)

    @property
    def upkeep(self):
        return sum(sq.unit_stats.upkeep for sq in self.squads)

    @property
    def army_size_limit(self):
        """B11: Army size limit based on general level."""
        return min(ARMY_SIZE_MAX,
                   ARMY_SIZE_BASE + (self.general_level - 1) * ARMY_SIZE_PER_LEVEL)

    @property
    def can_recruit(self):
        """B11: Check if army can accept more soldiers."""
        return self.total_soldiers < self.army_size_limit

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

    def get_battle_data(self, player_class=None):
        """Convert to battle deployment format.

        Uses current_count instead of max squad_size for understrength squads.
        """
        return self.get_battle_payload(player_class=player_class).to_legacy_dict()

    def get_battle_payload(self, player_class=None):
        """Return a typed battle deployment payload for this army."""
        squad_list = []
        for sq in self.squads:
            if sq.current_count > 0:
                rank = sq.veterancy_rank
                vet_data = {
                    "rank_name": rank[0],
                    "rank_index": sq.rank_index,
                    "atk_mult": rank[2],
                    "def_mult": rank[3],
                    "morale_bonus": rank[4],
                    "exhaustion_mult": rank[5],
                }
                squad_list.append((sq.unit_stats, sq.current_count, vet_data))
        return ArmyBattlePayload(
            squads=squad_list,
            general=GeneralBattlePayload(
                name=self.general_name,
                stats=self.general_stats,
                xp=self.general_xp,
                level=self.general_level,
                player_class=player_class,
            ),
        )

    def apply_battle_results(self, battle_scene):
        """Read battle results and update campaign squads."""
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

        # Note: General XP/level is updated post-battle by _award_post_battle_xp
        # in main.py. Do NOT overwrite it here from the battle general's XP,
        # as that would discard the post-battle XP bonus calculation.

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
            from core.utils import get_font
            font = get_font(max(14, camera.scale(15)))
            text = font.render(f"{self.name} ({self.total_soldiers})", True, light)
            surface.blit(text, (sx - text.get_width() // 2, sy + r + 4))

    def draw_info_panel(self, surface, x, y, font, small_font):
        texts = [
            (font, f"{self.name}", GOLD),
            (small_font, f"Strength: {self.army_strength}", WHITE),
            (small_font, f"Soldiers: {self.total_soldiers}/{self.army_size_limit}", WHITE),
            (small_font, f"Gold: {self.gold}", (255, 215, 0)),
            (small_font, f"Upkeep: {self.upkeep}/week", (200, 150, 100)),
            (small_font, f"General: {self.general_name} ({self.general_stats.name}) Lv{self.general_level}", WHITE),
            (small_font, f"Status: {self.current_status}", WHITE),
            (small_font, f"Location: {self.current_location}", WHITE),
        ]
        # D3: Supply status
        morale = getattr(self, 'campaign_morale', 100)
        if morale < 100:
            morale_color = (200, 50, 50) if morale < 50 else (220, 180, 50)
            texts.append((small_font, f"Supply Morale: {morale}", morale_color))
        texts.append((small_font, "--- Squads ---", (180, 180, 180)))
        for sq in self.squads:
            chevrons = ">" * sq.rank_index if sq.rank_index > 0 else ""
            wound = f" [{sq.current_count}/{sq.max_count}]" if sq.is_understrength else ""
            rank = f" [{sq.rank_name}]" if sq.battles_survived > 0 else ""
            texts.append((small_font,
                          f"  {chevrons}{sq.unit_stats.name} ({sq.current_count})"
                          f" K:{sq.total_kills}{rank}{wound}",
                          WHITE))

        for fnt, text, color in texts:
            rendered = fnt.render(text, True, color)
            surface.blit(rendered, (x, y))
            y += rendered.get_height() + 2
        return y

    def update_campaign_context(self, settlements, terrain_type=None):
        """Track army location text for map UI and AI behavior feedback."""
        nearest = None
        nearest_dist = float("inf")
        for settlement in settlements:
            d = distance(self.x, self.y, settlement.x, settlement.y)
            if d < nearest_dist:
                nearest = settlement
                nearest_dist = d

        if nearest and nearest_dist < 120:
            self.current_location = nearest.name
            self.current_region = nearest.settlement_type.title()
        elif nearest:
            self.current_location = f"Near {nearest.name}"
            self.current_region = terrain_type.title() if terrain_type else "Borderlands"
        else:
            self.current_location = terrain_type.title() if terrain_type else "Wilderness"
            self.current_region = self.current_location


def create_default_player_army():
    """B2: Player starts as independent mercenary lord with a small warband."""
    army = Army("Your Warband", 0, 800, 800, is_player=True)
    army.gold = STARTING_GOLD
    army.general_stats = GENERAL_COMMANDER
    # Small starting force - mercenary feel (fits within 60 soldier limit)
    army.add_squad(SWORDSMEN)   # 24
    army.add_squad(ARCHERS)     # 20
    army.add_squad(LIGHT_CAVALRY)  # 12 = 56 total
    return army


def create_racial_player_army(player_character):
    """Create player starting army based on race selection."""
    from data.unit_types import RACE_ROSTER, RACE_HEROES
    from campaign.player import get_tier_for_level
    from core.settings import STARTING_GOLD

    army = Army(f"{player_character.name}'s Warband", 0, 800, 800, is_player=True)
    army.gold = STARTING_GOLD
    if player_character.trait == "merchant_prince":
        army.gold *= 2

    # Set general stats from racial hero list
    heroes = RACE_HEROES.get(player_character.race, GENERAL_ROSTER)
    army.general_stats = heroes[0] if heroes else GENERAL_COMMANDER
    army.general_name = player_character.name

    # Get racial roster
    roster = RACE_ROSTER.get(player_character.race, [])
    if not roster:
        # Fallback to human roster
        roster = RACE_ROSTER.get("human", [SWORDSMEN, ARCHERS, LIGHT_CAVALRY])

    # Pick 2-3 starting units from the race's roster (first few = basic units)
    # Take first 2 basic units + 1 if roster is large enough
    if len(roster) >= 3:
        army.add_squad(roster[0])  # basic infantry
        army.add_squad(roster[1])  # second unit type
        army.add_squad(roster[2])  # third unit type
    elif len(roster) >= 2:
        army.add_squad(roster[0])
        army.add_squad(roster[1])
    else:
        army.add_squad(roster[0])

    return army


def create_enemy_army(name, team, x, y, difficulty=1):
    """Create an AI army using the appropriate racial roster."""
    army = Army(name, team, x, y)

    # Map team to race for roster lookup
    _TEAM_TO_RACE = {
        1: "human", 2: "high_elf", 3: "wood_elf", 4: "sea_elf",
        5: "snow_elf", 6: "dark_elf", 7: "dwarf", 8: "orc",
        9: "undead", 10: "troll_ogre", 11: "beastfolk",
        12: "goblin", 13: "demon",
    }
    race_id = _TEAM_TO_RACE.get(team)
    heroes = RACE_HEROES.get(race_id, GENERAL_ROSTER) if race_id else GENERAL_ROSTER
    army.general_stats = random.choice(heroes)

    roster = RACE_ROSTER.get(race_id) if race_id else None
    if roster:
        # Pick from racial roster
        basic = roster[:max(3, len(roster) // 2)]  # first half = basic units
        for _ in range(2 + difficulty):
            army.add_squad(random.choice(basic))
        if difficulty >= 2 and len(roster) > 3:
            # Add an elite unit
            army.add_squad(random.choice(roster[len(roster) // 2:]))
    else:
        # Fallback to legacy units
        base_units = [MILITIA, SWORDSMEN, SPEARMEN, ARCHERS]
        for _ in range(2 + difficulty):
            army.add_squad(random.choice(base_units))
        if difficulty >= 2:
            army.add_squad(LIGHT_CAVALRY)

    return army
