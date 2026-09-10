from __future__ import annotations

import locale
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path


def resolve_path(project_root: Path, relative_path: str) -> Path:
    root = project_root.resolve()
    target = (root / relative_path).resolve()

    if target != root and root not in target.parents:
        raise ValueError("Ruta fuera del proyecto no permitida")

    return target


def read_file(project_root: Path, path: str) -> str:
    target = resolve_path(project_root, path)

    if not target.exists():
        raise FileNotFoundError(f"No existe: {path}")

    if not target.is_file():
        raise ValueError(f"No es un archivo: {path}")

    return target.read_text(encoding="utf-8")


def write_file(
    project_root: Path,
    path: str,
    content: str,
) -> str:
    target = resolve_path(project_root, path)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return f"Archivo creado/modificado: {path}"


def list_directory(
    project_root: Path,
    path: str = ".",
) -> list[str]:
    target = resolve_path(project_root, path)

    if not target.exists():
        raise FileNotFoundError(f"No existe: {path}")

    results = []

    for item in sorted(target.iterdir()):
        prefix = "[DIR]" if item.is_dir() else "[FILE]"
        results.append(f"{prefix} {item.name}")

    return results


MIN_COMMAND_TIMEOUT = 1
MAX_COMMAND_TIMEOUT = 600
CLEANUP_TIMEOUT = 5
OUTPUT_LIMIT = 12000


def _terminate_process_tree(process: subprocess.Popen) -> str | None:
    """Terminate descendants before the shell; every cleanup wait is bounded."""
    errors = []
    if os.name == "nt":
        killer = None
        try:
            killer = subprocess.Popen(
                [os.path.join(os.environ["SystemRoot"], "System32", "taskkill.exe"),
                 "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if killer.wait(timeout=CLEANUP_TIMEOUT) != 0:
                errors.append("taskkill no pudo confirmar la terminación del árbol")
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Error terminando el árbol: {exc}")
        finally:
            if killer is not None and killer.poll() is None:
                try:
                    killer.kill()
                    killer.wait(timeout=CLEANUP_TIMEOUT)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(f"Error terminando taskkill: {exc}")
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            errors.append(f"Error terminando el grupo: {exc}")

    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=CLEANUP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"Error terminando el proceso: {exc}")
    return "; ".join(errors) or None


def _read_output_tail(output) -> str:
    # Regular files avoid waiting for EOF on pipes inherited by child processes.
    size = output.seek(0, os.SEEK_END)
    output.seek(max(0, size - OUTPUT_LIMIT))
    return output.read(OUTPUT_LIMIT).decode(
        locale.getpreferredencoding(False), errors="replace"
    )


def run_command(
    project_root: Path,
    command: str,
    timeout: int = 120,
) -> dict:
    if type(timeout) is not int or not MIN_COMMAND_TIMEOUT <= timeout <= MAX_COMMAND_TIMEOUT:
        raise ValueError("timeout debe ser un entero entre 1 y 600 segundos")

    print(f"[run_command] Comando: {command}", flush=True)
    print(f"[run_command] Timeout: {timeout} s", flush=True)
    started = time.monotonic()
    result = {
        "command": command,
        "timeout": timeout,
        "returncode": None,
        "timed_out": False,
    }

    # Do not use PIPE/communicate or a Popen context manager: their cleanup can
    # wait indefinitely on Windows when descendants retain inherited handles.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=project_root,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result["timed_out"] = True
                result["error"] = f"El comando excedió el timeout de {timeout} segundos"
                cleanup_error = _terminate_process_tree(process)
                if cleanup_error:
                    result["cleanup_error"] = cleanup_error
            result["returncode"] = process.poll()
        except OSError as exc:
            result["error"] = str(exc)

        result["stdout"] = _read_output_tail(stdout)
        result["stderr"] = _read_output_tail(stderr)

    result["duration_seconds"] = round(time.monotonic() - started, 3)
    print(f"[run_command] Código de salida: {result['returncode']}", flush=True)
    print(f"[run_command] Duración: {result['duration_seconds']} s", flush=True)
    print(f"[run_command] stdout (últimos {OUTPUT_LIMIT} bytes):\n{result['stdout']}", flush=True)
    print(f"[run_command] stderr (últimos {OUTPUT_LIMIT} bytes):\n{result['stderr']}", flush=True)
    if result.get("error"):
        print(f"[run_command] Error: {result['error']}", flush=True)
    if result.get("cleanup_error"):
        print(f"[run_command] Limpieza: {result['cleanup_error']}", flush=True)
    return result
