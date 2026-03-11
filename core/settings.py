"""Global game settings and constants."""

import pygame

# Display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "2D Total War"

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GREEN = (50, 200, 50)
DARK_GREEN = (30, 120, 30)
YELLOW = (220, 200, 50)
ORANGE = (220, 140, 30)
GREY = (128, 128, 128)
DARK_GREY = (64, 64, 64)
LIGHT_GREY = (192, 192, 192)
BROWN = (139, 90, 43)
DARK_BROWN = (80, 50, 20)
SAND = (210, 190, 140)
LIGHT_BLUE = (100, 150, 220)
DARK_RED = (140, 30, 30)
PURPLE = (140, 50, 180)
GOLD = (255, 215, 0)

# Team colors
TEAM_COLORS = {
    0: BLUE,
    1: RED,
}
TEAM_COLORS_LIGHT = {
    0: LIGHT_BLUE,
    1: (220, 100, 100),
}

# Battle map
BATTLE_MAP_WIDTH = 3000
BATTLE_MAP_HEIGHT = 2000

# Campaign map
CAMPAIGN_MAP_WIDTH = 2400
CAMPAIGN_MAP_HEIGHT = 1800

# Camera
CAMERA_SPEED = 8
CAMERA_EDGE_SCROLL_MARGIN = 30
CAMERA_ZOOM_MIN = 0.3
CAMERA_ZOOM_MAX = 2.0
CAMERA_ZOOM_SPEED = 0.1

# Units
SOLDIER_RADIUS = 4
SOLDIER_SPACING = 12
SQUAD_SELECTION_PADDING = 10

# Combat
MELEE_RANGE = 15
RANGED_MIN_RANGE = 50
CHARGE_BONUS_DISTANCE = 80
CHARGE_BONUS_MULTIPLIER = 1.5
MORALE_BREAK_THRESHOLD = 25
MORALE_ROUT_THRESHOLD = 10
MORALE_RECOVERY_RATE = 0.05
MORALE_DAMAGE_LOSS = 0.3
MORALE_CASUALTY_LOSS = 2.0
MORALE_GENERAL_AURA = 15.0
MORALE_GENERAL_DEATH_PENALTY = 30.0

# Flanking
FLANK_ANGLE_THRESHOLD = 1.57    # ~90 degrees: side counts as flank
REAR_ANGLE_THRESHOLD = 2.6     # ~150 degrees: behind counts as rear
FLANK_DAMAGE_BONUS = 1.3       # 30% more damage from flank
REAR_DAMAGE_BONUS = 1.6        # 60% more damage from rear
REAR_CHARGE_MORALE_SHOCK = 15  # instant morale hit from rear charge
FLANK_MORALE_SHOCK = 5         # instant morale hit from flank charge

# Exhaustion
EXHAUSTION_MAX = 100.0
EXHAUSTION_IDLE_RATE = 0.002        # per frame when standing still
EXHAUSTION_MOVE_RATE = 0.008        # per frame when moving
EXHAUSTION_FIGHT_RATE = 0.015       # per frame when fighting
EXHAUSTION_CHARGE_RATE = 0.020      # per frame when charging
EXHAUSTION_MORALE_THRESHOLD = 30    # exhaustion level where morale starts draining
EXHAUSTION_MORALE_DRAIN = 0.02      # morale lost per frame above threshold
EXHAUSTION_SPEED_PENALTY = 0.3      # max speed reduction at full exhaustion
EXHAUSTION_DAMAGE_PENALTY = 0.25    # max damage reduction at full exhaustion
EXHAUSTION_COOLDOWN_PENALTY = 0.4   # max attack cooldown increase at full exhaustion

# Spear Bracing
BRACE_CHARGE_DAMAGE_MULT = 2.5     # damage dealt to charging cavalry
BRACE_CHARGE_MORALE_SHOCK = 10     # morale hit to cavalry that charges braced spears
BRACE_MIN_IDLE_FRAMES = 60         # must be stationary this long to brace

# Generals / Dueling
GENERAL_RADIUS = 8
GENERAL_HEALTH_MULTIPLIER = 5.0
DUEL_RANGE = 30
DUEL_CIRCLE_RADIUS = 60
DUEL_DURATION_MAX = 600  # frames (~10 seconds at 60fps)

# Campaign
SETTLEMENT_RADIUS = 20
ARMY_ICON_RADIUS = 12
CAMPAIGN_MOVE_SPEED = 3
RECRUITMENT_COST_MULTIPLIER = 1.0
INCOME_PER_SETTLEMENT = 100
STARTING_GOLD = 500
