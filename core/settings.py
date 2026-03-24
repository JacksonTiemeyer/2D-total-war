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

# Team colors — Phase 3: 13 racial factions
TEAM_COLORS = {
    0: BLUE,                 # Player / Independent
    1: RED,                  # Human Kingdoms
    2: (180, 180, 220),      # High Elf Dominion - silver
    3: (40, 140, 40),        # Wood Elf Enclave - forest green
    4: (60, 160, 160),       # Sea Elf Corsairs - teal
    5: (140, 180, 220),      # Snow Elf Khanate - ice blue
    6: (100, 40, 120),       # Dark Elf Cabal - dark purple
    7: (180, 140, 60),       # Dwarf Holds - bronze
    8: (80, 140, 40),        # Orc Waaagh! - orc green
    9: (120, 110, 90),       # Undead Legion - bone
    10: (140, 100, 60),      # Troll & Ogre Tribes - mud brown
    11: (140, 40, 40),       # Beastfolk Warherds - dark red
    12: (80, 120, 40),       # Feral Goblins - goblin green
    13: (180, 40, 20),       # Demon Horde - hellfire
    90: (120, 60, 60),       # Bandits
    91: (80, 40, 100),       # Cultists
    92: (100, 70, 50),       # Cannibals
    93: (110, 110, 90),      # Deserters
    94: (100, 120, 140),     # Mercenaries
    None: GREY,
}
TEAM_COLORS_LIGHT = {
    0: LIGHT_BLUE,
    1: (220, 100, 100),      # Human
    2: (210, 210, 240),      # High Elf
    3: (100, 200, 100),      # Wood Elf
    4: (120, 200, 200),      # Sea Elf
    5: (180, 210, 240),      # Snow Elf
    6: (160, 80, 180),       # Dark Elf
    7: (220, 180, 100),      # Dwarf
    8: (120, 180, 80),       # Orc
    9: (170, 160, 140),      # Undead
    10: (190, 150, 100),     # Troll/Ogre
    11: (190, 90, 90),       # Beastfolk
    12: (120, 160, 80),      # Goblin
    13: (220, 80, 60),       # Demon
    90: (180, 100, 100),
    91: (140, 80, 160),
    92: (160, 120, 90),
    93: (170, 170, 150),
    94: (160, 180, 200),
    None: (180, 180, 180),
}

# Battle map
BATTLE_MAP_WIDTH = 3000
BATTLE_MAP_HEIGHT = 2000

# Campaign map (Phase 3: expanded for fantasy world)
CAMPAIGN_MAP_WIDTH = 6000
CAMPAIGN_MAP_HEIGHT = 4500

# Real-time campaign
CAMPAIGN_TICKS_PER_DAY = 900         # frames per in-game day at 1x speed (15 sec)
CAMPAIGN_SPEED_PAUSED = 0
CAMPAIGN_SPEED_1X = 1
CAMPAIGN_SPEED_2X = 2
CAMPAIGN_SPEED_3X = 4

# Campaign fog of war
CAMPAIGN_VISION_RADIUS = 200          # base vision around player army
CAMPAIGN_SETTLEMENT_VISION = 150      # vision around owned settlements
CAMPAIGN_FOG_ALPHA = 120

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

# Balance tuning: make battles last longer (slower, less burst)
# and reduce the charge "one-shot" feel.
CHARGE_WINDOW_FRAMES = 14                  # how long squads stay in "charging" damage window
CHARGE_DAMAGE_BONUS_SCALE = 0.45          # scale for (charge_bonus * mass) added during charge window
CHARGE_DAMAGE_BONUS_CAP_MULT = 1.0        # cap: max extra charge bonus is base_weapon_dmg * this
MELEE_ATTACK_COOLDOWN_FRAMES = 45         # base melee attack cadence (in frames)
INCOMING_DAMAGE_MULT = 0.8               # global incoming damage multiplier

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

# Movement Speed Tiers
MOVE_MODE_WALK = "walk"
MOVE_MODE_MARCH = "march"
MOVE_MODE_RUN = "run"
WALK_SPEED_MULT = 0.5
MARCH_SPEED_MULT = 1.0
RUN_SPEED_MULT_INFANTRY = 1.4
RUN_SPEED_MULT_CAVALRY = 1.6

