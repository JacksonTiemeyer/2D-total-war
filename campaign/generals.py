"""General management system - loyalty, betrayal, persuasion, and prisoner mechanics.

B6: General Betrayal & Persuasion
D6: Prisoner & Ransom System
"""

import random
from core.settings import (
    LOYALTY_DEFAULT, LOYALTY_MIN, LOYALTY_MAX,
    LOYALTY_BETRAY_THRESHOLD, LOYALTY_BETRAY_CHANCE_BASE,
    LOYALTY_BETRAY_AMBITIOUS_MULT, LOYALTY_BETRAY_LOYAL_MULT,
    LOYALTY_BATTLE_WIN_BONUS, LOYALTY_BATTLE_LOSS_PENALTY,
    PERSUASION_RANGE,
    BRIBE_COST_BASE, BRIBE_LOYALTY_GAIN, BRIBE_FACTION_LOYALTY_LOSS,
    CONVINCE_BASE_CHANCE, CONVINCE_REP_BONUS,
    THREATEN_BASE_CHANCE, THREATEN_BACKFIRE_CHANCE,
    CAPTURE_CHANCE_BASE, CAPTURE_CHANCE_DECISIVE,
    PLAYER_CAPTURE_DAYS, PLAYER_CAPTURE_RANSOM_BASE, PLAYER_CAPTURE_DISBAND_RATE,
    RANSOM_GOLD_BASE,
    RECRUIT_PRISONER_BASE_CHANCE,
    EXECUTE_REP_PENALTY_FACTION, EXECUTE_REP_PENALTY_ALL,
    EXECUTE_INTIMIDATION_BONUS,
)


class GeneralStatus:
    """Status of a general in the world."""
    ACTIVE = "active"       # leading an army
    CAPTURED = "captured"   # held prisoner
    DEAD = "dead"           # permanently removed (NPC only)


class Prisoner:
    """A captured general held by the player or an AI faction."""
    def __init__(self, general_name, faction_team, personality, general_level=1):
        self.general_name = general_name
        self.faction_team = faction_team
        self.personality = personality
        self.general_level = general_level
        self.days_held = 0

    def serialize(self):
        return {
            "general_name": self.general_name,
            "faction_team": self.faction_team,
            "personality": self.personality,
            "general_level": self.general_level,
            "days_held": self.days_held,
        }

    @staticmethod
    def deserialize(data):
        p = Prisoner(
            data["general_name"],
            data["faction_team"],
            data.get("personality", "cautious"),
            data.get("general_level", 1),
        )
        p.days_held = data.get("days_held", 0)
        return p


class PlayerCaptureState:
    """Tracks the player's capture state when defeated."""
    def __init__(self):
        self.is_captured = False
        self.days_remaining = 0
        self.ransom_cost = 0
        self.captor_team = None  # which faction holds the player

    def serialize(self):
        return {
            "is_captured": self.is_captured,
            "days_remaining": self.days_remaining,
            "ransom_cost": self.ransom_cost,
            "captor_team": self.captor_team,
        }

    def deserialize(self, data):
        self.is_captured = data.get("is_captured", False)
        self.days_remaining = data.get("days_remaining", 0)
        self.ransom_cost = data.get("ransom_cost", 0)
        self.captor_team = data.get("captor_team", None)


