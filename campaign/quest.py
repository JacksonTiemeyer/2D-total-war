"""Quest system - faction quests and bounty boards."""

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
    HIDEOUT = "hideout"
    RAID = "raid"
    DELIVER_MESSAGE = "deliver_message"
    RESCUE = "rescue"
    BOUNTY = "bounty"


class Quest:
    """A single quest with objectives, rewards, and visibility rules."""

    def __init__(self, quest_type, title, description, faction_team=None,
                 target_x=None, target_y=None, target_name=None,
                 gold_reward=0, rep_reward=0, time_limit=0,
                 kill_target_team=None, kill_count=0,
                 origin_settlement=None, local_only=True,
                 kill_radius=None, requires_settlement_capture=False):
        self.quest_type = quest_type
        self.title = title
        self.description = description
        self.faction_team = faction_team
        self.status = QuestStatus.AVAILABLE

        self.target_x = target_x
        self.target_y = target_y
        self.target_name = target_name

        self.gold_reward = gold_reward
        self.rep_reward = rep_reward

        self.time_limit = time_limit
        self.days_remaining = time_limit

        self.kill_target_team = kill_target_team
        self.kill_count = kill_count
        self.kills_done = 0
        self.kill_radius = kill_radius
        self.requires_settlement_capture = requires_settlement_capture

        self.origin_settlement = origin_settlement
        self.local_only = local_only

        self.accepted_day = 0

    @property
    def is_location_quest(self):
        return self.target_x is not None and self.target_y is not None

    @property
    def is_kill_quest(self):
        return self.kill_count > 0

    def is_available_in_settlement(self, settlement):
        """Local quests are shown only in their faction's settlements."""
        if self.status != QuestStatus.AVAILABLE:
            return False
        if not self.local_only:
            return True
        if self.faction_team is not None and settlement.owner == self.faction_team:
            return True
        return settlement.name == self.origin_settlement

    def check_completion(self, player_army, day):
        """Check if quest objectives are met. Returns True if newly completed."""
        if self.status != QuestStatus.ACTIVE:
            return False

        if self.time_limit > 0:
            self.days_remaining = self.time_limit - (day - self.accepted_day)
            if self.days_remaining <= 0:
                self.status = QuestStatus.FAILED
                return False

        if (self.is_location_quest and not self.is_kill_quest and
                not self.requires_settlement_capture):
            if distance(player_army.x, player_army.y,
                        self.target_x, self.target_y) < 60:
                self.status = QuestStatus.COMPLETED
                return True

        if self.is_kill_quest and self.kills_done >= self.kill_count:
            self.status = QuestStatus.COMPLETED
            return True

        return False

    def record_kill(self, enemy_team, kill_x=None, kill_y=None):
        """Record a nearby kill for localized hunt/hideout quests."""
        if self.status != QuestStatus.ACTIVE:
            return
        if not self.is_kill_quest or self.kill_target_team != enemy_team:
            return
        if (self.kill_radius is not None and kill_x is not None and kill_y is not None
                and self.target_x is not None and self.target_y is not None):
            if distance(kill_x, kill_y, self.target_x, self.target_y) > self.kill_radius:
                return
        self.kills_done += 1

    def record_settlement_capture(self, settlement_name):
        """Mark capture-based quests complete after the target actually falls."""
        if self.status != QuestStatus.ACTIVE:
            return
        if self.requires_settlement_capture and settlement_name == self.target_name:
            self.status = QuestStatus.COMPLETED

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
            "kill_radius": self.kill_radius,
            "requires_settlement_capture": self.requires_settlement_capture,
            "origin_settlement": self.origin_settlement,
            "local_only": self.local_only,
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
            origin_settlement=data.get("origin_settlement"),
            local_only=data.get("local_only", True),
            kill_radius=data.get("kill_radius"),
            requires_settlement_capture=data.get("requires_settlement_capture", False),
        )
        q.status = data.get("status", QuestStatus.AVAILABLE)
        q.days_remaining = data.get("days_remaining", q.time_limit)
        q.kills_done = data.get("kills_done", 0)
        q.accepted_day = data.get("accepted_day", 0)
        return q


