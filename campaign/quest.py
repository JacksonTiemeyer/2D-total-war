"""Quest system - faction quests and bounty board (B3).

Quest types: Patrol, Hunt Bandits, Escort, Raid, Deliver Message, Rescue.
Quests are generated at settlements and tracked via the campaign HUD.
"""

import random
from core.utils import distance


class QuestStatus:
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestType:
    PATROL = "patrol"
    HUNT_BANDITS = "hunt_bandits"
    RAID = "raid"
    DELIVER_MESSAGE = "deliver_message"
    RESCUE = "rescue"
    BOUNTY = "bounty"  # generic bounty board quest


class Quest:
    """A single quest with objectives, rewards, and tracking."""

    def __init__(self, quest_type, title, description, faction_team=None,
                 target_x=None, target_y=None, target_name=None,
                 gold_reward=0, rep_reward=0, time_limit=0,
                 kill_target_team=None, kill_count=0):
        self.quest_type = quest_type
        self.title = title
        self.description = description
        self.faction_team = faction_team  # which faction offered it (None = bounty board)
        self.status = QuestStatus.AVAILABLE

        # Location objective
        self.target_x = target_x
        self.target_y = target_y
        self.target_name = target_name

        # Rewards
        self.gold_reward = gold_reward
        self.rep_reward = rep_reward

        # Time limit (0 = no limit)
        self.time_limit = time_limit
        self.days_remaining = time_limit

        # Kill objectives
        self.kill_target_team = kill_target_team
        self.kill_count = kill_count
        self.kills_done = 0

        # Day accepted
        self.accepted_day = 0

    @property
    def is_location_quest(self):
        return self.target_x is not None and self.target_y is not None

    @property
    def is_kill_quest(self):
        return self.kill_count > 0

    def check_completion(self, player_army, day):
        """Check if quest objectives are met. Returns True if newly completed."""
        if self.status != QuestStatus.ACTIVE:
            return False

        # Check time limit
        if self.time_limit > 0:
            self.days_remaining = self.time_limit - (day - self.accepted_day)
            if self.days_remaining <= 0:
                self.status = QuestStatus.FAILED
                return False

        # Location objective: reach target
        if self.is_location_quest:
            if distance(player_army.x, player_army.y,
                        self.target_x, self.target_y) < 60:
                if not self.is_kill_quest:
                    self.status = QuestStatus.COMPLETED
                    return True

        # Kill objective
        if self.is_kill_quest:
            if self.kills_done >= self.kill_count:
                self.status = QuestStatus.COMPLETED
                return True

        return False

    def accept(self, day):
        self.status = QuestStatus.ACTIVE
        self.accepted_day = day

    def serialize(self):
        return {
            "quest_type": self.quest_type,
            "title": self.title,
            "description": self.description,
            "faction_team": self.faction_team,
            "status": self.status,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "target_name": self.target_name,
            "gold_reward": self.gold_reward,
            "rep_reward": self.rep_reward,
            "time_limit": self.time_limit,
            "days_remaining": self.days_remaining,
            "kill_target_team": self.kill_target_team,
            "kill_count": self.kill_count,
            "kills_done": self.kills_done,
            "accepted_day": self.accepted_day,
        }

    @staticmethod
    def deserialize(data):
        q = Quest(
            data["quest_type"], data["title"], data["description"],
            faction_team=data.get("faction_team"),
            target_x=data.get("target_x"),
            target_y=data.get("target_y"),
            target_name=data.get("target_name"),
            gold_reward=data.get("gold_reward", 0),
            rep_reward=data.get("rep_reward", 0),
            time_limit=data.get("time_limit", 0),
            kill_target_team=data.get("kill_target_team"),
            kill_count=data.get("kill_count", 0),
        )
        q.status = data.get("status", QuestStatus.AVAILABLE)
        q.days_remaining = data.get("days_remaining", q.time_limit)
        q.kills_done = data.get("kills_done", 0)
        q.accepted_day = data.get("accepted_day", 0)
        return q


