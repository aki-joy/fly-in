import argparse
import os
import sys
from parse import MapParser
from error import FlyInError
from graph import Graph
from planner import Planner
from simulation import Simulation


def main() -> None:
    """マップを読み、各ターンの移動を出力する。--gui なら画面にも表示する。"""
    parser = argparse.ArgumentParser(description="Fly-in drone routing")
    parser.add_argument("map_file", help="path to the map file")
    parser.add_argument("--gui", action="store_true",
                        help="show the simulation in a pygame window")
    args = parser.parse_args()

    try:
        fly_map = MapParser().load(args.map_file)
        graph = Graph(fly_map)
        timelines = Planner(graph).solve()
        for line in Simulation(timelines).lines():
            print(line)
        if args.gui:
            sys.stdout.flush()
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            from visualizer import Visualizer
            Visualizer(graph, timelines).run()
    except FlyInError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ModuleNotFoundError as e:
        print(f"Error: {e.name} is not installed (run 'make install')",
              file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Internal error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
