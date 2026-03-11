"""Camera system with panning and zoom."""

import pygame
from core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMERA_SPEED, CAMERA_EDGE_SCROLL_MARGIN,
    CAMERA_ZOOM_MIN, CAMERA_ZOOM_MAX, CAMERA_ZOOM_SPEED,
)


class Camera:
    def __init__(self, map_width, map_height):
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
        self.map_width = map_width
        self.map_height = map_height
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_cam_start = (0.0, 0.0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            old_zoom = self.zoom
            self.zoom += event.y * CAMERA_ZOOM_SPEED
            self.zoom = max(CAMERA_ZOOM_MIN, min(CAMERA_ZOOM_MAX, self.zoom))
            # Zoom toward mouse position
            mx, my = pygame.mouse.get_pos()
            factor = self.zoom / old_zoom
            self.x = mx - factor * (mx - self.x)
            self.y = my - factor * (my - self.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self.dragging = True
            self.drag_start = event.pos
            self.drag_cam_start = (self.x, self.y)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dx = event.pos[0] - self.drag_start[0]
            dy = event.pos[1] - self.drag_start[1]
            self.x = self.drag_cam_start[0] + dx
            self.y = self.drag_cam_start[1] + dy

    def update(self):
        # Edge scrolling
        mx, my = pygame.mouse.get_pos()
        if mx < CAMERA_EDGE_SCROLL_MARGIN:
            self.x += CAMERA_SPEED
        elif mx > SCREEN_WIDTH - CAMERA_EDGE_SCROLL_MARGIN:
            self.x -= CAMERA_SPEED
        if my < CAMERA_EDGE_SCROLL_MARGIN:
            self.y += CAMERA_SPEED
        elif my > SCREEN_HEIGHT - CAMERA_EDGE_SCROLL_MARGIN:
            self.y -= CAMERA_SPEED

        # Keyboard scrolling
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x += CAMERA_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x -= CAMERA_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y += CAMERA_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y -= CAMERA_SPEED

        # Clamp
        self.x = min(0, max(-(self.map_width * self.zoom - SCREEN_WIDTH), self.x))
        self.y = min(0, max(-(self.map_height * self.zoom - SCREEN_HEIGHT), self.y))

    def world_to_screen(self, wx, wy):
        sx = wx * self.zoom + self.x
        sy = wy * self.zoom + self.y
        return (int(sx), int(sy))

    def screen_to_world(self, sx, sy):
        wx = (sx - self.x) / self.zoom
        wy = (sy - self.y) / self.zoom
        return (wx, wy)

    def scale(self, value):
        return max(1, int(value * self.zoom))

    def center_on(self, wx, wy):
        self.x = SCREEN_WIDTH / 2 - wx * self.zoom
        self.y = SCREEN_HEIGHT / 2 - wy * self.zoom
