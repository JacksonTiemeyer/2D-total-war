"""Shared orchestration helpers for game-state handoffs."""

from core.contracts import (
    BattleStats,
    CompanionBattlePayload,
    GeneralBattleStats,
    SquadBattleStats,
)


def build_companion_payloads(campaign):
    """Build companion battle deployment payloads from campaign state."""
    if not campaign or not hasattr(campaign, "companion_manager"):
        return None

    from data.unit_types import SWORDSMEN

    companions = campaign.companion_manager.companions
    if not companions:
        return None

    payloads = []
    for companion in companions:
        if not companion.alive:
            continue
        payloads.append(
            CompanionBattlePayload(
                name=companion.name,
                stats=SWORDSMEN,
                level=companion.level,
                player_class=companion.companion_class,
            )
        )
    return payloads or None


def collect_battle_stats(battle, current_enemy=None) -> BattleStats:
    """Build a structured post-battle summary payload."""
    player_squads = []
    enemy_squads = []
    total_player_kills = 0
    total_enemy_kills = 0

    for squad in battle.player_squads:
        entry = SquadBattleStats(
            name=squad.unit_stats.name,
            initial=squad.initial_count,
            alive=squad.alive_count,
            kills=squad.kills,
            exhaustion=squad.exhaustion_display,
        )
        player_squads.append(entry)
        total_player_kills += squad.kills

    for squad in battle.enemy_squads:
        entry = SquadBattleStats(
            name=squad.unit_stats.name,
            initial=squad.initial_count,
            alive=squad.alive_count,
            kills=squad.kills,
        )
        enemy_squads.append(entry)
        total_enemy_kills += squad.kills

    dead_generals = getattr(battle, "_dead_generals", [])
    player_generals = [
        GeneralBattleStats(
            name=general.name,
            type=general.general_type,
            kills=general.kills,
            duels_won=general.duels_won,
            level=general.level,
            alive=general.alive,
        )
        for general in battle.player_generals + [g for g in dead_generals if g.team == 0]
    ]
    enemy_generals = [
        GeneralBattleStats(
            name=general.name,
            type=general.general_type,
            kills=general.kills,
            duels_won=general.duels_won,
            level=general.level,
            alive=general.alive,
        )
        for general in battle.enemy_generals + [g for g in dead_generals if g.team == 1]
    ]

    loot_gold = 0
    if battle.result == "player_win" and current_enemy is not None:
        base_loot = 50
        strength_loot = current_enemy.army_strength // 5
        squad_loot = len(current_enemy.squads) * 15
        loot_gold = base_loot + strength_loot + squad_loot

    mvp = None
    if player_squads:
        top = max(player_squads, key=lambda squad: squad.kills)
        if top.kills > 0:
            mvp = top.name

    enemy_initial = sum(squad.initial for squad in enemy_squads)
    player_initial = sum(squad.initial for squad in player_squads)
    heroic_victory = battle.result == "player_win" and enemy_initial > player_initial

    return BattleStats(
        result=battle.result,
        duration_frames=battle.battle_timer,
        player_squads=player_squads,
        enemy_squads=enemy_squads,
        player_generals=player_generals,
        enemy_generals=enemy_generals,
        total_player_kills=total_player_kills,
        total_enemy_kills=total_enemy_kills,
        loot_gold=loot_gold,
        mvp=mvp,
        heroic_victory=heroic_victory,
    )
