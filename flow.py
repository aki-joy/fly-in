import heapq
from collections import deque


class FlowNetwork:
    """Directed flow network with residual edges.

    Every edge added with add_edge() gets a paired reverse edge. Edge e
    and its reverse are stored at indices e and e ^ 1, so the flow on a
    forward edge is the remaining capacity of its reverse edge.
    """

    _INF = float("inf")

    def __init__(self) -> None:
        """Create an empty network."""
        self._head: list[list[int]] = []
        self._to: list[int] = []
        self._cap: list[int] = []
        self._cost: list[int] = []

    def add_node(self) -> int:
        """Add a node and return its id."""
        self._head.append([])
        return len(self._head) - 1

    def add_edge(self, u: int, v: int, cap: int, cost: int = 0) -> int:
        """Add an edge u -> v and return its id.

        Args:
            u: Tail node id.
            v: Head node id.
            cap: Capacity (must be >= 0).
            cost: Cost per unit of flow (must be >= 0).
        """
        e = len(self._to)
        self._to += [v, u]
        self._cap += [cap, 0]
        self._cost += [cost, -cost]
        self._head[u].append(e)
        self._head[v].append(e + 1)
        return e

    def out_edges(self, u: int) -> list[int]:
        """Return the ids of forward edges leaving u."""
        return [e for e in self._head[u] if e % 2 == 0]

    def head(self, e: int) -> int:
        """Return the node edge e points to."""
        return self._to[e]

    def flow(self, e: int) -> int:
        """Return the flow currently on forward edge e."""
        return self._cap[e ^ 1]

    def add_flow_back(self, e: int) -> None:
        """Remove one unit of flow from forward edge e."""
        self._cap[e] += 1
        self._cap[e ^ 1] -= 1

    def max_flow(self, s: int, t: int, limit: int) -> int:
        """Push up to limit units from s to t (Edmonds-Karp).

        Flow already in the network is kept, so this can be called again
        after adding nodes and edges.

        Returns:
            The amount of flow pushed by this call.
        """
        total = 0
        while total < limit:
            prev = self._bfs(s, t)
            if prev is None:
                break
            total += self._push(s, t, prev, limit - total)
        return total

    def min_cost_flow(self, s: int, t: int, limit: int) -> int:
        """Push up to limit units from s to t at minimum total cost.

        Uses successive shortest paths with Dijkstra and node potentials.
        Requires an empty network whose edge costs are all >= 0.

        Returns:
            The amount of flow pushed.
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
        """Find a shortest augmenting path; return predecessor edges."""
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
        """Push flow along the path recorded in prev; return the amount."""
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
