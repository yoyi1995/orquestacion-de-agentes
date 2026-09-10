import argparse
import sys

from factory.workspace import new_project


def main(argv=None):
    parser = argparse.ArgumentParser(description="Crea una carpeta de producto y su estado inicial")
    parser.add_argument("name")
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        project, state = new_project(args.name, args.request)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Proyecto: {project}\nEstado: {state / 'state.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
