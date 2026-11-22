import heapq
from dataclasses import dataclass

from models import FlyInMap, Zone, ZoneType


@dataclass(frozen=True)
class Edge:
    """隣接ゾーンへの移動1つ。costはかかるターン数。"""

    to: str
    cost: int
    link_id: int
    priority: bool


class Graph:
    """ゾーンの隣接リストと、接続ごとの容量を持つグラフ。"""

    def __init__(self, fly_map: FlyInMap) -> None:
        """マップから隣接リストを作る。blockedゾーンへの辺は張らない。"""
        self.start: str = fly_map.start
        self.end: str = fly_map.end
        self.nb_drones: int = fly_map.nb_drones
        self.zones: dict[str, Zone] = fly_map.zones
        self.adjacency: dict[str, list[Edge]] = {
            name: [] for name in fly_map.zones
        }
        self.link_capacity: list[int] = []
        self.link_names: list[str] = []

        for link_id, conn in enumerate(fly_map.connection):
            self.link_capacity.append(conn.max_link_capacity)
            self.link_names.append(f"{conn.zone_a}-{conn.zone_b}")
            a = self.zones[conn.zone_a]
            b = self.zones[conn.zone_b]
            if ZoneType.BLOCKED in (a.zone_type, b.zone_type):
                continue
            self.adjacency[a.name].append(self._make_edge(b, link_id))
            self.adjacency[b.name].append(self._make_edge(a, link_id))

    def neighbors(self, name: str) -> list[Edge]:
        """ゾーンnameから出ていく辺のリストを返す。"""
        return self.adjacency[name]

    def shortest_turns(self) -> int | None:
        """1機のドローンがendに着くまでの最少ターン数を返す。

        辺のコスト（restricted = 2ターン）を使ったダイクストラ法で求める。

        Returns:
            ターン数。endに到達できなければNone。
        """
        best_turns: dict[str, int] = {self.start: 0}
        heap: list[tuple[int, str]] = [(0, self.start)]
        while heap:
            turns, zone = heapq.heappop(heap)
            if zone == self.end:
                return turns
            if turns > best_turns[zone]:
                continue
            for edge in self.adjacency[zone]:
                next_turns = turns + edge.cost
                if next_turns < best_turns.get(edge.to, next_turns + 1):
                    best_turns[edge.to] = next_turns
                    heapq.heappush(heap, (next_turns, edge.to))
        return None

    @staticmethod
    def _make_edge(dest: Zone, link_id: int) -> Edge:
        """ゾーンdestへ向かう辺を、destの種類に応じて作る。"""
        return Edge(
            to=dest.name,
            cost=dest.zone_type.cost,
            link_id=link_id,
            priority=dest.zone_type is ZoneType.PRIORITY,
        )