class GeneralManager:
    """Manages all named generals: loyalty, status, prisoners, and betrayal.

    Centralizes general tracking so loyalty, capture, death, and persuasion
    work across campaign and battle systems.
    """

    def __init__(self):
        # general_name -> {loyalty, status, faction_team, personality, level}
        self.generals = {}
        # Prisoners held by the player
        self.player_prisoners = []
        # Player capture state
        self.player_capture = PlayerCaptureState()
        # Intimidation bonus from recent executions (decays over time)
        self.intimidation_bonus = 0
        # Track dead generals for permadeath
        self.dead_generals = set()

    def register_general(self, general_name, faction_team, personality=None, level=1):
        """Register a general in the tracking system. Idempotent."""
        if general_name in self.generals:
            return
        if general_name in self.dead_generals:
            return  # permadeath - don't re-register
        self.generals[general_name] = {
            "loyalty": LOYALTY_DEFAULT,
            "status": GeneralStatus.ACTIVE,
            "faction_team": faction_team,
            "personality": personality or "cautious",
            "level": level,
        }

    def get_loyalty(self, general_name):
        """Get a general's loyalty to their faction (0-100)."""
        info = self.generals.get(general_name)
        if info is None:
            return LOYALTY_DEFAULT
        return info["loyalty"]

    def set_loyalty(self, general_name, value):
        """Set loyalty, clamped to valid range."""
        info = self.generals.get(general_name)
        if info:
            info["loyalty"] = max(LOYALTY_MIN, min(LOYALTY_MAX, value))

    def modify_loyalty(self, general_name, delta):
        """Adjust loyalty by delta."""
        current = self.get_loyalty(general_name)
        self.set_loyalty(general_name, current + delta)

    def get_status(self, general_name):
        """Get current status of a general."""
        if general_name in self.dead_generals:
            return GeneralStatus.DEAD
        info = self.generals.get(general_name)
        if info is None:
            return GeneralStatus.ACTIVE
        return info["status"]

    def get_faction(self, general_name):
        """Get which faction a general belongs to."""
        info = self.generals.get(general_name)
        if info is None:
            return None
        return info["faction_team"]

    def get_personality(self, general_name):
        """Get a general's personality trait."""
        info = self.generals.get(general_name)
        if info is None:
            return "cautious"
        return info["personality"]

    # ------------------------------------------------------------------
    # Battle outcome effects
    # ------------------------------------------------------------------

    def on_battle_win(self, general_name):
        """General won a battle - loyalty increases."""
        self.modify_loyalty(general_name, LOYALTY_BATTLE_WIN_BONUS)

    def on_battle_loss(self, general_name):
        """General lost a battle - loyalty decreases."""
        self.modify_loyalty(general_name, -LOYALTY_BATTLE_LOSS_PENALTY)

    # ------------------------------------------------------------------
    # Betrayal system (B6)
    # ------------------------------------------------------------------

    def check_betrayals(self, armies, ai_controllers, diplomacy, add_notification):
        """Called each day. Check if any general with low loyalty defects.

        Returns list of (army, action) where action is 'defect' or 'independent'.
        """
        betrayals = []
        for army in list(armies):
            if army.is_player:
                continue
            name = army.general_name
            info = self.generals.get(name)
            if info is None:
                continue
            if info["status"] != GeneralStatus.ACTIVE:
                continue

            loyalty = info["loyalty"]
            if loyalty >= LOYALTY_BETRAY_THRESHOLD:
                continue

            # Calculate betrayal chance based on personality
            personality = info["personality"]
            chance = LOYALTY_BETRAY_CHANCE_BASE * (
                1.0 + (LOYALTY_BETRAY_THRESHOLD - loyalty) / LOYALTY_BETRAY_THRESHOLD
            )
            if personality == "ambitious":
                chance *= LOYALTY_BETRAY_AMBITIOUS_MULT
            elif personality == "loyal":
                chance *= LOYALTY_BETRAY_LOYAL_MULT
            elif personality == "greedy":
                chance *= 1.5

            if random.random() < chance:
                # Decide: defect to another faction or go independent
                if random.random() < 0.4:
                    # Go independent - become a roaming army
                    action = "independent"
                    add_notification(
                        f"{name} has gone rogue and become independent!")
                else:
                    action = "defect"
                    add_notification(
                        f"{name} has betrayed their faction!")
                betrayals.append((army, action))

        return betrayals

    def process_betrayal(self, army, action, armies, ai_controllers,
                         factions, diplomacy):
        """Execute a betrayal: change army's faction or make independent.

        Returns the new team for the army.
        """
        old_team = army.team
        name = army.general_name

        if action == "independent":
            # Become a roaming independent army (team 99)
            new_team = 99
            army.team = new_team
            info = self.generals.get(name)
            if info:
                info["faction_team"] = new_team
            return new_team

        # Defect to a different faction
        # Pick a faction that is not at war with the general and not same faction
        candidate_teams = []
        for f in factions:
            if f.team != old_team and f.team != 0:
                if not diplomacy.are_at_war(f.team, old_team):
                    candidate_teams.append(f.team)
        if not candidate_teams:
            # If everyone is at war, go independent
            new_team = 99
        else:
            new_team = random.choice(candidate_teams)

        army.team = new_team
        info = self.generals.get(name)
        if info:
            info["faction_team"] = new_team
            info["loyalty"] = LOYALTY_DEFAULT  # reset loyalty to new faction
        return new_team

    # ------------------------------------------------------------------
    # Persuasion system (B6)
    # ------------------------------------------------------------------

    def attempt_bribe(self, general_name, player_army, diplomacy):
        """Attempt to bribe a general. Costs gold, shifts loyalty.

        Returns (success: bool, message: str).
        """
        info = self.generals.get(general_name)
        if info is None:
            return False, "Unknown general."

        personality = info["personality"]
        cost = BRIBE_COST_BASE
        if personality == "greedy":
            cost = int(cost * 0.7)  # greedy generals are cheaper to bribe
        elif personality == "loyal":
            cost = int(cost * 1.5)  # loyal generals cost more

        if player_army.gold < cost:
            return False, f"Not enough gold (need {cost})."

        player_army.gold -= cost

        # Shift loyalty away from faction, improve general's opinion of player
        gain = BRIBE_LOYALTY_GAIN
        if personality == "greedy":
            gain = int(gain * 1.5)
        elif personality == "loyal":
            gain = int(gain * 0.5)

        self.modify_loyalty(general_name, -BRIBE_FACTION_LOYALTY_LOSS)
        diplomacy.modify_general_opinion(general_name, gain)

        return True, f"Bribed {general_name} for {cost} gold. (-{BRIBE_FACTION_LOYALTY_LOSS} loyalty, +{gain} opinion)"

    def attempt_convince(self, general_name, player_army, diplomacy):
        """Attempt to convince a general through persuasion.

        Success based on player reputation and general personality.
        Returns (success: bool, message: str).
        """
        info = self.generals.get(general_name)
        if info is None:
            return False, "Unknown general."

        faction_team = info["faction_team"]
        personality = info["personality"]

        # Base chance + reputation bonus
        player_rep = diplomacy.get_relation(0, faction_team) if faction_team else 0
        gen_opinion = diplomacy.get_general_opinion(general_name)
        chance = CONVINCE_BASE_CHANCE + gen_opinion * CONVINCE_REP_BONUS

        # Personality modifiers
        if personality == "ambitious":
            chance += 0.1  # ambitious generals can be swayed
        elif personality == "loyal":
            chance -= 0.2  # loyal generals resist
        elif personality == "cautious":
            chance += 0.05

        chance = max(0.05, min(0.9, chance))

        if random.random() < chance:
            self.modify_loyalty(general_name, -15)
            diplomacy.modify_general_opinion(general_name, 10)
            return True, f"Convinced {general_name}! (-15 loyalty, +10 opinion)"
        else:
            diplomacy.modify_general_opinion(general_name, -5)
            return False, f"Failed to convince {general_name}. (-5 opinion)"

    def attempt_threaten(self, general_name, player_army, diplomacy):
        """Attempt to threaten a general into compliance.

        Works on cautious generals, backfires on aggressive ones.
        Returns (success: bool, message: str).
        """
        info = self.generals.get(general_name)
        if info is None:
            return False, "Unknown general."

        personality = info["personality"]

        if personality == "aggressive":
            # Backfire check
            if random.random() < THREATEN_BACKFIRE_CHANCE:
                self.modify_loyalty(general_name, 10)  # they dig in
                diplomacy.modify_general_opinion(general_name, -20)
                return False, f"Threat backfired! {general_name} is furious. (-20 opinion)"
            else:
                # Even non-backfire, not very effective
                self.modify_loyalty(general_name, -5)
                return True, f"Barely intimidated {general_name}. (-5 loyalty)"

        chance = THREATEN_BASE_CHANCE
        if personality == "cautious":
            chance += 0.2
        elif personality == "loyal":
            chance -= 0.15
        elif personality == "greedy":
            chance += 0.0  # neutral

        chance = max(0.05, min(0.85, chance))

        if random.random() < chance:
            self.modify_loyalty(general_name, -20)
            diplomacy.modify_general_opinion(general_name, -10)
            return True, f"Threatened {general_name} successfully. (-20 loyalty, -10 opinion)"
        else:
            diplomacy.modify_general_opinion(general_name, -10)
            return False, f"Threat failed against {general_name}. (-10 opinion)"

    # ------------------------------------------------------------------
    # Prisoner & capture system (D6)
    # ------------------------------------------------------------------

    def check_general_capture(self, general_name, battle_was_decisive=False):
        """After a battle loss, check if the general is captured.

        Returns True if captured, False if killed/escaped.
        NPC generals that are not captured are killed (permadeath).
        """
        chance = CAPTURE_CHANCE_DECISIVE if battle_was_decisive else CAPTURE_CHANCE_BASE
        return random.random() < chance

    def capture_npc_general(self, general_name, faction_team, personality,
                            general_level=1):
        """Capture an NPC general as a prisoner of the player."""
        info = self.generals.get(general_name)
        if info:
            info["status"] = GeneralStatus.CAPTURED

        prisoner = Prisoner(general_name, faction_team, personality, general_level)
        self.player_prisoners.append(prisoner)

    def kill_npc_general(self, general_name):
        """Permanently remove an NPC general (permadeath)."""
        self.dead_generals.add(general_name)
        info = self.generals.get(general_name)
        if info:
            info["status"] = GeneralStatus.DEAD
        # Also remove from prisoners if present
        self.player_prisoners = [
            p for p in self.player_prisoners
            if p.general_name != general_name
        ]

    def capture_player(self, captor_team):
        """Player is captured after losing a battle."""
        self.player_capture.is_captured = True
        self.player_capture.days_remaining = PLAYER_CAPTURE_DAYS
        self.player_capture.ransom_cost = PLAYER_CAPTURE_RANSOM_BASE
        self.player_capture.captor_team = captor_team

    def update_player_capture(self, player_army):
        """Called each day while player is captured.

        Returns True if player escapes/released this day.
        """
        if not self.player_capture.is_captured:
            return False

        self.player_capture.days_remaining -= 1
        if self.player_capture.days_remaining <= 0:
            # Auto-escape
            self.player_capture.is_captured = False
            # Disband part of army on escape
            self._disband_partial_army(player_army)
            return True
        return False

    def pay_player_ransom(self, player_army):
        """Player pays ransom to escape immediately.

        Returns (success: bool, message: str).
        """
        if not self.player_capture.is_captured:
            return False, "Not captured."

        cost = self.player_capture.ransom_cost
        if player_army.gold < cost:
            return False, f"Not enough gold (need {cost})."

        player_army.gold -= cost
        self.player_capture.is_captured = False
        return True, f"Paid {cost} gold ransom. You are free!"

    def _disband_partial_army(self, player_army):
        """Disband a portion of the player's army on capture escape."""
        for sq in player_army.squads:
            loss = int(sq.current_count * PLAYER_CAPTURE_DISBAND_RATE)
            sq.current_count = max(1, sq.current_count - loss)
        # Remove empty squads
        player_army.squads = [sq for sq in player_army.squads
                              if sq.current_count > 0]

    def ransom_prisoner(self, prisoner_index, diplomacy):
        """Ransom a prisoner back to their faction for gold.

        Returns (gold_gained: int, message: str) or (0, error_message).
        """
        if prisoner_index < 0 or prisoner_index >= len(self.player_prisoners):
            return 0, "Invalid prisoner."

        prisoner = self.player_prisoners[prisoner_index]
        gold = RANSOM_GOLD_BASE + prisoner.general_level * 50

        # Restore general to active status
        info = self.generals.get(prisoner.general_name)
        if info:
            info["status"] = GeneralStatus.ACTIVE
            info["loyalty"] = LOYALTY_DEFAULT  # reset loyalty

        # Improve relations with that faction
        diplomacy.modify_relation(0, prisoner.faction_team, 5)

        self.player_prisoners.pop(prisoner_index)
        return gold, f"Ransomed {prisoner.general_name} for {gold} gold. (+5 faction rep)"

    def recruit_prisoner(self, prisoner_index, diplomacy):
        """Attempt to recruit a prisoner to the player's side.

        Returns (success: bool, message: str, prisoner_or_none).
        """
        if prisoner_index < 0 or prisoner_index >= len(self.player_prisoners):
            return False, "Invalid prisoner.", None

        prisoner = self.player_prisoners[prisoner_index]
        gen_opinion = diplomacy.get_general_opinion(prisoner.general_name)
        loyalty = self.get_loyalty(prisoner.general_name)

        # Base chance modified by opinion and low loyalty
        chance = RECRUIT_PRISONER_BASE_CHANCE
        chance += gen_opinion * 0.005  # opinion helps
        chance += (LOYALTY_MAX - loyalty) * 0.003  # low loyalty to old faction helps

        if prisoner.personality == "ambitious":
            chance += 0.1
        elif prisoner.personality == "loyal":
            chance -= 0.15
        elif prisoner.personality == "greedy":
            chance += 0.05

        chance = max(0.05, min(0.85, chance))

        if random.random() < chance:
            # Recruited! Remove from prisoners, mark as player's general
            info = self.generals.get(prisoner.general_name)
            if info:
                info["status"] = GeneralStatus.ACTIVE
                info["faction_team"] = 0  # player's team
                info["loyalty"] = 60  # moderate loyalty to start

            # Worsen relations with their old faction
            diplomacy.modify_relation(0, prisoner.faction_team, -10)

            removed = self.player_prisoners.pop(prisoner_index)
            return True, f"Recruited {prisoner.general_name}! They join your cause.", removed
        else:
            return False, f"{prisoner.general_name} refuses to join you.", None

    def execute_prisoner(self, prisoner_index, diplomacy, factions):
        """Execute a prisoner. Permanent death, major rep penalties.

        Returns (message: str).
        """
        if prisoner_index < 0 or prisoner_index >= len(self.player_prisoners):
            return "Invalid prisoner."

        prisoner = self.player_prisoners[prisoner_index]
        name = prisoner.general_name

        # Kill the general permanently
        self.kill_npc_general(name)

        # Major reputation hit with their faction
        diplomacy.modify_relation(0, prisoner.faction_team, EXECUTE_REP_PENALTY_FACTION)

        # Minor reputation hit with all factions
        for f in factions:
            if f.team != 0 and f.team != prisoner.faction_team:
                diplomacy.modify_relation(0, f.team, EXECUTE_REP_PENALTY_ALL)

        # Intimidation bonus for next battle
        self.intimidation_bonus += EXECUTE_INTIMIDATION_BONUS

        return f"Executed {name}. ({EXECUTE_REP_PENALTY_FACTION} rep with faction, {EXECUTE_REP_PENALTY_ALL} with all others, +{EXECUTE_INTIMIDATION_BONUS} intimidation)"

    def consume_intimidation_bonus(self):
        """Get and reset intimidation bonus (used at battle start)."""
        bonus = self.intimidation_bonus
        self.intimidation_bonus = 0
        return bonus

    def update_prisoners(self):
        """Called each day. Advance prisoner timers."""
        for p in self.player_prisoners:
            p.days_held += 1

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self):
        return {
            "generals": self.generals,
            "dead_generals": list(self.dead_generals),
            "player_prisoners": [p.serialize() for p in self.player_prisoners],
            "player_capture": self.player_capture.serialize(),
            "intimidation_bonus": self.intimidation_bonus,
        }

    def deserialize(self, data):
        self.generals = data.get("generals", {})
        self.dead_generals = set(data.get("dead_generals", []))
        self.player_prisoners = [
            Prisoner.deserialize(pd) for pd in data.get("player_prisoners", [])
        ]
        if "player_capture" in data:
            self.player_capture.deserialize(data["player_capture"])
        self.intimidation_bonus = data.get("intimidation_bonus", 0)
