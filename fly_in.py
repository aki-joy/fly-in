import sys
from parse import MapParser
from error import FlyInError
from graph import Graph
from planner import Planner
from simulation import Simulation


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 fly_in.py <map_file>", file=sys.stderr)
        sys.exit(1)

    try:
        fly_map = MapParser().load(sys.argv[1])
        graph = Graph(fly_map)
        simulation = Simulation(graph, Planner(graph).solve())
        for line in simulation.lines():
            print(line)
    except FlyInError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Internal error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
