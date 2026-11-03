from models import FlyInMap, Zone, Connection, ZoneType
from error import MapLoadError, ParseError
import re


class MapParser:
    def __init__(self) -> None:
        self._nb_drones: int | None = None
        self._start: str | None = None
        self._end: str | None = None
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._edge_keys: set[frozenset[str]] = set()

    def load(self, path: str) -> FlyInMap:
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError as e:
            raise MapLoadError(f"file not found: {path}") from e
        except IsADirectoryError as e:
            raise MapLoadError(f"is a directory: {path}") from e
        except OSError as e:
            raise MapLoadError(f"cannot read {path}: {e.strerror}") from e
        except UnicodeDecodeError as e:
            raise MapLoadError(f"{path} is not a valid UTF-8 text file") from e
        return self.parse(lines)

    def parse(self, lines: list[str]) -> FlyInMap:

        for line_no, raw in enumerate(lines, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            prefix, sep, rest = line.partition(":")
            if not sep:
                raise ParseError(line_no, f"missing ':' in '{line}'")
            prefix = prefix.strip()
            rest = rest.strip()

            if prefix == "nb_drones":
                if self._nb_drones is not None:
                    raise ParseError(line_no, "nb_drones defined more than once")
                self._parse_nb_drones(line_no, rest)
            elif self._nb_drones is None:
                raise ParseError(line_no, "first line must be 'nb_drones: <number>'")
            elif prefix in ("start_hub", "end_hub", "hub"):
                self._parse_hub(line_no, prefix, rest)
            elif prefix == "connection":
                self._parse_connection(line_no, rest)
            else:
                raise ParseError(line_no, f"unknown directive: '{prefix}'")
        return self._build()

    def _parse_nb_drones(self, line_no: int, text: str) -> None:
        """Parse 'nb_drones: <positive_integer>'."""
        n = self._parse_int(line_no, "nb_drones", text)
        if n <= 0:
            raise ParseError(line_no, f"nb_drones must be positive: '{text}'")
        self._nb_drones = n

    def _parse_hub(self, line_no: int, prefix: str, text: str) -> None:
        body, meta = self._split_metadata(line_no, text)
        parts = body.split()
        if len(parts) != 3:
            raise ParseError(line_no, "expected '<name> <x> <y> [metadata]'")
        name, x_str, y_str = parts

        if "-" in name:
            raise ParseError(line_no, f"zone name must not contain '-': '{name}'")
        if name in self._zones:
            raise ParseError(line_no, f"duplicate zone name: '{name}'")
        x = self._parse_int(line_no, "x", x_str)
        y = self._parse_int(line_no, "y", y_str)

        unknown = meta.keys() - {"zone", "color", "max_drones"}
        if unknown:
            raise ParseError(line_no, f"unknown metadata: {sorted(unknown)}")

        try:
            zone_type = ZoneType(meta.get("zone", "normal"))
        except ValueError:
            raise ParseError(line_no, f"invalid zone type: '{meta['zone']}'") from None

        max_drones: int | None = 1
        if prefix == "hub":
            if "max_drones" in meta:
                max_drones = self._parse_int(line_no, "max_drones", meta["max_drones"])
                if max_drones <= 0:
                    raise ParseError(line_no, "max_drones must be positive")
        else:
            max_drones = None
            if prefix == "start_hub":
                if self._start is not None:
                    raise ParseError(line_no, "start_hub defined more than once")
                self._start = name
            else:
                if self._end is not None:
                    raise ParseError(line_no, "end_hub defined more than once")
                self._end = name

        self._zones[name] = Zone(name, x, y, zone_type, meta.get("color"), max_drones)

    def _parse_connection(self, line_no: int, text: str) -> None:

        body, meta = self._split_metadata(line_no, text)
        parts = body.split()
        if len(parts) != 1:
            raise ParseError(line_no, "expected '<zone1>-<zone2> [metadata]'")
        names = parts[0].split("-")
        if len(names) != 2 or not names[0] or not names[1]:
            raise ParseError(line_no, f"invalid connection: '{parts[0]}'")
        a, b = names

        for name in (a, b):
            if name not in self._zones:
                raise ParseError(line_no, f"undefined zone: '{name}'")
        if a == b:
            raise ParseError(line_no, f"zone connected to itself: '{a}'")
        key = frozenset((a, b))
        if key in self._edge_keys:
            raise ParseError(line_no, f"duplicate connection: '{a}-{b}'")

        unknown = meta.keys() - {"max_link_capacity"}
        if unknown:
            raise ParseError(line_no, f"unknown metadata: {sorted(unknown)}")
        capacity = 1
        if "max_link_capacity" in meta:
            capacity = self._parse_int(
                line_no, "max_link_capacity", meta["max_link_capacity"]
            )
            if capacity <= 0:
                raise ParseError(line_no, "max_link_capacity must be positive")

        self._edge_keys.add(key)
        self._connections.append(Connection(a, b, capacity))

    def _split_metadata(self, line_no: int, text: str) -> tuple[str, dict[str, str]]:

        body, sep, inner = text.partition("[")
        if not sep:
            if "]" in text:
                raise ParseError(line_no, "unexpected ']'")
            return text, {}
        if not inner.endswith("]") or "[" in inner or "]" in inner[:-1]:
            raise ParseError(line_no, "malformed metadata block")
        meta: dict[str, str] = {}
        for item in inner[:-1].split():
            key, eq, value = item.partition("=")
            if not eq or not key or not value:
                raise ParseError(line_no, f"invalid metadata entry: '{item}'")
            if key in meta:
                raise ParseError(line_no, f"duplicate metadata key: '{key}'")
            meta[key] = value
        return body, meta

    def _parse_int(self, line_no: int, field: str, text: str) -> int:
        _INT_RE = re.compile(r"-?[0-9]+")
        if not _INT_RE.fullmatch(text):
            raise ParseError(line_no, f"{field} must be an integer: '{text}'")
        return int(text)

    def _build(self) -> FlyInMap:
        """Check whole-file constraints and build the FlyInMap."""
        if self._nb_drones is None:
            raise ParseError(None, "missing 'nb_drones' line")
        if self._start is None:
            raise ParseError(None, "missing start_hub")
        if self._end is None:
            raise ParseError(None, "missing end_hub")
        return FlyInMap(
            self._nb_drones, self._start, self._end, self._zones, self._connections
        )