# Exhaustion
EXHAUSTION_MAX = 100.0
EXHAUSTION_IDLE_RATE = -0.005        # per frame when standing still (negative = recovery)
EXHAUSTION_WALK_RATE = 0.0          # per frame when walking (no exhaustion)
EXHAUSTION_MARCH_RATE = 0.002       # per frame when marching (minimal)
EXHAUSTION_MOVE_RATE = 0.008        # per frame when moving (legacy/run)
EXHAUSTION_FIGHT_RATE = 0.015       # per frame when fighting
EXHAUSTION_CHARGE_RATE = 0.020      # per frame when charging
EXHAUSTION_MORALE_THRESHOLD = 30    # exhaustion level where morale starts draining
EXHAUSTION_MORALE_DRAIN = 0.02      # morale lost per frame above threshold
EXHAUSTION_SPEED_PENALTY = 0.3      # max speed reduction at full exhaustion
EXHAUSTION_DAMAGE_PENALTY = 0.25    # max damage reduction at full exhaustion
EXHAUSTION_COOLDOWN_PENALTY = 0.4   # max attack cooldown increase at full exhaustion

# Unit Collision
COLLISION_GRID_CELL_SIZE = 30       # spatial grid cell size for collision detection
COLLISION_PUSH_STRENGTH = 0.8       # how strongly soldiers push apart
COLLISION_FRIENDLY_PUSH = 0.3       # softer push for friendly soldiers
COLLISION_ENGAGE_RADIUS = 18        # distance at which soldiers become "engaged"

# Phase 2: Unit Physics & Visuals
COLLISION_RADIUS = SOLDIER_RADIUS * 2.5   # base collision radius for push detection
ENGAGEMENT_LOCK_DISTANCE = 20             # soldiers within this of an enemy become engaged
ENGAGEMENT_BREAK_DISTANCE = 35            # must exceed this distance to disengage
CAVALRY_PUNCHTHROUGH_MASS_RATIO = 1.5     # mass ratio needed for cavalry punch-through
CAVALRY_PUNCHTHROUGH_PUSH = 2.5           # push force multiplier during charge punch-through
CAVALRY_PUNCHTHROUGH_MIN_DEPTH = 3        # formation must be thinner than this for punch-through

# Terrain Effects
HILL_RANGED_BONUS = 1.15          # +15% ranged damage from hill
HILL_CHARGE_DOWNHILL_BONUS = 1.20 # +20% charge bonus going downhill
HILL_SPEED_UPHILL_PENALTY = 0.90  # -10% speed going uphill
FOREST_CAVALRY_SPEED_MULT = 0.50  # -50% cavalry speed in forest
FOREST_RANGED_ACCURACY_MULT = 0.70# -30% ranged accuracy into/out of forest
FOREST_MELEE_DEFENSE_BONUS = 1.15 # +15% melee defense in forest

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

# Formations
FORMATION_LINE_COLS_RATIO = 2.0      # wider than deep
FORMATION_COLUMN_COLS_RATIO = 0.3    # deeper than wide
FORMATION_SQUARE_COLS_RATIO = 1.0    # equal
FORMATION_LOOSE_SPACING_MULT = 1.8   # wider spacing
FORMATION_WEDGE_ANGLE = 0.6          # radians, half-angle of V
COHESION_LIMIT = 20                  # max stray distance before auto-reform

# Combat Zone (melee engagement animation)
COMBAT_READY_FRAMES = 10             # frames in ready stance before swing
COMBAT_SWING_FRAMES = 6              # frames for swing animation
COMBAT_SWING_HIT_FRAME = 3           # damage lands on this frame of the swing
COMBAT_RECOVER_FRAMES = 12           # frames recovering after swing
COMBAT_VICTORY_PAUSE_FRAMES = 12     # frames of pause after killing opponent
COMBAT_ZONE_SEPARATION = 12.0        # initial distance between squad lines
COMBAT_ASSIST_FLANK_BONUS = 1.3      # damage bonus for 2v1 assist attacks
COMBAT_ASSIST_RECOVERY_PENALTY = 0.3 # recovery time increase when outnumbered
COMBAT_REINFORCEMENT_MORALE_SHOCK = -8  # morale hit when enemy reinforcements arrive

