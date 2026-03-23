"""Formation preview helpers for multi-unit selection."""
import math


def preview_line_formation(squads, destination, spacing=50):
    """Return a simple line formation preview for a set of squads.

    - squads: iterable of squads
    - destination: (tx, ty)
    - spacing: spacing along the line
    Returns: dict { squad: (tx, ty, facing) }
    """
    if not squads:
        return {}
    cx = sum(getattr(s, 'center', lambda: (0, 0))[0] for s in squads) / len(squads)
    cy = sum(getattr(s, 'center', lambda: (0, 0))[1] for s in squads) / len(squads)
    dx = destination[0] - cx
    dy = destination[1] - cy
    heading = math.atan2(dy, dx) if (dx != 0 or dy != 0) else 0.0
    px, py = -math.sin(heading), math.cos(heading)
    preview = {}
    for i, sq in enumerate(squads):
        offset = (i - len(squads) // 2) * spacing
        tx = cx + px * offset
        ty = cy + py * offset
        preview[sq] = (tx, ty, heading)
    return preview
