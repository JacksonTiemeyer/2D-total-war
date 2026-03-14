"""AI army behavior controller - priority-based task system (B5).

Each AI army evaluates priorities each tick and picks the highest-priority
task it can act on. General personality traits bias the decisions.
"""

import random
import math
from core.utils import distance


# --- General personality traits (B5) ---
class GeneralPersonality:
    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    LOYAL = "loyal"
    AMBITIOUS = "ambitious"
    GREEDY = "greedy"

ALL_PERSONALITIES = [
    GeneralPersonality.AGGRESSIVE,
    GeneralPersonality.CAUTIOUS,
    GeneralPersonality.LOYAL,
    GeneralPersonality.AMBITIOUS,
    GeneralPersonality.GREEDY,
]


# --- AI Task types ---
class AITask:
    DEFEND_HOME = "defend_home"
    WAR_ORDERS = "war_orders"
    PATROL = "patrol"
    HUNT_BANDITS = "hunt_bandits"
    PILLAGE = "pillage"
    REINFORCE = "reinforce"
    IDLE_GARRISON = "idle_garrison"


# Priority order (lower index = higher priority)
TASK_PRIORITY = [
    AITask.DEFEND_HOME,
    AITask.WAR_ORDERS,
    AITask.PATROL,
    AITask.HUNT_BANDITS,
    AITask.PILLAGE,
    AITask.REINFORCE,
    AITask.IDLE_GARRISON,
]

# Bandit-like team IDs
BANDIT_TEAMS = {90, 91, 92, 93, 94}


def pick_personality():
    """Pick a random personality, weighted toward common types."""
    weights = {
        GeneralPersonality.AGGRESSIVE: 30,
        GeneralPersonality.CAUTIOUS: 25,
        GeneralPersonality.LOYAL: 20,
        GeneralPersonality.AMBITIOUS: 15,
        GeneralPersonality.GREEDY: 10,
    }
    choices = list(weights.keys())
    w = [weights[c] for c in choices]
    return random.choices(choices, weights=w, k=1)[0]


