"""Utility functions."""

import math
import random


def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def angle_between(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


def normalize(dx, dy):
    mag = math.sqrt(dx * dx + dy * dy)
    if mag < 0.001:
        return (0.0, 0.0)
    return (dx / mag, dy / mag)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def point_in_rect(px, py, rx, ry, rw, rh):
    return rx <= px <= rx + rw and ry <= py <= ry + rh


def rects_overlap(r1, r2):
    """Check if two (x, y, w, h) rects overlap."""
    return (r1[0] < r2[0] + r2[2] and r1[0] + r1[2] > r2[0] and
            r1[1] < r2[1] + r2[3] and r1[1] + r1[3] > r2[1])


def random_offset(magnitude):
    return (random.uniform(-magnitude, magnitude),
            random.uniform(-magnitude, magnitude))


def lerp(a, b, t):
    return a + (b - a) * t