# CombatZone retreat/extraction
RETREAT_MORALE_PENALTY = -15             # morale hit when retreating from a combat zone
RETREAT_SPEED_DEBUFF = 0.7               # speed multiplier after retreating from combat
RETREAT_DEBUFF_FRAMES = 120              # duration of retreat speed debuff
GENERAL_ZONE_SPLASH_RADIUS = 20          # AoE radius for general attacks in combat zones

# Massive unit visual scale
MASSIVE_VISUAL_SCALE = 1.8           # soldier radius multiplier for massive units

# Mana / Magic System
MANA_REGEN_PER_SECOND = 1.0         # base mana regen per second (overridden per-unit)
MANA_BAR_COLOR = (100, 150, 255)    # blue mana bar
MANA_BAR_LOW_COLOR = (150, 100, 255)  # purple when low
SPELL_ICON_SIZE = 24                # pixel size of spell icons in HUD
SPELL_RANGE_INDICATOR_COLOR = (0, 150, 255, 80)  # semi-transparent blue
SPELL_CAST_COOLDOWN_FRAMES = 30     # minimum frames between casts
SPELL_PROJECTILE_SPEED = 6.0        # world units per frame
SPELL_AOE_DEFAULT_RADIUS = 60       # default area-of-effect radius

# Weather Effects
WEATHER_TYPES = ["clear", "rain", "fog", "mud", "wind"]
WEATHER_RAIN_ACCURACY = 0.8      # -20% ranged accuracy
WEATHER_RAIN_EXHAUSTION = 1.3    # +30% exhaustion rate
WEATHER_FOG_VISION = 0.5         # halve vision radius
WEATHER_MUD_SPEED = 0.7          # -30% movement speed
WEATHER_MUD_CHARGE = 0.5         # -50% charge bonus
WEATHER_WIND_ACCURACY = 0.15     # +/-15% ranged accuracy

# Vision / Fog of War
VISION_INFANTRY = 200
VISION_CAVALRY = 250
VISION_HILL_BONUS = 1.5       # +50% vision on hills
VISION_FOREST_BLOCK = True    # forests block LOS
FOG_ALPHA = 140               # darkness of unexplored fog

# Campaign
SETTLEMENT_RADIUS = 20
ARMY_ICON_RADIUS = 12
CAMPAIGN_MOVE_SPEED = 1.5  # base pixels/frame (reduced for slower pace)
RECRUITMENT_COST_MULTIPLIER = 1.0
INCOME_PER_SETTLEMENT = 100
STARTING_GOLD = 500

# B11: Army size limits (total soldiers)
ARMY_SIZE_BASE = 60           # starting army limit
ARMY_SIZE_PER_LEVEL = 15      # additional capacity per general level
ARMY_SIZE_MAX = 300            # hard cap

# B2: Faction joining
FACTION_JOIN_THRESHOLD = 50    # reputation needed to join a faction
FACTION_LEAVE_PENALTY = -30    # reputation hit when leaving

# B9: Settlement interaction
REST_COST_PER_DAY = 10         # gold cost per day of rest
REST_REPLENISH_RATE = 0.2      # fraction of missing soldiers restored per day
MERCENARY_COST_MULTIPLIER = 1.5  # mercs cost 50% more
TAVERN_RUMORS_COUNT = 3
TAVERN_MERCS_COUNT = 3