class QuestManager:
    """Manages quest generation, tracking, and completion."""

    MAX_ACTIVE_QUESTS = 5
    LOCAL_QUESTS_PER_FACTION = 2
    GLOBAL_QUESTS = 3
    REFRESH_INTERVAL = 7

    def __init__(self):
        self.active_quests = []
        self.bounty_board = []
        self.completed_count = 0
        self.last_refresh_day = 0

    def generate_bounty_board(self, settlements, factions, day,
                              armies=None, roaming_manager=None, scene=None):
        """Generate faction-local quests plus a few global jobs."""
        if day - self.last_refresh_day < self.REFRESH_INTERVAL and self.bounty_board:
            return
        self.last_refresh_day = day
        self.bounty_board = []
        self._settlements = settlements
        self._armies = armies
        self._roaming_manager = roaming_manager
        self._scene = scene

        settlements_by_owner = {}
        for settlement in settlements:
            if settlement.owner is not None:
                settlements_by_owner.setdefault(settlement.owner, []).append(settlement)

        for team, team_settlements in settlements_by_owner.items():
            for _ in range(self.LOCAL_QUESTS_PER_FACTION):
                quest = self._generate_local_quest(team_settlements, team)
                if quest:
                    self.bounty_board.append(quest)

        for _ in range(self.GLOBAL_QUESTS):
            quest = self._gen_raid_quest(settlements, factions)
            if quest:
                self.bounty_board.append(quest)

        self._armies = None
        self._roaming_manager = None
        self._scene = None
        self._settlements = None

    def get_bounty_board(self, settlement=None):
        if settlement is None:
            return list(self.bounty_board)
        return [q for q in self.bounty_board if q.is_available_in_settlement(settlement)]

    def _generate_local_quest(self, settlements, faction_team):
        quest_type = random.choice([
            QuestType.PATROL,
            QuestType.HUNT_BANDITS,
            QuestType.HIDEOUT,
            QuestType.BOUNTY,
        ])
        if quest_type == QuestType.PATROL:
            return self._gen_patrol_quest(settlements, faction_team)
        if quest_type == QuestType.HUNT_BANDITS:
            return self._gen_hunt_quest(settlements, faction_team)
        if quest_type == QuestType.HIDEOUT:
            return self._gen_hideout_quest(settlements, faction_team)
        return self._gen_bounty_quest(settlements, faction_team)

    def _gen_patrol_quest(self, settlements, faction_team=None):
        if not settlements:
            return None
        origin = random.choice(settlements)
        target = random.choice(settlements)
        gold = random.randint(40, 100)
        return Quest(
            QuestType.PATROL,
            f"Patrol to {target.name}",
            f"Travel to {target.name} to secure the roads.",
            faction_team=faction_team,
            target_x=target.x, target_y=target.y, target_name=target.name,
            gold_reward=gold, rep_reward=5,
            time_limit=random.randint(15, 30),
            origin_settlement=origin.name,
            local_only=True,
        )

    def _gen_hunt_quest(self, settlements, faction_team=None):
        from campaign.faction import TEAM_BANDITS
        if not settlements:
            return None
        origin = random.choice(settlements)
        gold = random.randint(60, 150)
        count = random.randint(1, 3)
        if (self._roaming_manager and self._armies is not None and self._scene is not None):
            self._roaming_manager.ensure_bandits_near(
                origin.x, origin.y, self._armies, self._settlements or settlements,
                self._scene, count=count)
        return Quest(
            QuestType.HUNT_BANDITS,
            f"Hunt Bandits near {origin.name}",
            f"Destroy {count} bandit group(s) near {origin.name}.",
            faction_team=faction_team,
            target_x=origin.x, target_y=origin.y, target_name=origin.name,
            gold_reward=gold, rep_reward=10,
            kill_target_team=TEAM_BANDITS, kill_count=count,
            time_limit=random.randint(20, 40),
            origin_settlement=origin.name,
            local_only=True,
            kill_radius=450,
        )

    def _gen_hideout_quest(self, settlements, faction_team=None):
        from campaign.faction import (
            TEAM_BANDITS, TEAM_CULTISTS, TEAM_CANNIBALS,
            TEAM_DESERTERS, TEAM_GOBLINS,
        )

        if not settlements:
            return None
        origin = random.choice(settlements)
        team = random.choice([
            TEAM_BANDITS, TEAM_CULTISTS, TEAM_CANNIBALS,
            TEAM_DESERTERS, TEAM_GOBLINS,
        ])
        label_by_team = {
            TEAM_BANDITS: "Bandit Hideout",
            TEAM_CULTISTS: "Cultist Hideout",
            TEAM_CANNIBALS: "Cannibal Camp",
            TEAM_DESERTERS: "Deserter Camp",
            TEAM_GOBLINS: "Goblin Den",
        }
        label = label_by_team[team]
        target_x, target_y = origin.x, origin.y
        target_name = label

        if (self._roaming_manager and self._armies is not None and self._scene is not None):
            hideout = self._roaming_manager.ensure_hideout_near(
                origin.x, origin.y, team, self._armies, self._settlements or settlements,
                self._scene,
                guard_count=random.randint(1, 2))
            target_x, target_y = hideout.x, hideout.y
            target_name = hideout.name

        return Quest(
            QuestType.HIDEOUT,
            f"Destroy {label} near {origin.name}",
            f"Track down the {label.lower()} threatening {origin.name} and wipe out its guards.",
            faction_team=faction_team,
            target_x=target_x, target_y=target_y, target_name=target_name,
            gold_reward=random.randint(90, 180), rep_reward=12,
            time_limit=random.randint(20, 40),
            kill_target_team=team, kill_count=1,
            origin_settlement=origin.name,
            local_only=True,
            kill_radius=260,
        )

    def _gen_raid_quest(self, settlements, factions):
        enemy_settlements = [s for s in settlements if s.owner and s.owner > 0]
        if not enemy_settlements:
            return None
        target = random.choice(enemy_settlements)
        gold = random.randint(80, 200)
        return Quest(
            QuestType.RAID,
            f"Raid {target.name}",
            f"Besiege and capture {target.name}.",
            faction_team=None,
            target_x=target.x, target_y=target.y, target_name=target.name,
            gold_reward=gold, rep_reward=15,
            time_limit=random.randint(25, 50),
            origin_settlement=target.name,
            local_only=False,
            requires_settlement_capture=True,
        )

    def _gen_bounty_quest(self, settlements, faction_team=None):
        if not settlements:
            return None
        origin = random.choice(settlements)
        target = random.choice(settlements)
        gold = random.randint(30, 80)
        return Quest(
            QuestType.BOUNTY,
            f"Visit {target.name}",
            f"Travel to {target.name} to collect a bounty.",
            faction_team=faction_team,
            target_x=target.x, target_y=target.y, target_name=target.name,
            gold_reward=gold, rep_reward=3,
            time_limit=random.randint(20, 40),
            origin_settlement=origin.name,
            local_only=True,
        )

    def accept_quest(self, quest, day, settlement=None):
        if len(self.active_quests) >= self.MAX_ACTIVE_QUESTS:
            return False
        if settlement is not None and not quest.is_available_in_settlement(settlement):
            return False
        quest.accept(day)
        self.active_quests.append(quest)
        if quest in self.bounty_board:
            self.bounty_board.remove(quest)
        return True

    def update(self, player_army, day, diplomacy=None):
        completed = []
        failed = []
        for quest in self.active_quests:
            if quest.check_completion(player_army, day):
                completed.append(quest)
            elif quest.status == QuestStatus.FAILED:
                failed.append(quest)

        for quest in completed:
            player_army.gold += quest.gold_reward
            if quest.faction_team is not None and diplomacy:
                diplomacy.modify_relation(0, quest.faction_team, quest.rep_reward)
            self.completed_count += 1

        self.active_quests = [q for q in self.active_quests if q.status == QuestStatus.ACTIVE]
        return completed, failed

    def record_kill(self, enemy_army):
        """Record a player-caused army kill for localized kill quests."""
        if enemy_army is None:
            return
        enemy_team = getattr(enemy_army, "team", enemy_army)
        kill_x = getattr(enemy_army, "x", None)
        kill_y = getattr(enemy_army, "y", None)
        for quest in self.active_quests:
            quest.record_kill(enemy_team, kill_x, kill_y)

    def record_settlement_capture(self, settlement_name):
        """Record that the player captured a settlement via quest resolution."""
        for quest in self.active_quests:
            quest.record_settlement_capture(settlement_name)

    def serialize(self):
        return {
            "active_quests": [q.serialize() for q in self.active_quests],
            "bounty_board": [q.serialize() for q in self.bounty_board],
            "completed_count": self.completed_count,
            "last_refresh_day": self.last_refresh_day,
        }

    def deserialize(self, data):
        self.active_quests = [Quest.deserialize(qd) for qd in data.get("active_quests", [])]
        self.bounty_board = [Quest.deserialize(qd) for qd in data.get("bounty_board", [])]
        self.completed_count = data.get("completed_count", 0)
        self.last_refresh_day = data.get("last_refresh_day", 0)
