"""Shared architecture contracts for cross-system handoffs."""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class CompanionBattlePayload:
    """Companion deployment data consumed by battle scenes."""

    name: str
    stats: Any
    level: int = 1
    player_class: Optional[str] = None

    def to_legacy_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneralBattlePayload:
    """General deployment data consumed by battle scenes."""

    name: str
    stats: Any
    xp: int = 0
    level: int = 1
    player_class: Optional[str] = None

    def to_legacy_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "stats": self.stats,
            "xp": self.xp,
            "level": self.level,
        }
        if self.player_class is not None:
            data["player_class"] = self.player_class
        return data


@dataclass(frozen=True)
class ArmyBattlePayload:
    """Army deployment payload shared between campaign and battle."""

    squads: list[tuple[Any, int, dict[str, Any]]] = field(default_factory=list)
    general: Optional[GeneralBattlePayload] = None

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "squads": list(self.squads),
            "general": self.general.to_legacy_dict() if self.general else None,
        }


@dataclass(frozen=True)
class PendingBattle:
    """Campaign-to-main battle handoff contract."""

    player_army: Any
    enemy_army: Any
    terrain_type: Optional[str] = None

    def to_legacy_tuple(self) -> tuple[Any, Any, Optional[str]]:
        return (self.player_army, self.enemy_army, self.terrain_type)


@dataclass(frozen=True)
class SquadBattleStats:
    name: str
    initial: int
    alive: int
    kills: int
    exhaustion: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "initial": self.initial,
            "alive": self.alive,
            "kills": self.kills,
        }
        if self.exhaustion is not None:
            data["exhaustion"] = self.exhaustion
        return data


@dataclass(frozen=True)
class GeneralBattleStats:
    name: str
    type: str
    kills: int
    duels_won: int
    level: int
    alive: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BattleStats:
    result: str
    duration_frames: int
    player_squads: list[SquadBattleStats]
    enemy_squads: list[SquadBattleStats]
    player_generals: list[GeneralBattleStats]
    enemy_generals: list[GeneralBattleStats]
    total_player_kills: int
    total_enemy_kills: int
    loot_gold: int = 0
    mvp: Optional[str] = None
    heroic_victory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "duration_frames": self.duration_frames,
            "player_squads": [sq.to_dict() for sq in self.player_squads],
            "enemy_squads": [sq.to_dict() for sq in self.enemy_squads],
            "player_generals": [g.to_dict() for g in self.player_generals],
            "enemy_generals": [g.to_dict() for g in self.enemy_generals],
            "total_player_kills": self.total_player_kills,
            "total_enemy_kills": self.total_enemy_kills,
            "loot_gold": self.loot_gold,
            "mvp": self.mvp,
            "heroic_victory": self.heroic_victory,
        }
