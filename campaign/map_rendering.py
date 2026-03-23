"""Campaign map rendering functions.

World presentation layer: terrain, roads, fog of war, and map indicators.
All functions accept the CampaignScene instance as first argument (``scene``).
"""

import pygame
from core.utils import get_font, distance
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMPAIGN_VISION_RADIUS, CAMPAIGN_SETTLEMENT_VISION, CAMPAIGN_FOG_ALPHA,
    TEAM_COLORS,
    WHITE, GREY,
    PERSUASION_RANGE,
)
from campaign.settlement import SettlementType


def draw_territory_borders(scene, surface):
    """B4: Draw faction territory as colored regions around settlements."""
    territory_alpha = 30
    for s in scene.settlements:
        if s.owner is None:
            continue
        color = TEAM_COLORS.get(s.owner, GREY)
        sx, sy = scene.camera.world_to_screen(s.x, s.y)

        if s.settlement_type == SettlementType.CASTLE:
            radius = scene.camera.scale(180)
        elif s.settlement_type == SettlementType.TOWN:
            radius = scene.camera.scale(150)
        else:
            radius = scene.camera.scale(100)

        if radius < 5:
            continue

        territory_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        territory_color = (*color, territory_alpha)
        pygame.draw.circle(territory_surf, territory_color, (radius, radius), radius)
        border_color = (*color, territory_alpha + 40)
        pygame.draw.circle(territory_surf, border_color, (radius, radius), radius, max(1, int(radius * 0.05)))
        surface.blit(territory_surf, (sx - radius, sy - radius))


