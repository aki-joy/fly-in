from enum import Enum
from dataclasses import dataclass, field


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int:

        return 2 if self is ZoneType.RESTRICTED else 1


@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int | None = 1


@dataclass
class Connection:
    zone_a: str
    zone_b: str
    max_link_capacity: int = 1


@dataclass
class FlyInMap:
    nb_drones: int
    start: str
    end: str
    zones: dict[str, Zone] = field(default_factory=dict)
    connection: list[Connection] = field(default_factory=list)