class ArmyAI:
    """AI controller attached to a single army.

    Evaluates priority-based tasks and issues move orders.
    """

    def __init__(self, army, personality=None):
        self.army = army
        self.personality = personality or pick_personality()
        self.current_task = AITask.IDLE_GARRISON
        self.task_target = None  # (x, y) or reference
        self.task_cooldown = 0  # ticks before re-evaluating
        self.loyalty = random.randint(50, 90)  # 0-100 loyalty to faction

    def update(self, armies, settlements, diplomacy):
        """Evaluate priorities and issue orders. Called every AI tick."""
        if self.task_cooldown > 0:
            self.task_cooldown -= 1
            # Still moving toward current target
            self.army.update()
            return

        task, target = self._evaluate_priorities(armies, settlements, diplomacy)
        self.current_task = task
        self.task_target = target

        if target:
            tx, ty = target
            # Add personality-based jitter
            jitter = 40 if self.personality == GeneralPersonality.CAUTIOUS else 80
            tx += random.randint(-jitter, jitter)
            ty += random.randint(-jitter, jitter)
            self.army.give_move_order(tx, ty)

        # Re-evaluate after some ticks (personality affects frequency)
        if self.personality == GeneralPersonality.AGGRESSIVE:
            self.task_cooldown = random.randint(20, 50)
        elif self.personality == GeneralPersonality.CAUTIOUS:
            self.task_cooldown = random.randint(40, 80)
        else:
            self.task_cooldown = random.randint(30, 60)

        self.army.update()

    def _evaluate_priorities(self, armies, settlements, diplomacy):
        """Return (task, (x,y)) for the highest-priority actionable task."""
        team = self.army.team

        # 1. DEFEND HOME - check if any own settlement is under attack
        target = self._check_defend_home(armies, settlements, diplomacy)
        if target:
            return AITask.DEFEND_HOME, target

        # 2. WAR ORDERS - attack enemy armies/settlements
        target = self._check_war_orders(armies, settlements, diplomacy)
        if target:
            return AITask.WAR_ORDERS, target

        # 3. PATROL - move between own settlements
        target = self._check_patrol(settlements)
        if target:
            return AITask.PATROL, target

        # 4. HUNT BANDITS
        target = self._check_hunt_bandits(armies)
        if target:
            return AITask.HUNT_BANDITS, target

        # 5. PILLAGE (aggressive/greedy only when at war)
        target = self._check_pillage(settlements, diplomacy)
        if target:
            return AITask.PILLAGE, target

        # 6. REINFORCE - move to outnumbered friendly army
        target = self._check_reinforce(armies, diplomacy)
        if target:
            return AITask.REINFORCE, target

        # 7. IDLE/GARRISON - go to nearest friendly settlement
        target = self._check_idle_garrison(settlements)
        if target:
            return AITask.IDLE_GARRISON, target

        # Fallback: wander
        return AITask.IDLE_GARRISON, (
            self.army.x + random.randint(-100, 100),
            self.army.y + random.randint(-100, 100),
        )

    def _check_defend_home(self, armies, settlements, diplomacy):
        """Check if any owned settlement has an enemy army nearby."""
        team = self.army.team
        own_settlements = [s for s in settlements if s.owner == team]
        if not own_settlements:
            return None

        for s in own_settlements:
            for a in armies:
                if a.team == team or a.is_player:
                    # Check if player is at war
                    if a.is_player and not diplomacy.are_at_war(team, 0):
                        continue
                    elif not a.is_player and not diplomacy.are_at_war(team, a.team):
                        continue
                if a.team != team and diplomacy.are_at_war(team, a.team):
                    if distance(a.x, a.y, s.x, s.y) < 200:
                        return (s.x, s.y)
        return None

    def _check_war_orders(self, armies, settlements, diplomacy):
        """Find enemy armies or settlements to attack."""
        team = self.army.team
        enemies = [a for a in armies
                   if a.team != team and not a.is_player
                   and diplomacy.are_at_war(team, a.team)]

        # Also consider player if at war
        player = next((a for a in armies if a.is_player), None)
        if player and diplomacy.are_at_war(team, 0):
            enemies.append(player)

        # Personality modifies willingness to attack
        if self.personality == GeneralPersonality.CAUTIOUS:
            # Only attack weaker enemies
            enemies = [e for e in enemies
                       if e.army_strength < self.army.army_strength * 1.2]
        elif self.personality == GeneralPersonality.AGGRESSIVE:
            pass  # attack anyone

        if enemies:
            # Aggressive: chase nearest enemy
            # Others: 60% chance to chase, 40% to target settlement
            if self.personality == GeneralPersonality.AGGRESSIVE or random.random() < 0.6:
                nearest = min(enemies, key=lambda e: distance(
                    self.army.x, self.army.y, e.x, e.y))
                return (nearest.x, nearest.y)

        # Attack enemy settlements
        enemy_settlements = [s for s in settlements
                             if s.owner is not None and s.owner != team
                             and diplomacy.are_at_war(team, s.owner)
                             and self.army.army_strength > s.garrison_strength]
        if enemy_settlements:
            if self.personality in (GeneralPersonality.AGGRESSIVE, GeneralPersonality.GREEDY):
                target = min(enemy_settlements,
                             key=lambda s: distance(self.army.x, self.army.y, s.x, s.y))
                return (target.x, target.y)
            elif random.random() < 0.3:
                target = random.choice(enemy_settlements)
                return (target.x, target.y)

        return None

    def _check_patrol(self, settlements):
        """Patrol between own settlements."""
        team = self.army.team
        own = [s for s in settlements if s.owner == team]
        if not own:
            return None

        # Cautious/Loyal: prefer patrolling near settlements
        if self.personality in (GeneralPersonality.CAUTIOUS, GeneralPersonality.LOYAL):
            if random.random() < 0.7:
                target = random.choice(own)
                return (target.x, target.y)
        elif random.random() < 0.4:
            target = random.choice(own)
            return (target.x, target.y)

        return None

    def _check_hunt_bandits(self, armies):
        """Find bandit armies to destroy."""
        bandits = [a for a in armies if a.team in BANDIT_TEAMS
                   and a.army_strength < self.army.army_strength * 1.5]
        if not bandits:
            return None

        # Aggressive/Loyal hunt bandits more
        chance = 0.4
        if self.personality == GeneralPersonality.AGGRESSIVE:
            chance = 0.6
        elif self.personality == GeneralPersonality.CAUTIOUS:
            chance = 0.2

        if random.random() < chance:
            nearest = min(bandits, key=lambda b: distance(
                self.army.x, self.army.y, b.x, b.y))
            # Only if reasonably close
            if distance(self.army.x, self.army.y, nearest.x, nearest.y) < 800:
                return (nearest.x, nearest.y)
        return None

    def _check_pillage(self, settlements, diplomacy):
        """Raid enemy villages (greedy/aggressive only)."""
        if self.personality not in (GeneralPersonality.AGGRESSIVE, GeneralPersonality.GREEDY):
            return None

        team = self.army.team
        targets = [s for s in settlements
                   if s.owner is not None and s.owner != team
                   and diplomacy.are_at_war(team, s.owner)
                   and s.settlement_type == "village"
                   and self.army.army_strength > s.garrison_strength]
        if targets and random.random() < 0.4:
            target = min(targets, key=lambda s: distance(
                self.army.x, self.army.y, s.x, s.y))
            return (target.x, target.y)
        return None

    def _check_reinforce(self, armies, diplomacy):
        """Move toward friendly army that is outnumbered."""
        team = self.army.team
        friendlies = [a for a in armies if a.team == team and a is not self.army]
        if not friendlies:
            return None

        for ally in friendlies:
            # Check if any enemy is nearby and stronger
            for enemy in armies:
                if enemy.team != team and diplomacy.are_at_war(team, enemy.team):
                    if (distance(ally.x, ally.y, enemy.x, enemy.y) < 300 and
                            enemy.army_strength > ally.army_strength):
                        if self.personality == GeneralPersonality.LOYAL or random.random() < 0.3:
                            return (ally.x, ally.y)
        return None

    def _check_idle_garrison(self, settlements):
        """Return to nearest friendly settlement to rest."""
        team = self.army.team
        own = [s for s in settlements if s.owner == team]
        if own:
            nearest = min(own, key=lambda s: distance(
                self.army.x, self.army.y, s.x, s.y))
            return (nearest.x, nearest.y)
        return None

    def serialize(self):
        """Serialize AI state for save system."""
        return {
            "personality": self.personality,
            "current_task": self.current_task,
            "task_cooldown": self.task_cooldown,
            "loyalty": self.loyalty,
        }

    def deserialize(self, data):
        """Restore AI state from save data."""
        self.personality = data.get("personality", self.personality)
        self.current_task = data.get("current_task", AITask.IDLE_GARRISON)
        self.task_cooldown = data.get("task_cooldown", 0)
        self.loyalty = data.get("loyalty", self.loyalty)
