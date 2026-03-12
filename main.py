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
    POST_BATTLE = "post_battle"
    SKIRMISH_SETUP = "skirmish_setup"


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
        self.battle_stats = None   # post-battle summary data
        self.skirmish_setup = None # skirmish army builder
        self.is_skirmish = False   # true when battle launched from skirmish mode

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
            elif self.state == GameState.POST_BATTLE:
                self._handle_post_battle_event(event)
            elif self.state == GameState.SKIRMISH_SETUP:
                self._handle_skirmish_event(event)

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.campaign = CampaignScene()
                self.state = GameState.CAMPAIGN
            elif event.key == pygame.K_s:
                # Skirmish mode
                from battle.skirmish_setup import SkirmishSetup
                self.skirmish_setup = SkirmishSetup()
                self.state = GameState.SKIRMISH_SETUP
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
                self._collect_battle_stats()
                self.state = GameState.POST_BATTLE
                return
        self.battle.handle_event(event)

    def _handle_post_battle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._resolve_battle()

    def _handle_skirmish_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.skirmish_setup = None
                self.state = GameState.MAIN_MENU
                return
        if self.skirmish_setup:
            result = self.skirmish_setup.handle_event(event)
            if result:
                # result is (player_data, enemy_data)
                self.battle = BattleScene(result[0], result[1])
                self.is_skirmish = True
                self.state = GameState.BATTLE

    def _update(self):
        if self.state == GameState.CAMPAIGN:
            self.campaign.update()
            battle = self.campaign.get_pending_battle()
            if battle:
                self.current_enemy = battle[1]
                self.state = GameState.PRE_BATTLE
        elif self.state == GameState.BATTLE:
            self.battle.update()
        elif self.state == GameState.SKIRMISH_SETUP:
            pass  # skirmish setup is event-driven

    def _collect_battle_stats(self):
        """Gather end-of-battle statistics for the summary screen."""
        b = self.battle
        stats = {
            "result": b.result,
            "duration_frames": b.battle_timer,
            "player_squads": [],
            "enemy_squads": [],
            "player_generals": [],
            "enemy_generals": [],
            "total_player_kills": 0,
            "total_enemy_kills": 0,
            "loot_gold": 0,
        }
        for sq in b.player_squads:
            entry = {
                "name": sq.unit_stats.name,
                "initial": sq.initial_count,
                "alive": sq.alive_count,
                "kills": sq.kills,
                "exhaustion": sq.exhaustion_display,
            }
            stats["player_squads"].append(entry)
            stats["total_player_kills"] += sq.kills
        for sq in b.enemy_squads:
            entry = {
                "name": sq.unit_stats.name,
                "initial": sq.initial_count,
                "alive": sq.alive_count,
                "kills": sq.kills,
            }
            stats["enemy_squads"].append(entry)
            stats["total_enemy_kills"] += sq.kills
        # General stats (include dead ones too via original lists)
        for g in b.player_generals + [g for g in getattr(b, '_dead_generals', []) if g.team == 0]:
            stats["player_generals"].append({
                "name": g.name, "type": g.general_type,
                "kills": g.kills, "duels_won": g.duels_won,
                "level": g.level, "alive": g.alive,
            })
        for g in b.enemy_generals + [g for g in getattr(b, '_dead_generals', []) if g.team == 1]:
            stats["enemy_generals"].append({
                "name": g.name, "type": g.general_type,
                "kills": g.kills, "duels_won": g.duels_won,
                "level": g.level, "alive": g.alive,
            })
        # Loot calculation
        if b.result == BattleResult.PLAYER_WIN and self.current_enemy:
            stats["loot_gold"] = 50 + len(self.current_enemy.squads) * 20
        # MVP squad
        all_player = stats["player_squads"]
        if all_player:
            mvp = max(all_player, key=lambda s: s["kills"])
            stats["mvp"] = mvp["name"] if mvp["kills"] > 0 else None
        else:
            stats["mvp"] = None
        self.battle_stats = stats

    def _resolve_battle(self):
        """Apply battle results to campaign and return."""
        if self.is_skirmish:
            self.battle = None
            self.battle_stats = None
            self.is_skirmish = False
            self.state = GameState.MAIN_MENU
            return

        if self.battle.result == BattleResult.PLAYER_WIN:
            if self.current_enemy:
                self.campaign.remove_army(self.current_enemy)
                self.campaign.player_army.gold += self.battle_stats.get("loot_gold", 0)
            # Apply casualties to player army (survivors persist)
            self.campaign.player_army.apply_battle_results(self.battle)
        else:
            # Defeat: apply casualties (survivors persist, but losses are real)
            self.campaign.player_army.apply_battle_results(self.battle)

        self.current_enemy = None
        self.battle = None
        self.battle_stats = None
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
        elif self.state == GameState.POST_BATTLE:
            self._draw_post_battle()
        elif self.state == GameState.SKIRMISH_SETUP:
            if self.skirmish_setup:
                self.skirmish_setup.draw(self.screen)

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

        # Start prompts
        prompt = font.render("[ENTER] Campaign Mode", True, WHITE)
        if pygame.time.get_ticks() % 1000 < 700:
            self.screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 480))

        skirmish = font.render("[S] Skirmish Mode", True, (180, 200, 255))
        self.screen.blit(skirmish, (SCREEN_WIDTH // 2 - skirmish.get_width() // 2, 520))

        controls = small.render("ESC to quit", True, (100, 100, 100))
        self.screen.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, 570))

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
        for csq in pa.squads:
            stats = csq.unit_stats
            count_str = f"{csq.current_count}/{csq.max_count}" if csq.is_understrength else str(csq.current_count)
            text = tiny.render(
                f"  {stats.name} ({count_str}) - ATK:{stats.melee_attack} "
                f"DEF:{stats.melee_defense}"
                f"{' RNG:'+str(stats.ranged_attack) if stats.ranged_attack else ''}",
                True, WHITE)
            self.screen.blit(text, (110, y))
            y += 20
        gen = tiny.render(f"  General: {pa.general_name} ({pa.general_stats.name}) Lv{pa.general_level}", True, GOLD)
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
        for csq in ea.squads:
            stats = csq.unit_stats
            count_str = f"{csq.current_count}/{csq.max_count}" if csq.is_understrength else str(csq.current_count)
            text = tiny.render(
                f"  {stats.name} ({count_str}) - ATK:{stats.melee_attack} "
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

    def _draw_post_battle(self):
        """Draw post-battle summary screen."""
        self.screen.fill((20, 18, 15))
        s = self.battle_stats
        if not s:
            return

        font = pygame.font.SysFont(None, 48)
        med = pygame.font.SysFont(None, 24)
        small = pygame.font.SysFont(None, 20)
        tiny = pygame.font.SysFont(None, 17)

        # Title
        is_win = s["result"] == BattleResult.PLAYER_WIN
        title_text = "VICTORY!" if is_win else "DEFEAT"
        title_color = GOLD if is_win else (200, 50, 50)
        title = font.render(title_text, True, title_color)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        # Duration
        mins = s["duration_frames"] // (60 * 60)
        secs = (s["duration_frames"] // 60) % 60
        dur = small.render(f"Battle Duration: {mins:02d}:{secs:02d}", True, (160, 160, 160))
        self.screen.blit(dur, (SCREEN_WIDTH // 2 - dur.get_width() // 2, 80))

        # Two columns
        col_left = 60
        col_right = SCREEN_WIDTH // 2 + 30
        col_w = SCREEN_WIDTH // 2 - 90

        # Left column - Your Army
        y = 120
        header = med.render("Your Forces", True, (100, 150, 255))
        self.screen.blit(header, (col_left, y))
        y += 30

        # Column headers
        hdr = tiny.render(f"{'Unit':<20} {'Alive':>8} {'Killed':>8} {'Kills':>8}", True, (140, 140, 140))
        self.screen.blit(hdr, (col_left, y))
        y += 5
        pygame.draw.line(self.screen, (60, 60, 60), (col_left, y + 12), (col_left + col_w, y + 12))
        y += 16

        total_started = 0
        total_survived = 0
        for sq in s["player_squads"]:
            killed = sq["initial"] - sq["alive"]
            total_started += sq["initial"]
            total_survived += sq["alive"]
            # Color code: green if all survived, red if wiped
            if sq["alive"] == 0:
                color = (180, 60, 60)
            elif sq["alive"] < sq["initial"]:
                color = (220, 200, 100)
            else:
                color = (100, 220, 100)
            line = tiny.render(
                f"{sq['name']:<20} {sq['alive']:>3}/{sq['initial']:<4} {killed:>8} {sq['kills']:>8}",
                True, color)
            self.screen.blit(line, (col_left, y))
            y += 18

        y += 8
        totals = small.render(
            f"Survived: {total_survived}/{total_started}  |  Total Kills: {s['total_player_kills']}",
            True, WHITE)
        self.screen.blit(totals, (col_left, y))
        y += 25

        # Player generals
        for g in s.get("player_generals", []):
            status = "ALIVE" if g["alive"] else "FALLEN"
            gcolor = GOLD if g["alive"] else (180, 60, 60)
            gt = tiny.render(
                f"General {g['name']} ({g['type']}) Lv{g['level']} - "
                f"Kills:{g['kills']} Duels:{g['duels_won']} [{status}]",
                True, gcolor)
            self.screen.blit(gt, (col_left, y))
            y += 18

        # MVP
        if s.get("mvp"):
            y += 10
            mvp = med.render(f"MVP: {s['mvp']}", True, GOLD)
            self.screen.blit(mvp, (col_left, y))

        # Right column - Enemy Army
        y = 120
        header2 = med.render("Enemy Forces", True, (255, 100, 100))
        self.screen.blit(header2, (col_right, y))
        y += 30

        hdr2 = tiny.render(f"{'Unit':<20} {'Alive':>8} {'Killed':>8} {'Kills':>8}", True, (140, 140, 140))
        self.screen.blit(hdr2, (col_right, y))
        y += 5
        pygame.draw.line(self.screen, (60, 60, 60), (col_right, y + 12), (col_right + col_w, y + 12))
        y += 16

        e_total_started = 0
        e_total_survived = 0
        for sq in s["enemy_squads"]:
            killed = sq["initial"] - sq["alive"]
            e_total_started += sq["initial"]
            e_total_survived += sq["alive"]
            if sq["alive"] == 0:
                color = (180, 60, 60)
            elif sq["alive"] < sq["initial"]:
                color = (220, 200, 100)
            else:
                color = (100, 220, 100)
            line = tiny.render(
                f"{sq['name']:<20} {sq['alive']:>3}/{sq['initial']:<4} {killed:>8} {sq['kills']:>8}",
                True, color)
            self.screen.blit(line, (col_right, y))
            y += 18

        y += 8
        e_totals = small.render(
            f"Survived: {e_total_survived}/{e_total_started}  |  Total Kills: {s['total_enemy_kills']}",
            True, WHITE)
        self.screen.blit(e_totals, (col_right, y))
        y += 25

        for g in s.get("enemy_generals", []):
            status = "ALIVE" if g["alive"] else "FALLEN"
            gcolor = (200, 150, 100) if g["alive"] else (180, 60, 60)
            gt = tiny.render(
                f"General {g['name']} ({g['type']}) Lv{g['level']} - "
                f"Kills:{g['kills']} Duels:{g['duels_won']} [{status}]",
                True, gcolor)
            self.screen.blit(gt, (col_right, y))
            y += 18

        # Loot
        if s["loot_gold"] > 0:
            y = max(y, SCREEN_HEIGHT - 140)
            loot = med.render(f"Loot: +{s['loot_gold']} Gold", True, GOLD)
            self.screen.blit(loot, (SCREEN_WIDTH // 2 - loot.get_width() // 2, SCREEN_HEIGHT - 120))

        # Continue prompt
        cont = med.render("Press ENTER to continue", True, WHITE)
        if pygame.time.get_ticks() % 1000 < 700:
            self.screen.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, SCREEN_HEIGHT - 60))


if __name__ == "__main__":
    game = Game()
    game.run()
