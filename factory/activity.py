"""Operational events only; no orchestration or command execution."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from uuid import uuid4

from factory.workspace import ROOT, validate_project_name
from factory.tools import resolve_path

ROLES = ('codex', 'architect', 'backend', 'frontend', 'reviewer', 'qa', 'devops')
STATUSES = ('working', 'completed', 'waiting', 'error', 'skipped', 'inactive', 'unknown')
TYPES = ('project_started', 'task_created', 'task_delegated', 'agent_working',
         'file_changed', 'command_executed', 'test_passed', 'test_failed', 'error',
         'correction', 'agent_finished', 'project_finished',
         'knowledge_created', 'knowledge_updated', 'knowledge_reused')


def redact(value):
    text = str(value)
    text = re.sub(r'(?i)\b(authorization\s*:\s*bearer|bearer)\s+\S+', r'\1 [REDACTED]', text)
    text = re.sub(r'(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*[^\s,;]+', r'\1=[REDACTED]', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{12,}', '[REDACTED]', text)
    return text[:12000]


def validate_event(data):
    validate_project_name(data['project'])
    if data.get('role') not in ROLES or data.get('type') not in TYPES:
        raise ValueError('Rol o tipo inválido')
    if data.get('status') not in STATUSES:
        raise ValueError('Estado inválido')
    for key in ('task', 'message', 'command', 'url'):
        if not isinstance(data.get(key, ''), str):
            raise ValueError('Texto inválido')
    if not isinstance(data.get('files', []), list) or any(not isinstance(x, str) for x in data.get('files', [])):
        raise ValueError('files debe ser lista de rutas')
    duration = data.get('duration_seconds')
    if duration is not None and (not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0):
        raise ValueError('Duración inválida')
    if data.get('returncode') is not None and type(data['returncode']) is not int:
        raise ValueError('Código de salida inválido')
    return data


def record_event(project, role, event_type, status='unknown', root=ROOT, **fields):
    event = dict(project=project, role=role, type=event_type, status=status,
                 **{k: v for k, v in fields.items() if k in ('task', 'message', 'files', 'command', 'returncode', 'duration_seconds', 'url')})
    validate_event(event)
    for key in ('task', 'message', 'command', 'url'):
        if key in event:
            event[key] = redact(event[key])
    event['files'] = [redact(x) for x in event.get('files', []) if not Path(x.replace('\\', '/')).name.startswith('.env')]
    now = datetime.now(timezone.utc)
    event.update(id=uuid4().hex, timestamp=now.isoformat(), schema_version=1)
    directory = resolve_path(Path(root), f'project-state/{project}/events')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (now.strftime('%Y%m%dT%H%M%S%fZ') + '-' + event['id'] + '.json')
    temporary = target.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(event, ensure_ascii=False), encoding='utf-8')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--role', choices=ROLES, default='codex')
    parser.add_argument('--type', choices=TYPES, required=True)
    parser.add_argument('--status', choices=STATUSES, default='unknown')
    for field in ('task', 'message', 'command', 'url'):
        parser.add_argument('--' + field, default='')
    parser.add_argument('--file', action='append', dest='files', default=[])
    parser.add_argument('--returncode', type=int)
    parser.add_argument('--duration-seconds', type=float)
    args = vars(parser.parse_args())
    args['event_type'] = args.pop('type')
    try:
        print(record_event(**args))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
