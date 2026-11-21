from enum import Enum
from dataclasses import dataclass, field


class ZoneType(Enum):
    """ゾーンの種類。"""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int:
        """このゾーンへ移動するのにかかるターン数を返す。"""
        return 2 if self is ZoneType.RESTRICTED else 1


@dataclass
class Zone:
    """マップ上のゾーン（ハブ）。max_dronesがNoneなら上限なし。"""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int | None = 1


@dataclass
class Connection:
    """2つのゾーンを結ぶ双方向の接続。"""

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1


@dataclass
class FlyInMap:
    """マップファイルをパースした結果。"""

    nb_drones: int
    start: str
    end: str
    zones: dict[str, Zone] = field(default_factory=dict)
    connection: list[Connection] = field(default_factory=list)
