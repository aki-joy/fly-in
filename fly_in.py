import sys
from parse import MapParser


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 fly_in.py <map_file>", file=sys.stderr)
        sys.exit(1)

    try:
        fly_map = MapParser().load(sys.argv[1])