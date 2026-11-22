from error import NoPathError
from flow import FlowNetwork
from graph import Graph
from models import ZoneType


Timeline = list[str]

_WAIT_COST = 1
_PRIORITY_MOVE_COST = 2
_NORMAL_MOVE_COST = 3
_RESTRICTED_MOVE_COST = 6


class TimeExpandedNetwork:
    """各ノードが（ゾーン, ターン）の状態を表すフローネットワーク。

    レイヤーtはターンt終了時点の状態を持つ。end以外の各ゾーンには
    "in"ノードと"out"ノードがあり、容量max_dronesの辺で結ばれる。
    これでゾーン内にいられるドローン数を制限する。ターンtの移動は、
    レイヤーt-1の"out"ノードからレイヤーtの"in"ノードへ、容量
    max_link_capacityの辺を通る。restrictedゾーンへの移動は、
    レイヤーtの中継(transit)ノードを経由してレイヤーt+1に到着する。
    中継ノードには待機用の辺がないので、ドローンが接続上に
    留まることはない。
    """

    def __init__(self, graph: Graph, use_costs: bool) -> None:
        """レイヤー0だけを持つネットワークを作る。

        Args:
            graph: ゾーンのグラフ。
            use_costs: 辺にコストを設定するか（最小費用流で使う）。
        """
        self.net = FlowNetwork()
        self.source = self.net.add_node()
        self.sink = self.net.add_node()
        self.turns = 0
        self.positions: dict[int, tuple[str, int]] = {}
        self._graph = graph
        self._use_costs = use_costs
        self._big = graph.nb_drones
        self._zone_in: list[dict[str, int]] = []
        self._zone_out: list[dict[str, int]] = []
        self._pending: list[tuple[int, str]] = []

        self._add_zone_layer(0)
        self.net.add_edge(self.source, self._zone_in[0][graph.start],
                          self._big)

    def add_layer(self) -> None:
        """ネットワークを1ターン分延長する。"""
        t = self.turns + 1
        self._add_zone_layer(t)
        prev_out = self._zone_out[t - 1]
        cur_in = self._zone_in[t]

        for name, node in prev_out.items():
            cost = 0 if name == self._graph.start else _WAIT_COST
            self._edge(node, cur_in[name], self._big, cost)

        for node, dest in self._pending:
            self._edge(node, cur_in[dest], self._big, 0)
        self._pending = []

        for name, node in prev_out.items():
            for edge in self._graph.neighbors(name):
                cap = self._graph.link_capacity[edge.link_id]
                if edge.cost == 1:
                    cost = (_PRIORITY_MOVE_COST if edge.priority
                            else _NORMAL_MOVE_COST)
                    self._edge(node, cur_in[edge.to], cap, cost)
                else:
                    transit = self.net.add_node()
                    label = self._graph.link_names[edge.link_id]
                    self.positions[transit] = (label, t)
                    self._edge(node, transit, cap, _RESTRICTED_MOVE_COST)
                    self._pending.append((transit, edge.to))
        self.turns = t

    def _add_zone_layer(self, t: int) -> None:
        """レイヤーtに、blockedでない全ゾーンのin/outノードを作る。"""
        zone_in: dict[str, int] = {}
        zone_out: dict[str, int] = {}
        for name, zone in self._graph.zones.items():
            if zone.zone_type is ZoneType.BLOCKED:
                continue
            node_in = self.net.add_node()
            self.positions[node_in] = (name, t)
            zone_in[name] = node_in
            if name == self._graph.end:
                self._edge(node_in, self.sink, self._big, 0)
                continue
            cap = self._big
            if zone.max_drones is not None:
                cap = min(cap, zone.max_drones)
            node_out = self.net.add_node()
            self._edge(node_in, node_out, cap, 0)
            zone_out[name] = node_out
        self._zone_in.append(zone_in)
        self._zone_out.append(zone_out)

    def _edge(self, u: int, v: int, cap: int, cost: int) -> None:
        """辺を追加する。コストが無効ならコストを0にする。"""
        self.net.add_edge(u, v, cap, cost if self._use_costs else 0)


class Planner:
    """全ドローンを最少ターンで届けるスケジュールを計算する。"""

    def __init__(self, graph: Graph) -> None:
        """計画に使うグラフを保持する。"""
        self._graph = graph

    def solve(self) -> list[Timeline]:
        """ドローンごとのタイムラインを、出発順に並べて返す。

        Raises:
            NoPathError: endゾーンに到達できない場合。
        """
        lower = self._graph.shortest_turns()
        if lower is None:
            raise NoPathError(
                f"no path from '{self._graph.start}' to '{self._graph.end}'")
        turns = self._min_turns(lower)
        return self._schedule(turns)

    def _min_turns(self, lower: int) -> int:
        """全ドローンが到着できる最小のターン数を求める。

        レイヤーを1つずつ追加し、既存のフローは保持したままにする。
        そのため各ステップでは、追加分の増加パスだけを探せばよい。
        """
        n = self._graph.nb_drones
        # One drone per turn along a shortest path always works.
        upper = lower + n - 1
        ten = TimeExpandedNetwork(self._graph, use_costs=False)
        flow = 0
        while flow < n:
            if ten.turns >= upper:
                raise RuntimeError("turn upper bound exceeded")
            ten.add_layer()
            if ten.turns >= lower:
                flow += ten.net.max_flow(ten.source, ten.sink, n - flow)
        return ten.turns

    def _schedule(self, turns: int) -> list[Timeline]:
        """ターン数turnsで最小費用流を求め、タイムラインに分解する。"""
        ten = TimeExpandedNetwork(self._graph, use_costs=True)
        for _ in range(turns):
            ten.add_layer()
        n = self._graph.nb_drones
        if ten.net.min_cost_flow(ten.source, ten.sink, n) != n:
            raise RuntimeError("min-cost flow did not reach every drone")
        timelines = [self._extract(ten) for _ in range(n)]
        timelines.sort(key=self._departure)
        return timelines

    @staticmethod
    def _extract(ten: TimeExpandedNetwork) -> Timeline:
        """sourceからsinkまでフローを1単位たどり、それを消費する。"""
        net = ten.net
        timeline: Timeline = []
        u = ten.source
        while u != ten.sink:
            for e in net.out_edges(u):
                if net.flow(e) > 0:
                    net.add_flow_back(e)
                    u = net.head(e)
                    break
            else:
                raise RuntimeError("broken flow while extracting a path")
            if u in ten.positions:
                timeline.append(ten.positions[u][0])
        return timeline

    @staticmethod
    def _departure(timeline: Timeline) -> int:
        """ドローンが最初にstartを離れるターンを返す。"""
        for t in range(1, len(timeline)):
            if timeline[t] != timeline[0]:
                return t
        return len(timeline)
