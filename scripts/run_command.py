import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
import sys
from uuid import uuid4

from factory.tools import run_command, resolve_path
from factory.workspace import project_paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ejecuta un comando finito con timeout y registro JSON")
    parser.add_argument("--project", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--command", required=True)
    args = parser.parse_args(argv)
    try:
        project, state = project_paths(args.project)
        if not project.is_dir():
            raise ValueError("El proyecto no existe")
        if not args.command.strip():
            raise ValueError("El comando no puede estar vacío")
        if not 1 <= args.timeout <= 600:
            raise ValueError("timeout debe ser un entero entre 1 y 600 segundos")
        runs = resolve_path(state, "runs")
        runs.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc)
        try:
            with redirect_stdout(sys.stderr):
                result = run_command(project, args.command, args.timeout)
        except (ValueError, OSError) as exc:
            result = {"command": args.command, "timeout": args.timeout,
                      "returncode": None, "timed_out": False, "error": str(exc)}
        result.update(project=args.project, cwd=str(project), timestamp=timestamp.isoformat())
        record = runs / f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}.json"
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        with record.open("x", encoding="utf-8") as stream:
            stream.write(serialized + "\n")
        print(serialized)
        if result.get("timed_out"):
            return 124
        if result.get("error") or result.get("cleanup_error") or result.get("returncode") != 0:
            return 1
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
