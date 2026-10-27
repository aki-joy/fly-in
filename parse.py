from models import FlyInMap, Zone, Connection
from dataclasses import field
import sys

class MapParser:
    def __init__(self) -> None:
        self._nb_drones: int
        self._start: str
        self._end: str
        self._zones: dict[str, Zone] = {}
        self._connection: list[Connection] = []

    def load(self, path: str) -> FlyInMap:
        try:
            with open(path, encoding="utf-8") as f:
                return self.parse(f.readlines())
        except FileNotFoundError:
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        except IsADirectoryError:
            print(f"Error: is a directory: {path}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error: cannot read {path}: {e.strerror}", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Error: {path} is not a valid UTF-8 text file", file=sys.stderr)
            sys.exit(1)



    def parse(self, lines: list[str]) -> FlyInMap:
        for line_no, raw in enumerate(lines, 1):
            line = raw.split("#")[0].strip()
            if not line:
                continue
            prefix, sep, rest = line.partition(":")
            if not sep:
                raise ParseError
            prefix = prefix.strip()
            rest = rest.strip()

            if prefix == "nb_drones":
                self._parse_nb_drones(line_no, rest)
            elif prefix in ("start_hub", "end_hub", "hub"):
                self._parse_hub(line_no)




    def _parse_nb_drones(self, line_no: int, text: str) -> None:
        try:
            self.nb_drones = int(text)
        except ValueError:
            raise(f"Invalid syntax: {line_no} line:{text} is not integer")


    def _parse_hub(self, line_no: int, text: str) -> None:
        try:
            text
            

    