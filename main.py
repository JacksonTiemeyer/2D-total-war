"""2D Total War - Main entry point.

A 2D game inspired by Total War and Mount & Blade Warband.
- Campaign map: move your army, capture settlements, recruit squads
- Real-time battles: command squads with formations, morale, and charges
- General dueling: Three Kingdoms-style hero duels

Controls:
  Campaign:
    RMB         - Move army
    LMB         - Select settlement/army
    R           - Open recruitment (near friendly settlement)
    G           - Cycle general type
    ENTER       - End turn

  Battle:
    LMB/Drag    - Select squads
    RMB         - Move/Attack order
    MMB/Drag    - Pan camera
    Scroll      - Zoom
    SPACE       - Pause
    1/2/3       - Battle speed
    F           - Toggle fire at will (ranged)
"""

import sys
import pygame
from core.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, WHITE, BLACK, GOLD
from campaign.campaign_scene import CampaignScene
from battle.battle_scene import BattleScene, BattleResult


class GameState:
    MAIN_MENU = "main_menu"
    CAMPAIGN = "campaign"
    BATTLE = "battle"
    PRE_BATTLE = "pre_battle"


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MAIN_MENU
        self.campaign = None
        self.battle = None
        self.current_enemy = None  # enemy army for pending battle

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()
        pygame.quit()
        sys.exit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == GameState.MAIN_MENU:
                self._handle_menu_event(event)
            elif self.state == GameState.CAMPAIGN:
                self.campaign.handle_event(event)
            elif self.state == GameState.PRE_BATTLE:
                self._handle_pre_battle_event(event)
            elif self.state == GameState.BATTLE:
                self._handle_battle_event(event)

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.campaign = CampaignScene()
                self.state = GameState.CAMPAIGN
            elif event.key == pygame.K_ESCAPE:
                self.running = False

    def _handle_pre_battle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_b:
                # Start battle
                player_data = self.campaign.player_army.get_battle_data()
                enemy_data = self.current_enemy.get_battle_data()
                self.battle = BattleScene(player_data, enemy_data)
                self.state = GameState.BATTLE
            elif event.key == pygame.K_ESCAPE or event.key == pygame.K_r:
                # Retreat - move player away
                self.campaign.player_army.x -= 80
                self.campaign.player_army.y -= 80
                self.current_enemy = None
                self.state = GameState.CAMPAIGN

    def _handle_battle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.battle.result != BattleResult.ONGOING:
                self._resolve_battle()
                return
        self.battle.handle_event(event)

    def _update(self):
        if self.state == GameState.CAMPAIGN:
            self.campaign.update()
            battle = self.campaign.get_pending_battle()
            if battle:
                self.current_enemy = battle[1]
                self.state = GameState.PRE_BATTLE
        elif self.state == GameState.BATTLE:
            self.battle.update()

    def _resolve_battle(self):
        if self.battle.result == BattleResult.PLAYER_WIN:
            # Remove enemy army from campaign
            if self.current_enemy:
                self.campaign.remove_army(self.current_enemy)
                # Loot gold
                self.campaign.player_army.gold += 50 + len(self.current_enemy.squads) * 20
        else:
            # Player lost - lose some squads
            if self.campaign.player_army.squads:
                # Lose half the army
                losses = len(self.campaign.player_army.squads) // 2
                for _ in range(max(1, losses)):
                    if self.campaign.player_army.squads:
                        self.campaign.player_army.squads.pop()

        self.current_enemy = None
        self.battle = None
        self.state = GameState.CAMPAIGN

    def _draw(self):
        if self.state == GameState.MAIN_MENU:
            self._draw_menu()
        elif self.state == GameState.CAMPAIGN:
            self.campaign.draw(self.screen)
        elif self.state == GameState.PRE_BATTLE:
            self._draw_pre_battle()
        elif self.state == GameState.BATTLE:
            self.battle.draw(self.screen)

        pygame.display.flip()

    def _draw_menu(self):
        self.screen.fill((20, 15, 10))

        # Title
        big_font = pygame.font.SysFont(None, 80)
        title = big_font.render("2D TOTAL WAR", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 150))

        # Subtitle
        font = pygame.font.SysFont(None, 28)
        sub = font.render("A Total War x Mount & Blade Prototype", True, (180, 170, 140))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 240))

        # Features
        small = pygame.font.SysFont(None, 22)
        features = [
            "Squad-based tactical combat with formations and morale",
            "Three Kingdoms-style general dueling system",
            "Mount & Blade campaign map with roaming armies",
            "Settlement capture and squad recruitment",
        ]
        y = 310
        for f in features:
            text = small.render(f"  {f}", True, (150, 145, 130))
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 28

        # Start prompt
        prompt = font.render("Press ENTER or SPACE to begin", True, WHITE)
        # Blink effect
        if pygame.time.get_ticks() % 1000 < 700:
            self.screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 500))

        # Controls summary
        controls = small.render("ESC to quit", True, (100, 100, 100))
        self.screen.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, 550))

    def _draw_pre_battle(self):
        self.screen.fill((30, 25, 20))
        font = pygame.font.SysFont(None, 48)
        small = pygame.font.SysFont(None, 22)
        tiny = pygame.font.SysFont(None, 18)

        title = font.render("BATTLE!", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 60))

        # Player army info
        pa = self.campaign.player_army
        y = 130
        header = small.render("Your Forces:", True, (100, 150, 255))
        self.screen.blit(header, (100, y))
        y += 25
        for stats, _ in pa.squads:
            text = tiny.render(
                f"  {stats.name} ({stats.squad_size}) - ATK:{stats.melee_attack} "
                f"DEF:{stats.melee_defense}"
                f"{' RNG:'+str(stats.ranged_attack) if stats.ranged_attack else ''}",
                True, WHITE)
            self.screen.blit(text, (110, y))
            y += 20
        gen = tiny.render(f"  General: {pa.general_name} ({pa.general_stats.name})", True, GOLD)
        self.screen.blit(gen, (110, y))
        y += 20
        strength = small.render(f"  Total Strength: {pa.army_strength}", True, (100, 200, 100))
        self.screen.blit(strength, (110, y))

        # Enemy army info
        ea = self.current_enemy
        y = 130
        header2 = small.render("Enemy Forces:", True, (255, 100, 100))
        self.screen.blit(header2, (SCREEN_WIDTH - 400, y))
        y += 25
        for stats, _ in ea.squads:
            text = tiny.render(
                f"  {stats.name} ({stats.squad_size}) - ATK:{stats.melee_attack} "
                f"DEF:{stats.melee_defense}"
                f"{' RNG:'+str(stats.ranged_attack) if stats.ranged_attack else ''}",
                True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH - 390, y))
            y += 20
        gen2 = tiny.render(f"  General: {ea.general_name} ({ea.general_stats.name})", True, GOLD)
        self.screen.blit(gen2, (SCREEN_WIDTH - 390, y))
        y += 20
        strength2 = small.render(f"  Total Strength: {ea.army_strength}", True, (200, 100, 100))
        self.screen.blit(strength2, (SCREEN_WIDTH - 390, y))

        # Options
        opt_y = SCREEN_HEIGHT - 150
        opt1 = small.render("[ENTER / B] Fight!", True, GOLD)
        opt2 = small.render("[ESC / R] Retreat", True, (200, 150, 100))
        self.screen.blit(opt1, (SCREEN_WIDTH // 2 - 80, opt_y))
        self.screen.blit(opt2, (SCREEN_WIDTH // 2 - 80, opt_y + 30))


if __name__ == "__main__":
    game = Game()
    game.run()