class QuestManager:
    """Manages quest generation, tracking, and completion."""

    MAX_ACTIVE_QUESTS = 5
    BOUNTY_BOARD_SIZE = 3
    REFRESH_INTERVAL = 7  # days between bounty board refresh

    def __init__(self):
        self.active_quests = []  # player's accepted quests
        self.bounty_board = []   # available at settlements
        self.completed_count = 0
        self.last_refresh_day = 0

    def generate_bounty_board(self, settlements, factions, day,
                              armies=None, roaming_manager=None, scene=None):
        """Generate new bounty board quests."""
        if day - self.last_refresh_day < self.REFRESH_INTERVAL and self.bounty_board:
            return
        self.last_refresh_day = day
        self.bounty_board = []
        self._armies = armies
        self._roaming_manager = roaming_manager
        self._scene = scene

        for _ in range(self.BOUNTY_BOARD_SIZE):
            quest = self._generate_random_quest(settlements, factions)
            if quest:
                self.bounty_board.append(quest)

        self._armies = None
        self._roaming_manager = None
        self._scene = None

    def _generate_random_quest(self, settlements, factions):
        """Create a random quest."""
        quest_type = random.choice([
            QuestType.PATROL, QuestType.HUNT_BANDITS,
            QuestType.RAID, QuestType.BOUNTY,
        ])

        if quest_type == QuestType.PATROL:
            return self._gen_patrol_quest(settlements)
        elif quest_type == QuestType.HUNT_BANDITS:
            return self._gen_hunt_quest(settlements)
        elif quest_type == QuestType.RAID:
            return self._gen_raid_quest(settlements, factions)
        else:
            return self._gen_bounty_quest(settlements)

    def _gen_patrol_quest(self, settlements):
        if len(settlements) < 2:
            return None
        targets = random.sample(settlements, 2)
        t = targets[1]
        gold = random.randint(40, 100)
        return Quest(
            QuestType.PATROL,
            f"Patrol to {t.name}",
            f"Travel to {t.name} to secure the roads.",
            target_x=t.x, target_y=t.y, target_name=t.name,
            gold_reward=gold, rep_reward=5,
            time_limit=random.randint(15, 30),
        )

    def _gen_hunt_quest(self, settlements):
        from campaign.faction import TEAM_BANDITS
        gold = random.randint(60, 150)
        count = random.randint(1, 3)
        if not settlements:
            return None
        s = random.choice(settlements)
        # Ensure bandits actually exist near the quest target
        if (self._roaming_manager and self._armies is not None
                and self._scene is not None):
            self._roaming_manager.ensure_bandits_near(
                s.x, s.y, self._armies, settlements, self._scene, count=count)
        return Quest(
            QuestType.HUNT_BANDITS,
            f"Hunt Bandits near {s.name}",
            f"Destroy {count} bandit group(s) near {s.name}.",
            target_x=s.x, target_y=s.y, target_name=s.name,
            gold_reward=gold, rep_reward=10,
            kill_target_team=TEAM_BANDITS, kill_count=count,
            time_limit=random.randint(20, 40),
        )

    def _gen_raid_quest(self, settlements, factions):
        # Find an enemy settlement
        enemy_settlements = [s for s in settlements if s.owner and s.owner > 0]
        if not enemy_settlements:
            return self._gen_bounty_quest(settlements)
        t = random.choice(enemy_settlements)
        gold = random.randint(80, 200)
        return Quest(
            QuestType.RAID,
            f"Raid {t.name}",
            f"Attack the settlement of {t.name}.",
            target_x=t.x, target_y=t.y, target_name=t.name,
            gold_reward=gold, rep_reward=15,
            time_limit=random.randint(25, 50),
        )

    def _gen_bounty_quest(self, settlements):
        if not settlements:
            return None
        t = random.choice(settlements)
        gold = random.randint(30, 80)
        return Quest(
            QuestType.BOUNTY,
            f"Visit {t.name}",
            f"Travel to {t.name} to collect a bounty.",
            target_x=t.x, target_y=t.y, target_name=t.name,
            gold_reward=gold, rep_reward=3,
            time_limit=random.randint(20, 40),
        )

    def accept_quest(self, quest, day):
        """Player accepts a quest from the bounty board."""
        if len(self.active_quests) >= self.MAX_ACTIVE_QUESTS:
            return False
        quest.accept(day)
        self.active_quests.append(quest)
        if quest in self.bounty_board:
            self.bounty_board.remove(quest)
        return True

    def update(self, player_army, day, diplomacy=None):
        """Check quest completion and time limits."""
        completed = []
        failed = []
        for q in self.active_quests:
            if q.check_completion(player_army, day):
                completed.append(q)
            elif q.status == QuestStatus.FAILED:
                failed.append(q)

        # Process completed quests
        for q in completed:
            player_army.gold += q.gold_reward
            if q.faction_team is not None and diplomacy:
                diplomacy.modify_relation(0, q.faction_team, q.rep_reward)
            self.completed_count += 1

        # Remove completed/failed
        self.active_quests = [q for q in self.active_quests
                              if q.status == QuestStatus.ACTIVE]

        return completed, failed

    def record_kill(self, enemy_team):
        """Record an enemy army kill for kill-based quests."""
        for q in self.active_quests:
            if q.is_kill_quest and q.kill_target_team == enemy_team:
                q.kills_done += 1

    def serialize(self):
        return {
            "active_quests": [q.serialize() for q in self.active_quests],
            "bounty_board": [q.serialize() for q in self.bounty_board],
            "completed_count": self.completed_count,
            "last_refresh_day": self.last_refresh_day,
        }

    def deserialize(self, data):
        self.active_quests = [Quest.deserialize(qd)
                              for qd in data.get("active_quests", [])]
        self.bounty_board = [Quest.deserialize(qd)
                             for qd in data.get("bounty_board", [])]
        self.completed_count = data.get("completed_count", 0)
        self.last_refresh_day = data.get("last_refresh_day", 0)