def draw_stronghold(scene, surface, stronghold):
    """B8: Draw a roaming army stronghold on the map."""
    from campaign.roaming import StrongholdStage
    sx, sy = scene.camera.world_to_screen(stronghold.x, stronghold.y)
    color = TEAM_COLORS.get(stronghold.team, GREY)
    r = scene.camera.scale(15)
    if r < 3:
        return
    if stronghold.stage == StrongholdStage.STRONGHOLD:
        r = scene.camera.scale(20)
        pygame.draw.rect(surface, color, (sx - r, sy - r, r * 2, r * 2))
        pygame.draw.rect(surface, (200, 200, 200), (sx - r, sy - r, r * 2, r * 2), 2)
    else:
        pts = [(sx, sy - r), (sx - r, sy + r), (sx + r, sy + r)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, (200, 200, 200), pts, 1)
    if scene.camera.zoom > 0.4:
        font = get_font(max(12, scene.camera.scale(13)))
        text = font.render(stronghold.name, True, (220, 180, 180))
        surface.blit(text, (sx - text.get_width() // 2, sy + r + 2))


def draw_roads(scene, surface):
    """Draw roads connecting settlements of the same faction."""
    if not hasattr(scene, '_road_cache') or scene._territory_needs_update:
        scene._road_cache = []
        by_owner = {}
        for s in scene.settlements:
            if s.owner is not None:
                by_owner.setdefault(s.owner, []).append(s)
        for owner, slist in by_owner.items():
            if len(slist) < 2:
                continue
            for s in slist:
                others = sorted(
                    [o for o in slist if o is not s],
                    key=lambda o: distance(s.x, s.y, o.x, o.y))
                for o in others[:2]:
                    pair = tuple(sorted([id(s), id(o)]))
                    if pair not in [tuple(sorted([id(a), id(b)])) for a, b, _ in scene._road_cache]:
                        scene._road_cache.append((s, o, owner))

    road_color_base = (140, 120, 80)
    for s1, s2, owner in scene._road_cache:
        sx1, sy1 = scene.camera.world_to_screen(s1.x, s1.y)
        sx2, sy2 = scene.camera.world_to_screen(s2.x, s2.y)
        team_color = TEAM_COLORS.get(owner, GREY)
        road_color = (
            min(255, (road_color_base[0] + team_color[0]) // 2),
            min(255, (road_color_base[1] + team_color[1]) // 2),
            min(255, (road_color_base[2] + team_color[2]) // 2),
        )
        pygame.draw.line(surface, road_color,
                         (int(sx1), int(sy1)), (int(sx2), int(sy2)), max(1, int(scene.camera.scale(2))))


def draw_interaction_indicators(scene, surface):
    """Draw interaction hint icons near interactable objects close to player."""
    px, py = scene.player_army.x, scene.player_army.y
    indicator_font = get_font(max(12, scene.camera.scale(14)))

    for s in scene.settlements:
        d = distance(px, py, s.x, s.y)
        if d < 80:
            sx, sy = scene.camera.world_to_screen(s.x, s.y)
            r = scene.camera.scale(25)
            pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500.0
            alpha = int(80 + 80 * pulse)
            ring_surf = pygame.Surface((int(r * 2 + 4), int(r * 2 + 4)), pygame.SRCALPHA)
            color = (255, 215, 0, alpha)
            pygame.draw.circle(ring_surf, color, (int(r + 2), int(r + 2)), int(r), 2)
            surface.blit(ring_surf, (int(sx - r - 2), int(sy - r - 2)))
            label = indicator_font.render("[E]", True, (255, 215, 0))
            surface.blit(label, (int(sx) - label.get_width() // 2,
                                 int(sy) - int(r) - 16))

    for army in scene.armies:
        if army.is_player:
            continue
        if not scene._is_visible(army.x, army.y):
            continue
        d = distance(px, py, army.x, army.y)
        if d < PERSUASION_RANGE:
            sx, sy = scene.camera.world_to_screen(army.x, army.y)
            indicator_font_small = get_font(max(10, scene.camera.scale(11)))
            if scene._are_hostile(0, army.team):
                label = indicator_font_small.render("!", True, (255, 80, 80))
            else:
                label = indicator_font_small.render("?", True, (100, 200, 255))
            surface.blit(label, (int(sx) + 8, int(sy) - 16))


def draw_terrain(scene, surface):
    """Draw decorative terrain features."""
    forests = [
        (200, 400, 120), (1000, 200, 80), (700, 800, 100),
        (1500, 900, 90), (1900, 300, 70), (1100, 700, 110),
        (900, 900, 85), (600, 1400, 95), (2800, 1500, 80),
        (3300, 400, 75), (1700, 2200, 90),
    ]
    for fx, fy, fr in forests:
        sx, sy = scene.camera.world_to_screen(fx, fy)
        r = scene.camera.scale(fr)
        if r < 3:
            continue
        forest_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(forest_surf, (60, 100, 40, 80), (r, r), r)
        surface.blit(forest_surf, (sx - r, sy - r))

    mountains = [
        (1100, 150, 60), (1800, 600, 50), (300, 900, 45),
        (1600, 100, 55), (3000, 400, 50), (2500, 1400, 45),
        (500, 1800, 40),
    ]
    for mx, my, mr in mountains:
        sx, sy = scene.camera.world_to_screen(mx, my)
        r = scene.camera.scale(mr)
        if r < 3:
            continue
        pts = [(sx, sy - r), (sx - r, sy + r // 2), (sx + r, sy + r // 2)]
        pygame.draw.polygon(surface, (120, 110, 90), pts)
        pygame.draw.polygon(surface, (160, 150, 120), pts, 2)
        cap = [(sx, sy - r), (sx - r // 3, sy - r // 3), (sx + r // 3, sy - r // 3)]
        pygame.draw.polygon(surface, WHITE, cap)

    deserts = [(2800, 1900, 200), (3200, 1700, 150), (3000, 2100, 120)]
    for dx, dy, dr in deserts:
        sx, sy = scene.camera.world_to_screen(dx, dy)
        r = scene.camera.scale(dr)
        if r < 3:
            continue
        desert_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(desert_surf, (210, 190, 140, 60), (r, r), r)
        surface.blit(desert_surf, (sx - r, sy - r))

    for wx, wy, wr in [(1200, 2700, 250), (800, 2500, 150), (1600, 2700, 180)]:
        sx, sy = scene.camera.world_to_screen(wx, wy)
        r = scene.camera.scale(wr)
        if r < 3:
            continue
        water_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(water_surf, (60, 100, 160, 50), (r, r), r)
        surface.blit(water_surf, (sx - r, sy - r))


def draw_fog_of_war(scene, surface):
    """B13: Draw fog of war overlay - darken areas outside vision range."""
    fog_scale = 4
    fog_w = SCREEN_WIDTH // fog_scale
    fog_h = SCREEN_HEIGHT // fog_scale

    fog = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA)
    fog.fill((20, 15, 10, CAMPAIGN_FOG_ALPHA))

    px, py = scene.camera.world_to_screen(scene.player_army.x, scene.player_army.y)
    pr = scene.camera.scale(CAMPAIGN_VISION_RADIUS) // fog_scale
    if pr > 0:
        pygame.draw.circle(fog, (0, 0, 0, 0), (px // fog_scale, py // fog_scale), pr)

    for s in scene.settlements:
        if s.owner == 0 or (s.owner is not None and
                            scene.diplomacy.are_allied(0, s.owner)):
            sx, sy = scene.camera.world_to_screen(s.x, s.y)
            sr = scene.camera.scale(CAMPAIGN_SETTLEMENT_VISION) // fog_scale
            if sr > 0:
                pygame.draw.circle(fog, (0, 0, 0, 0), (sx // fog_scale, sy // fog_scale), sr)

    fog_scaled = pygame.transform.scale(fog, (SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.blit(fog_scaled, (0, 0))
