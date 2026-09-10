"""Small workspace helpers; orchestration remains in the Codex session."""
from datetime import datetime, timezone
from pathlib import Path
import re

from factory.tools import resolve_path

ROOT = Path(__file__).resolve().parents[1]
RESERVED = {"con", "prn", "aux", "nul"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


def validate_project_name(name: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", name) or name in RESERVED:
        raise ValueError("Nombre inválido: usa 1–80 letras minúsculas ASCII, números, _ o -; sin nombres reservados Windows")
    return name


def project_paths(name: str, workspace_root: Path = ROOT) -> tuple[Path, Path]:
    validate_project_name(name)
    root = Path(workspace_root).resolve()
    projects = resolve_path(root, "proyectos")
    states = resolve_path(root, "project-state")
    project = resolve_path(projects, name)
    state = resolve_path(states, name)
    if project == projects or state == states or projects == root or states == root:
        raise ValueError("La ruta debe identificar un proyecto independiente")
    return project, state


def new_project(name: str, request: str, workspace_root: Path = ROOT) -> tuple[Path, Path]:
    if not request.strip():
        raise ValueError("El requerimiento no puede estar vacío")
    project, state = project_paths(name, workspace_root)
    if project.exists() or state.exists():
        raise ValueError("Ya existe el proyecto o su estado; no se sobrescribirá")
    template = (Path(workspace_root) / "factory" / "project-template.md").read_text(encoding="utf-8")
    values = {"PROJECT_NAME": name, "REQUEST": request.strip(),
              "CREATED_AT": datetime.now(timezone.utc).isoformat()}
    content = re.sub(r"\{\{(PROJECT_NAME|REQUEST|CREATED_AT)\}\}",
                     lambda match: values[match.group(1)], template)
    project.mkdir(parents=True, exist_ok=False)
    state.mkdir(parents=True, exist_ok=False)
    (state / "state.md").write_text(content, encoding="utf-8")
    return project, state
