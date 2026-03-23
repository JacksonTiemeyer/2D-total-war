"""Formation engine utilities for multi-squad control.

Provides helpers to compute offsets for standard line-based formations and
basic line placement for multiple squads moving toward a destination.
This is a minimal, safe injection point for a more feature-complete system.
"""
import math


def rotate(x, y, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return x * ca - y * sa, x * sa + y * ca


def compute_line_formation_for_squads(squads, destination, spacing=50):
    """Return per-squad target points for a clean line formation toward destination.

    - squads: iterable of Squad objects (or objects exposing center and set_move_order)
    - destination: (tx, ty) world coordinates where the formation should approach
    - spacing: spacing between squads along the line
    Returns: dict { squad: (tx, ty, facing_angle) }
    """
    if not squads:
        return {}
    # Center of gravity of squads
    cx = sum(getattr(s, 'center', lambda: (0, 0))[0] for s in squads) / max(1, len(squads))
    cy = sum(getattr(s, 'center', lambda: (0, 0))[1] for s in squads) / max(1, len(squads))
    dx = destination[0] - cx
    dy = destination[1] - cy
    heading = math.atan2(dy, dx) if (dx != 0 or dy != 0) else 0.0
    # Perpendicular axis for line
    px, py = -math.sin(heading), math.cos(heading)
    out = {}
    for i, sq in enumerate(squads):
        offset = (i - len(squads) // 2) * spacing
        tx = cx + px * offset
        ty = cy + py * offset
        out[sq] = (tx, ty, heading)
    return out
