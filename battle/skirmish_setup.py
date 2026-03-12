"""Skirmish mode - army builder for standalone battles."""

import random
import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, GOLD, YELLOW, GREY,
)
from data.unit_types import (
    ALL_RECRUITABLE, GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST,
    GENERAL_ROSTER,
)


BUDGET_OPTIONS = [500, 1000, 1500, 2000, 3000]
GENERAL_OPTIONS = [GENERAL_COMMANDER, GENERAL_CHAMPION, GENERAL_STRATEGIST]
GENERAL_NAMES = ["Commander", "Champion", "Strategist"]


class SkirmishSetup:
    """Army builder UI for skirmish mode."""

    def __init__(self):
        self.budget = 1000
        self.budget_index = 1
        self.player_squads = []  # list of UnitStats
        self.general_index = 0   # which general type
        self.scroll_offset = 0
        self.spent = 0

    @property
    def remaining(self):
        return self.budget - self.spent

    def handle_event(self, event):
        """Handle input. Returns (player_data, enemy_data) when fight starts, else None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.budget_index = max(0, self.budget_index - 1)
                self.budget = BUDGET_OPTIONS[self.budget_index]
                self._trim_to_budget()
            elif event.key == pygame.K_RIGHT:
                self.budget_index = min(len(BUDGET_OPTIONS) - 1, self.budget_index + 1)
                self.budget = BUDGET_OPTIONS[self.budget_index]
                self._trim_to_budget()
            elif event.key == pygame.K_g:
                self.general_index = (self.general_index + 1) % len(GENERAL_OPTIONS)
            elif event.key == pygame.K_BACKSPACE:
                if self.player_squads:
                    removed = self.player_squads.pop()
                    self.spent -= removed.cost
            elif event.key == pygame.K_RETURN:
                if self.player_squads:
                    return self._start_battle()

            # Number keys 1-9 to add units
            num = event.key - pygame.K_1
            if 0 <= num < len(ALL_RECRUITABLE):
                unit = ALL_RECRUITABLE[num]
                if self.spent + unit.cost <= self.budget:
                    self.player_squads.append(unit)
                    self.spent += unit.cost

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click(event.pos)

        return None

    def _handle_click(self, pos):
        mx, my = pos
        # Check unit list clicks (left side)
        list_y_start = 160
        for i, unit in enumerate(ALL_RECRUITABLE):
            y = list_y_start + i * 28
            if 40 <= mx <= 500 and y <= my <= y + 26:
                if self.spent + unit.cost <= self.budget:
                    self.player_squads.append(unit)
                    self.spent += unit.cost
                return

        # Check remove buttons on right side (army list)
        army_y_start = 160
        for i, unit in enumerate(self.player_squads):
            y = army_y_start + i * 24
            # "X" button at end of line
            if SCREEN_WIDTH - 80 <= mx <= SCREEN_WIDTH - 40 and y <= my <= y + 22:
                self.player_squads.pop(i)
                self.spent -= unit.cost
                return

        # Budget arrows
        if 250 <= my <= 280:
            if 200 <= mx <= 230:  # left arrow
                self.budget_index = max(0, self.budget_index - 1)
                self.budget = BUDGET_OPTIONS[self.budget_index]
                self._trim_to_budget()
            elif 370 <= mx <= 400:  # right arrow
                self.budget_index = min(len(BUDGET_OPTIONS) - 1, self.budget_index + 1)
                self.budget = BUDGET_OPTIONS[self.budget_index]
                self._trim_to_budget()

        # Fight button
        if (SCREEN_WIDTH // 2 - 80 <= mx <= SCREEN_WIDTH // 2 + 80 and
                SCREEN_HEIGHT - 70 <= my <= SCREEN_HEIGHT - 30):
            if self.player_squads:
                pass  # handled by ENTER key in handle_event

    def _trim_to_budget(self):
        while self.spent > self.budget and self.player_squads:
            removed = self.player_squads.pop()
            self.spent -= removed.cost

    def _generate_enemy(self):
        """Generate an enemy army that roughly matches the player's budget."""
        enemy_squads = []
        enemy_spent = 0
        target = self.budget
        available = list(ALL_RECRUITABLE)
        random.shuffle(available)

        # Fill with a reasonable mix
        while enemy_spent < target * 0.85:
            unit = random.choice(available)
            if enemy_spent + unit.cost <= target:
                enemy_squads.append(unit)
                enemy_spent += unit.cost
            else:
                # Try a cheaper unit
                cheap = [u for u in available if enemy_spent + u.cost <= target]
                if not cheap:
                    break
                enemy_squads.append(random.choice(cheap))
                enemy_spent += enemy_squads[-1].cost

        return enemy_squads

    def _start_battle(self):
        """Build battle data dicts for player and enemy."""
        gen_stats = GENERAL_OPTIONS[self.general_index]
        player_data = {
            "squads": [(unit, 1) for unit in self.player_squads],
            "general": {"name": "Player General", "stats": gen_stats},
        }

        enemy_squads = self._generate_enemy()
        enemy_gen = random.choice(GENERAL_ROSTER)
        enemy_data = {
            "squads": [(unit, 1) for unit in enemy_squads],
            "general": {"name": "Enemy General", "stats": enemy_gen},
        }

        return (player_data, enemy_data)

    def draw(self, surface):
        surface.fill((25, 20, 18))

        font = pygame.font.SysFont(None, 40)
        med = pygame.font.SysFont(None, 24)
        small = pygame.font.SysFont(None, 20)
        tiny = pygame.font.SysFont(None, 17)

        # Title
        title = font.render("SKIRMISH - Army Builder", True, GOLD)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Budget selector
        budget_label = med.render("Budget:", True, WHITE)
        surface.blit(budget_label, (200, 70))
        budget_val = med.render(f"< {self.budget} Gold >", True, GOLD)
        surface.blit(budget_val, (290, 70))

        remaining = med.render(f"Remaining: {self.remaining}", True,
                               (100, 220, 100) if self.remaining >= 0 else (220, 60, 60))
        surface.blit(remaining, (500, 70))

        # General selector
        gen_label = med.render(f"General: {GENERAL_NAMES[self.general_index]} [G to cycle]", True, GOLD)
        surface.blit(gen_label, (200, 100))

        # Divider
        pygame.draw.line(surface, (60, 60, 60), (0, 140), (SCREEN_WIDTH, 140))

        # Left column: Available units
        header_left = med.render("Available Units (click or press 1-9)", True, (100, 150, 255))
        surface.blit(header_left, (40, 145))

        y = 170
        for i, unit in enumerate(ALL_RECRUITABLE):
            key = str(i + 1) if i < 9 else ""
            affordable = self.remaining >= unit.cost
            color = WHITE if affordable else (80, 80, 80)
            text = tiny.render(
                f"[{key}] {unit.name:<18} Cost:{unit.cost:<5} "
                f"HP:{unit.health} ATK:{unit.melee_attack} DEF:{unit.melee_defense} "
                f"WS:{unit.weapon_strength} AP:{unit.armor_penetration}%"
                f"{' RNG:'+str(unit.ranged_attack) if unit.ranged_attack else ''}"
                f"{' Brace' if unit.can_brace else ''}"
                f"  Size:{unit.squad_size}",
                True, color)
            surface.blit(text, (40, y))
            y += 22

        # Right column: Your army
        col_right = SCREEN_WIDTH // 2 + 40
        header_right = med.render("Your Army [BACKSPACE to remove last]", True, (100, 255, 100))
        surface.blit(header_right, (col_right, 145))

        y = 170
        for i, unit in enumerate(self.player_squads):
            text = tiny.render(f"{unit.name} ({unit.squad_size}) - {unit.cost}g", True, WHITE)
            surface.blit(text, (col_right, y))
            # Remove button
            x_btn = tiny.render("[X]", True, (200, 80, 80))
            surface.blit(x_btn, (SCREEN_WIDTH - 70, y))
            y += 22

        if not self.player_squads:
            empty = small.render("No units yet - add some!", True, (120, 120, 120))
            surface.blit(empty, (col_right, y))

        # Army summary
        total_soldiers = sum(u.squad_size for u in self.player_squads)
        summary_y = SCREEN_HEIGHT - 110
        summary = small.render(
            f"Squads: {len(self.player_squads)}  |  Soldiers: {total_soldiers}  |  "
            f"Spent: {self.spent}/{self.budget}",
            True, WHITE)
        surface.blit(summary, (SCREEN_WIDTH // 2 - summary.get_width() // 2, summary_y))

        # Fight button
        btn_y = SCREEN_HEIGHT - 70
        btn_color = GOLD if self.player_squads else (80, 80, 80)
        btn_text = med.render("[ENTER] Fight!", True, btn_color)
        if pygame.time.get_ticks() % 1000 < 700 or not self.player_squads:
            surface.blit(btn_text, (SCREEN_WIDTH // 2 - btn_text.get_width() // 2, btn_y))

        # Back
        back = small.render("[ESC] Back to Menu", True, (140, 140, 140))
        surface.blit(back, (SCREEN_WIDTH // 2 - back.get_width() // 2, SCREEN_HEIGHT - 30))

        # Controls
        ctrl = tiny.render(
            "[LEFT/RIGHT] Budget  [1-9] Add Unit  [G] General  [BACKSPACE] Remove  [ENTER] Fight  [ESC] Back",
            True, (100, 100, 100))
        surface.blit(ctrl, (SCREEN_WIDTH // 2 - ctrl.get_width() // 2, SCREEN_HEIGHT - 12))
