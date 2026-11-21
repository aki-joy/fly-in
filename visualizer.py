import pygame

from error import VisualizerError
from graph import Graph
from planner import Timeline

Point = tuple[float, float]
Color = tuple[int, int, int]

_BACKGROUND: Color = (24, 26, 32)
_TEXT: Color = (230, 230, 235)
_LINK: Color = (110, 115, 130)
_DEFAULT_ZONE: Color = (120, 120, 130)
_DRONE: Color = (255, 150, 40)


class Visualizer:
    """ネットワークと各ターンのドローンの位置をpygameで表示する。"""

    _SIZE = (1280, 720)
    _MARGIN = 60
    _RADIUS = 14
    _TURN_MS = 700

    def __init__(self, graph: Graph, timelines: list[Timeline]) -> None:
        """グラフと、ドローンごとのタイムラインを保持する。"""
        self._graph = graph
        self._timelines = timelines
        self._turns = max((len(tl) - 1 for tl in timelines), default=0)
        self._centers: dict[str, Point] = {}

    def run(self) -> None:
        """ウィンドウを開き、1ターンずつ自動で進めて表示する。

        ウィンドウを閉じるかESCで終了する。

        Raises:
            VisualizerError: ウィンドウを開けない場合。
        """
        try:
            pygame.init()
            screen = pygame.display.set_mode(self._SIZE)
        except pygame.error as e:
            pygame.quit()
            raise VisualizerError(f"cannot open window: {e}") from e
        try:
            pygame.display.set_caption("Fly-in")
            self._centers = self._layout()
            font = pygame.font.Font(None, 18)
            clock = pygame.time.Clock()
            turn, elapsed = 0, 0
            while not self._quit_requested():
                elapsed += clock.tick(30)
                if elapsed >= self._TURN_MS and turn < self._turns:
                    turn, elapsed = turn + 1, 0
                self._draw(screen, font, turn)
                pygame.display.flip()
        finally:
            pygame.quit()

    @staticmethod
    def _quit_requested() -> bool:
        """ウィンドウが閉じられたかESCが押されたらTrueを返す。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
        return False

    def _layout(self) -> dict[str, Point]:
        """各ゾーンの画面座標を、マップ全体が画面に収まるように求める。"""
        zones = self._graph.zones.values()
        min_x = min(z.x for z in zones)
        max_y = max(z.y for z in zones)
        span_x = max(z.x for z in zones) - min_x
        span_y = max_y - min(z.y for z in zones)
        width = self._SIZE[0] - 2 * self._MARGIN
        height = self._SIZE[1] - 2 * self._MARGIN
        scale = min(width / max(span_x, 1), height / max(span_y, 1))
        left = (self._SIZE[0] - span_x * scale) / 2
        top = (self._SIZE[1] - span_y * scale) / 2
        # マップのyは上向き、画面のyは下向きなので反転する。
        return {z.name: (left + (z.x - min_x) * scale,
                         top + (max_y - z.y) * scale) for z in zones}

    def _draw(self, screen: pygame.Surface, font: pygame.font.Font,
              turn: int) -> None:
        """ターンturnの状態（接続・ゾーン・ドローン）を描く。"""
        screen.fill(_BACKGROUND)
        for label in self._graph.link_names:
            a, b = label.split("-")
            pygame.draw.line(screen, _LINK, self._centers[a],
                             self._centers[b], 2)
        for name, zone in self._graph.zones.items():
            center = self._centers[name]
            pygame.draw.circle(screen, self._zone_color(zone.color), center,
                               self._RADIUS)
            text = font.render(name, True, _TEXT)
            screen.blit(text, text.get_rect(
                midtop=(center[0], center[1] + self._RADIUS + 2)))

        # 同じ位置にいるドローンは1つの印にまとめ、機数を書く。
        counts: dict[Point, int] = {}
        # endに着いたドローンはendに残して、配達済みの機数として数える。
        for tl in self._timelines:
            pos = self._position(tl, min(turn, len(tl) - 1))
            counts[pos] = counts.get(pos, 0) + 1
        for pos, n in counts.items():
            pygame.draw.circle(screen, _DRONE, pos, self._RADIUS * 0.7)
            text = font.render(str(n), True, _BACKGROUND)
            screen.blit(text, text.get_rect(center=pos))

        status = font.render(f"Turn {turn} / {self._turns}", True, _TEXT)
        screen.blit(status, (16, 16))

    def _position(self, tl: Timeline, t: int) -> Point:
        """ターンtのドローンの画面座標を返す。

        restrictedゾーンへ飛行中なら、出発ゾーンと到着ゾーンの中間。
        """
        if tl[t] in self._centers:
            return self._centers[tl[t]]
        (x1, y1), (x2, y2) = self._centers[tl[t - 1]], self._centers[tl[t + 1]]
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @staticmethod
    def _zone_color(color: str | None) -> Color:
        """マップのcolorをRGBにする。指定なし・知らない色名なら既定色。"""
        if color is None:
            return _DEFAULT_ZONE
        try:
            c = pygame.Color(color)
        except ValueError:
            return _DEFAULT_ZONE
        return (c.r, c.g, c.b)
