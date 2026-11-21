from planner import Timeline


class Simulation:
    """各ドローンのタイムラインを、1ターン1行の出力に変換する。"""

    def __init__(self, timelines: list[Timeline]) -> None:
        """ドローンごと（D1, D2, ...）のタイムラインを保持する。"""
        self._timelines = timelines
        self.turns = max((len(tl) - 1 for tl in timelines), default=0)

    def lines(self) -> list[str]:
        """1ターン1行で、そのターンに動いたドローンを並べた行のリストを返す。"""
        result: list[str] = []
        for t in range(1, self.turns + 1):
            moves = [
                f"D{i}-{tl[t]}"
                for i, tl in enumerate(self._timelines, 1)
                if t < len(tl) and tl[t] != tl[t - 1]
            ]
            result.append(" ".join(moves))
        return result
