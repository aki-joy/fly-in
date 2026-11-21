import heapq
from collections import deque


class FlowNetwork:
    """残余辺を持つ有向フローネットワーク。

    add_edge()で追加した辺には、対になる逆辺が作られる。辺eと
    その逆辺はインデックスeとe ^ 1に格納されるので、順方向の辺の
    フロー量は、逆辺の残り容量と等しい。
    """

    _INF = float("inf")

    def __init__(self) -> None:
        """空のネットワークを作る。"""
        self._head: list[list[int]] = []
        self._to: list[int] = []
        self._cap: list[int] = []
        self._cost: list[int] = []

    def add_node(self) -> int:
        """ノードを追加してそのidを返す。"""
        self._head.append([])
        return len(self._head) - 1

    def add_edge(self, u: int, v: int, cap: int, cost: int = 0) -> int:
        """辺u -> vを追加してそのidを返す。

        Args:
            u: 始点ノードのid。
            v: 終点ノードのid。
            cap: 容量（0以上）。
            cost: フロー1単位あたりのコスト（0以上）。
        """
        e = len(self._to)
        self._to += [v, u]
        self._cap += [cap, 0]
        self._cost += [cost, -cost]
        self._head[u].append(e)
        self._head[v].append(e + 1)
        return e

    def out_edges(self, u: int) -> list[int]:
        """uから出ていく順方向の辺のidを返す。"""
        return [e for e in self._head[u] if e % 2 == 0]

    def head(self, e: int) -> int:
        """辺eが指すノードを返す。"""
        return self._to[e]

    def flow(self, e: int) -> int:
        """順方向の辺eに今流れているフロー量を返す。"""
        return self._cap[e ^ 1]

    def add_flow_back(self, e: int) -> None:
        """順方向の辺eからフローを1単位取り除く。"""
        self._cap[e] += 1
        self._cap[e ^ 1] -= 1

    def max_flow(self, s: int, t: int, limit: int) -> int:
        """sからtへ最大limit単位のフローを流す（Edmonds-Karp法）。

        ネットワーク内の既存のフローは保持されるので、ノードや辺を
        追加したあとに再度呼び出せる。

        Returns:
            この呼び出しで流したフロー量。
        """
        total = 0
        while total < limit:
            prev = self._bfs(s, t)
            if prev is None:
                break
            total += self._push(s, t, prev, limit - total)
        return total

    def min_cost_flow(self, s: int, t: int, limit: int) -> int:
        """sからtへ最大limit単位のフローを、総コスト最小で流す。

        ダイクストラ法とポテンシャルを使った逐次最短路法で求める。
        フローが空で、全辺のコストが0以上のネットワークが前提。

        Returns:
            流したフロー量。
        """
        n = len(self._head)
        potential = [0] * n
        total = 0
        while total < limit:
            dist = [self._INF] * n
            prev = [-1] * n
            dist[s] = 0
            heap: list[tuple[float, int]] = [(0, s)]
            while heap:
                d, u = heapq.heappop(heap)
                if d > dist[u]:
                    continue
                for e in self._head[u]:
                    if self._cap[e] == 0:
                        continue
                    v = self._to[e]
                    nd = d + self._cost[e] + potential[u] - potential[v]
                    if nd < dist[v]:
                        dist[v] = nd
                        prev[v] = e
                        heapq.heappush(heap, (nd, v))
            if dist[t] == self._INF:
                break
            for v in range(n):
                if dist[v] != self._INF:
                    potential[v] += int(dist[v])
            total += self._push(s, t, prev, limit - total)
        return total

    def _bfs(self, s: int, t: int) -> list[int] | None:
        """最短の増加パスを探し、各ノードへの直前の辺のリストを返す。"""
        prev = [-1] * len(self._head)
        seen = [False] * len(self._head)
        seen[s] = True
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for e in self._head[u]:
                v = self._to[e]
                if self._cap[e] > 0 and not seen[v]:
                    seen[v] = True
                    prev[v] = e
                    if v == t:
                        return prev
                    queue.append(v)
        return None

    def _push(self, s: int, t: int, prev: list[int], limit: int) -> int:
        """prevに記録されたパスに沿ってフローを流し、その量を返す。"""
        amount = limit
        v = t
        while v != s:
            e = prev[v]
            amount = min(amount, self._cap[e])
            v = self._to[e ^ 1]
        v = t
        while v != s:
            e = prev[v]
            self._cap[e] -= amount
            self._cap[e ^ 1] += amount
            v = self._to[e ^ 1]
        return amount
