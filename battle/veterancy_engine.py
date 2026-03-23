"""VeterancyEngine - centralized veterancy and post-battle XP propagation.

Handles XP formula calculation, level-up checks, and squad veterancy
progression. Centralizes logic previously in main.py._award_post_battle_xp().
"""


class VeterancyEngine:
    """Engine for veterancy tracking and XP distribution."""

    def __init__(self):
        pass

    def calculate_xp(self, battle_stats):
        """Calculate XP earned from a battle based on stats.

        Formula: base_xp * (1 + strength_ratio) * win_mult * (1 - casualty_ratio * 0.5)

        Args:
            battle_stats: Dict with 'result', 'enemy_squads', 'player_squads'.
                Each squad entry has 'initial' and 'alive' counts.

        Returns:
            int: XP amount (minimum 1).
        """
        from battle.battle_scene import BattleResult

        if not battle_stats:
            return 0

        is_win = battle_stats.get("result") == BattleResult.PLAYER_WIN
        win_mult = 1.0 if is_win else 0.4

        enemy_initial = sum(sq["initial"] for sq in battle_stats.get("enemy_squads", []))
        player_initial = sum(sq["initial"] for sq in battle_stats.get("player_squads", []))
        strength_ratio = enemy_initial / max(1, player_initial)

        player_survived = sum(sq["alive"] for sq in battle_stats.get("player_squads", []))
        casualty_ratio = 1.0 - (player_survived / max(1, player_initial))

        base_xp = 5
        xp = int(base_xp * (1.0 + strength_ratio) * win_mult * (1.0 - casualty_ratio * 0.5))
        return max(1, xp)

    def award_xp(self, general, amount):
        """Award XP to a general and handle level ups.

        Args:
            general: Object with 'xp' attribute (and optionally 'level').
            amount: XP amount to award.
        """
        if not hasattr(general, 'xp'):
            return
        general.xp += amount
        from battle.abilities import level_from_xp
        next_level = level_from_xp(general.xp)
        if hasattr(general, 'level') and next_level > general.level:
            general.level = next_level

    def distribute_battle_xp(self, battle_stats, campaign, player_character=None):
        """Full post-battle XP distribution to general, player character, and companions.

        This replaces main.py._award_post_battle_xp().

        Args:
            battle_stats: Battle stats dict.
            campaign: Campaign object with player_army and companion_manager.
            player_character: Optional player character with add_xp().

        Returns:
            list: Notification strings for level-ups.
        """
        from battle.battle_scene import BattleResult

        notifications = []
        xp = self.calculate_xp(battle_stats)
        if xp == 0:
            return notifications

        is_win = battle_stats.get("result") == BattleResult.PLAYER_WIN

        # Campaign general
        pa = campaign.player_army
        pa.general_xp += xp
        from battle.abilities import level_from_xp
        new_level = level_from_xp(pa.general_xp)
        if new_level > pa.general_level:
            pa.general_level = new_level

        # Player character
        if player_character:
            levels_gained = player_character.add_xp(xp)
            if levels_gained > 0:
                notifications.append(
                    f"Level up! You are now level {player_character.level} ({player_character.tier_name})")

        # Companions
        if hasattr(campaign, 'companion_manager'):
            companion_xp = max(1, xp // 2)
            for comp in campaign.companion_manager.companions:
                if comp.alive:
                    levels = comp.add_xp(companion_xp)
                    if levels > 0:
                        notifications.append(
                            f"Companion {comp.name} is now level {comp.level}!")
                    comp.modify_loyalty(2 if is_win else -1)

        return notifications
