"""Character creation UI — race, class, trait, and name selection.

Displayed as a new game state between MAIN_MENU and CAMPAIGN.
Produces a PlayerCharacter object that gets attached to the campaign.

Full implementation in Batch 9.
"""

import pygame
from core.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, GOLD
from core.utils import get_font
from campaign.player import (
    PlayerCharacter, ALL_CLASSES, CLASS_DESCRIPTIONS, PLAYER_TRAITS,
)
from data.races import ALL_PLAYABLE_RACES


# ── Creation Steps ──────────────────────────────────────────────────────

STEP_RACE = 0
STEP_CLASS = 1
STEP_TRAIT = 2
STEP_NAME = 3
STEP_CONFIRM = 4

RACE_DISPLAY_NAMES = {
    "human": "Human",
    "high_elf": "High Elf",
    "wood_elf": "Wood Elf",
    "sea_elf": "Sea Elf",
    "snow_elf": "Snow Elf",
    "dark_elf": "Dark Elf",
    "dwarf": "Dwarf",
    "orc": "Orc",
    "undead": "Undead",
    "troll_ogre": "Troll / Ogre",
    "beastfolk": "Beastfolk",
}

CLASS_DISPLAY_NAMES = {
    "warlord": "Warlord",
    "battlemage": "Battlemage",
    "champion": "Champion",
    "rogue": "Rogue",
    "engineer": "Engineer",
    "necromancer": "Necromancer",
}


