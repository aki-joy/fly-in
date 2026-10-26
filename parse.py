from models import FlyInMap
import sys

class MapParser:
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
        except ParseError as e:
            print(f"Error: line {e.line_no}: {e}", file=sys.stderr)
            sys.exit(1)




    def parse(self, lines: list[str]) -> FlyInMap:
