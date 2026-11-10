from graph import Edge, Graph
from planner import Timeline


class Simulation:
    """Turn drone timelines into output lines and check them."""

    def __init__(self, graph: Graph, timelines: list[Timeline]) -> None:
        """Store the graph and one timeline per drone (D1, D2, ...)."""
        self._graph = graph
        self._timelines = timelines
        self.turns = max((len(tl) - 1 for tl in timelines), default=0)

    def lines(self) -> list[str]:
        """Return one line per turn listing the drones that moved."""
        result: list[str] = []
        for t in range(1, self.turns + 1):
            moves = [
                f"D{i}-{tl[t]}"
                for i, tl in enumerate(self._timelines, 1)
                if t < len(tl) and tl[t] != tl[t - 1]
            ]
            result.append(" ".join(moves))
        return result

    def validate(self) -> list[str]:
        """Check every movement, occupancy and capacity rule.

        Returns:
            A description of each violation (empty if the schedule is
            valid).
        """
        g = self._graph
        errors: list[str] = []
        for i, tl in enumerate(self._timelines, 1):
            if tl[0] != g.start:
                errors.append(f"D{i} does not start at {g.start}")
            if tl[-1] != g.end or g.end in tl[:-1]:
                errors.append(f"D{i} does not end exactly at {g.end}")

        for t in range(1, self.turns + 1):
            occupancy: dict[str, int] = {}
            link_use: dict[int, int] = {}
            for i, tl in enumerate(self._timelines, 1):
                if t >= len(tl):
                    continue
                error = self._check_step(tl, t, link_use)
                if error:
                    errors.append(f"turn {t}: D{i} {error}")
                if tl[t] in g.zones:
                    occupancy[tl[t]] = occupancy.get(tl[t], 0) + 1

            for name, count in occupancy.items():
                limit = g.zones[name].max_drones
                if limit is not None and count > limit:
                    errors.append(f"turn {t}: {name} holds {count} drones")
            for link_id, count in link_use.items():
                if count > g.link_capacity[link_id]:
                    errors.append(f"turn {t}: {g.link_names[link_id]} "
                                  f"used by {count} drones")
        return errors

    def _check_step(self, tl: Timeline, t: int,
                    link_use: dict[int, int]) -> str | None:
        """Check the move from tl[t-1] to tl[t] and count link usage.

        Returns:
            A description of the problem, or None if the move is valid.
        """
        zones = self._graph.zones
        prev, cur = tl[t - 1], tl[t]
        if prev not in zones:
            # On a connection: the arrival was checked at departure.
            return None if cur in zones else f"stays on {prev}"
        if prev == cur:
            return None

        if cur in zones:
            edge = self._edge_to(prev, cur)
            if edge is None or edge.cost != 1:
                return f"cannot move {prev} -> {cur}"
        else:
            edge = self._edge_via(prev, cur)
            if edge is None or edge.cost != 2:
                return f"cannot fly {prev} -> {cur}"
            if t + 1 >= len(tl) or tl[t + 1] != edge.to:
                return f"does not land on {edge.to} after {cur}"
        link_use[edge.link_id] = link_use.get(edge.link_id, 0) + 1
        return None

    def _edge_to(self, name: str, dest: str) -> Edge | None:
        """Return the edge from zone name to zone dest, if any."""
        for edge in self._graph.neighbors(name):
            if edge.to == dest:
                return edge
        return None

    def _edge_via(self, name: str, label: str) -> Edge | None:
        """Return the edge leaving name through the connection label."""
        for edge in self._graph.neighbors(name):
            if self._graph.link_names[edge.link_id] == label:
                return edge
        return None