class CharacterCreation:
    """Handles the character creation flow and UI.

    Full rendering and input handling will be implemented in Batch 9.
    This scaffold establishes the data flow and state machine.
    """

    def __init__(self):
        self.step = STEP_RACE
        self.selected_race = None
        self.selected_class = None
        self.selected_trait = None
        self.player_name = ""
        self.finished = False
        self._result = None

        # Selection indices for keyboard navigation
        self._race_index = 0
        self._class_index = 0
        self._trait_index = 0

    @property
    def result(self):
        """Returns the created PlayerCharacter, or None if not finished."""
        return self._result

    def handle_event(self, event):
        """Handle input for the current creation step.

        Returns the completed PlayerCharacter when all steps are done,
        or None if still in progress.
        """
        if self.finished:
            return self._result

        if event.type != pygame.KEYDOWN:
            return None

        if self.step == STEP_RACE:
            return self._handle_race_input(event)
        elif self.step == STEP_CLASS:
            return self._handle_class_input(event)
        elif self.step == STEP_TRAIT:
            return self._handle_trait_input(event)
        elif self.step == STEP_NAME:
            return self._handle_name_input(event)
        elif self.step == STEP_CONFIRM:
            return self._handle_confirm_input(event)
        return None

    def _handle_race_input(self, event):
        races = list(ALL_PLAYABLE_RACES)
        if event.key == pygame.K_UP:
            self._race_index = (self._race_index - 1) % len(races)
        elif event.key == pygame.K_DOWN:
            self._race_index = (self._race_index + 1) % len(races)
        elif event.key == pygame.K_RETURN:
            self.selected_race = races[self._race_index]
            self.step = STEP_CLASS
        elif event.key == pygame.K_ESCAPE:
            return "back_to_menu"
        return None

    def _handle_class_input(self, event):
        classes = list(ALL_CLASSES)
        if event.key == pygame.K_UP:
            self._class_index = (self._class_index - 1) % len(classes)
        elif event.key == pygame.K_DOWN:
            self._class_index = (self._class_index + 1) % len(classes)
        elif event.key == pygame.K_RETURN:
            self.selected_class = classes[self._class_index]
            self.step = STEP_TRAIT
        elif event.key == pygame.K_ESCAPE:
            self.step = STEP_RACE
        return None

    def _handle_trait_input(self, event):
        traits = list(PLAYER_TRAITS.keys())
        if event.key == pygame.K_UP:
            self._trait_index = (self._trait_index - 1) % len(traits)
        elif event.key == pygame.K_DOWN:
            self._trait_index = (self._trait_index + 1) % len(traits)
        elif event.key == pygame.K_RETURN:
            self.selected_trait = traits[self._trait_index]
            self.step = STEP_NAME
        elif event.key == pygame.K_ESCAPE:
            self.step = STEP_CLASS
        return None

    def _handle_name_input(self, event):
        if event.key == pygame.K_RETURN and self.player_name.strip():
            self.step = STEP_CONFIRM
        elif event.key == pygame.K_ESCAPE:
            self.step = STEP_TRAIT
        elif event.key == pygame.K_BACKSPACE:
            self.player_name = self.player_name[:-1]
        elif event.unicode and len(self.player_name) < 20:
            if event.unicode.isprintable():
                self.player_name += event.unicode
        return None

    def _handle_confirm_input(self, event):
        if event.key == pygame.K_RETURN:
            self._result = PlayerCharacter(
                name=self.player_name.strip(),
                race=self.selected_race,
                player_class=self.selected_class,
                trait=self.selected_trait,
            )
            self.finished = True
            return self._result
        elif event.key == pygame.K_ESCAPE:
            self.step = STEP_NAME
        return None

    def draw(self, surface):
        """Draw the current creation step. Placeholder — full UI in Batch 9."""
        surface.fill((15, 12, 8))
        title_font = get_font(48)
        font = get_font(24)
        small = get_font(18)

        # Title
        title = title_font.render("CHARACTER CREATION", True, GOLD)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        if self.step == STEP_RACE:
            self._draw_race_select(surface, font, small)
        elif self.step == STEP_CLASS:
            self._draw_class_select(surface, font, small)
        elif self.step == STEP_TRAIT:
            self._draw_trait_select(surface, font, small)
        elif self.step == STEP_NAME:
            self._draw_name_input(surface, font, small)
        elif self.step == STEP_CONFIRM:
            self._draw_confirm(surface, font, small)

    def _draw_race_select(self, surface, font, small):
        header = font.render("Choose Your Race", True, WHITE)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 100))

        races = list(ALL_PLAYABLE_RACES)
        y = 160
        for i, race_id in enumerate(races):
            color = GOLD if i == self._race_index else WHITE
            name = RACE_DISPLAY_NAMES.get(race_id, race_id)
            text = small.render(f"{'> ' if i == self._race_index else '  '}{name}", True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - 100, y))
            y += 26

        hint = small.render("[UP/DOWN] Navigate   [ENTER] Select   [ESC] Back", True, (120, 120, 120))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def _draw_class_select(self, surface, font, small):
        header = font.render("Choose Your Class", True, WHITE)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 100))

        classes = list(ALL_CLASSES)
        y = 160
        for i, cls_id in enumerate(classes):
            color = GOLD if i == self._class_index else WHITE
            name = CLASS_DISPLAY_NAMES.get(cls_id, cls_id)
            text = small.render(f"{'> ' if i == self._class_index else '  '}{name}", True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - 100, y))
            # Description on the right
            if i == self._class_index:
                desc = small.render(CLASS_DESCRIPTIONS.get(cls_id, ""), True, (180, 180, 160))
                surface.blit(desc, (SCREEN_WIDTH // 2 - 100, y + 22))
                y += 22
            y += 26

        hint = small.render("[UP/DOWN] Navigate   [ENTER] Select   [ESC] Back", True, (120, 120, 120))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def _draw_trait_select(self, surface, font, small):
        header = font.render("Choose Your Trait", True, WHITE)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 100))

        traits = list(PLAYER_TRAITS.items())
        y = 160
        for i, (trait_id, info) in enumerate(traits):
            color = GOLD if i == self._trait_index else WHITE
            prefix = "> " if i == self._trait_index else "  "
            text = small.render(f"{prefix}{info['name']} — {info['effect']}", True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - 200, y))
            y += 26

        hint = small.render("[UP/DOWN] Navigate   [ENTER] Select   [ESC] Back", True, (120, 120, 120))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def _draw_name_input(self, surface, font, small):
        header = font.render("Enter Your Name", True, WHITE)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 100))

        # Name input box
        name_display = self.player_name + "_"
        name_text = font.render(name_display, True, GOLD)
        box_x = SCREEN_WIDTH // 2 - 150
        box_y = 200
        pygame.draw.rect(surface, (40, 35, 30), (box_x, box_y, 300, 40))
        pygame.draw.rect(surface, GOLD, (box_x, box_y, 300, 40), 2)
        surface.blit(name_text, (box_x + 10, box_y + 8))

        hint = small.render("[ENTER] Confirm   [ESC] Back", True, (120, 120, 120))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def _draw_confirm(self, surface, font, small):
        header = font.render("Confirm Your Character", True, WHITE)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 100))

        y = 180
        lines = [
            f"Name: {self.player_name}",
            f"Race: {RACE_DISPLAY_NAMES.get(self.selected_race, self.selected_race)}",
            f"Class: {CLASS_DISPLAY_NAMES.get(self.selected_class, self.selected_class)}",
            f"Trait: {PLAYER_TRAITS.get(self.selected_trait, {}).get('name', self.selected_trait)}",
        ]
        for line in lines:
            text = font.render(line, True, WHITE)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 36

        hint = small.render("[ENTER] Begin Campaign   [ESC] Go Back", True, (120, 120, 120))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))