# B6: General Betrayal & Persuasion
LOYALTY_DEFAULT = 70              # starting loyalty for new generals
LOYALTY_MIN = 0
LOYALTY_MAX = 100
LOYALTY_BETRAY_THRESHOLD = 30     # below this, general may defect
LOYALTY_BETRAY_CHANCE_BASE = 0.02 # daily chance at exactly threshold
LOYALTY_BETRAY_AMBITIOUS_MULT = 2.0  # ambitious generals defect more
LOYALTY_BETRAY_LOYAL_MULT = 0.3   # loyal generals rarely defect
LOYALTY_BETRAY_GREEDY_MULT = 1.5  # greedy generals defect somewhat more
LOYALTY_BATTLE_WIN_BONUS = 3      # loyalty gained on winning battle
LOYALTY_BATTLE_LOSS_PENALTY = 5   # loyalty lost on losing battle
PERSUASION_RANGE = 120            # world distance to attempt persuasion
BRIBE_COST_BASE = 100             # base gold cost for bribe
BRIBE_LOYALTY_GAIN = 15           # loyalty toward player per bribe
BRIBE_FACTION_LOYALTY_LOSS = 10   # loyalty toward own faction lost per bribe
CONVINCE_BASE_CHANCE = 0.3        # base success chance for convince
CONVINCE_REP_BONUS = 0.005        # added chance per player reputation point
THREATEN_BASE_CHANCE = 0.4        # base success for threaten on cautious
THREATEN_BACKFIRE_CHANCE = 0.5    # chance threaten backfires on aggressive

# D6: Prisoner & Ransom System
CAPTURE_CHANCE_BASE = 0.50        # base chance to capture defeated general
CAPTURE_CHANCE_DECISIVE = 0.75    # capture chance if battle was decisive
PLAYER_CAPTURE_DAYS = 5           # days player is held captive
PLAYER_CAPTURE_RANSOM_BASE = 300  # base ransom cost for player
PLAYER_CAPTURE_DISBAND_RATE = 0.3 # fraction of army that disbands during capture
RANSOM_GOLD_BASE = 200            # base gold received for ransoming a general
RECRUIT_PRISONER_BASE_CHANCE = 0.25  # base chance to recruit a prisoner
EXECUTE_REP_PENALTY_FACTION = -30 # reputation hit with prisoner's faction
EXECUTE_REP_PENALTY_ALL = -5      # reputation hit with all factions
EXECUTE_INTIMIDATION_BONUS = 10   # morale bonus in next battle after execution

# D1: Terrain-specific Battles
CAMPAIGN_TERRAIN_TYPES = ["plains", "forest", "mountain", "desert", "coastal"]

# D2: Seasons & Weather (Campaign)
SEASON_SPRING = "spring"
SEASON_SUMMER = "summer"
SEASON_AUTUMN = "autumn"
SEASON_WINTER = "winter"
SEASON_CYCLE_LENGTH = 100          # days per full cycle
SEASON_SPRING_END = 25             # days 1-25
SEASON_SUMMER_END = 50             # days 26-50
SEASON_AUTUMN_END = 75             # days 51-75
# days 76-100 = winter
SEASON_SUMMER_EXHAUSTION_MULT = 1.3   # +30% exhaustion in summer battles
SEASON_SUMMER_DESERT_SPEED_BONUS = 1.2 # +20% speed for desert factions in summer
SEASON_AUTUMN_INCOME_BONUS = 1.5       # +50% settlement income in autumn (harvest)
SEASON_AUTUMN_MUD_CHANCE = 0.4         # chance of mud weather in autumn battles
SEASON_WINTER_MOVE_PENALTY = 0.7       # -30% campaign movement in winter
SEASON_WINTER_MOUNTAIN_ATTRITION = 1   # soldiers lost per day in mountains during winter
SEASON_WINTER_RANGED_PENALTY = 0.85    # -15% ranged accuracy in winter battles
SEASON_WINTER_HARSH_WEATHER_CHANCE = 0.5  # chance of fog/rain weather in winter battles

# D3: Supply Lines
SUPPLY_RANGE = 400                  # max distance from friendly settlement before attrition
SUPPLY_MORALE_LOSS = 2              # morale lost per day when out of supply
SUPPLY_DESERTION_CHANCE = 0.05      # chance per squad per day of losing a soldier
SUPPLY_WARNING_RANGE = 350          # range at which supply warning appears

# D5: Tournaments & Arena
TOURNAMENT_INTERVAL = 15            # days between tournaments at a town
TOURNAMENT_ENTRY_FEE = 50           # gold cost to enter
TOURNAMENT_ROUND_COUNT = 3          # number of rounds in bracket
TOURNAMENT_BASE_REWARD = 200        # gold reward for winning
TOURNAMENT_REP_REWARD = 10          # reputation reward for winning
TOURNAMENT_ROUND_REWARDS = [25, 50, 200]  # gold per round won
