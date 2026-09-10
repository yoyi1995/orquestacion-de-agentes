"""Bounded, allowlisted projection of factory evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from factory.activity import ROLES, redact, validate_event
from factory.workspace import ROOT, validate_project_name
from factory.tools import resolve_path


def local_url(value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1') and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
            return value
    except ValueError:
        pass
    return ''


def read_safe(root, path):
    original = Path(path).absolute()
    path = resolve_path(root, path)
    if path != original or path.name.startswith('.env'):
        raise ValueError('Enlace o archivo no permitido')
    if path.stat().st_size > 512000:
        raise ValueError('Archivo supera 512 KB')
    return path.read_text(encoding='utf-8-sig')


def snapshot(root=ROOT):
    root = Path(root).resolve()
    projects = []
    states = resolve_path(root, 'project-state')
    if not states.exists():
        return dict(projects=[], current_project=None, generated_at=datetime.now(timezone.utc).isoformat())
    for directory in sorted(states.iterdir()):
        if not directory.is_dir():
            continue
        try:
            validate_project_name(directory.name)
            directory = resolve_path(states, directory.name)
        except ValueError:
            continue
        warnings, events, runs = [], [], []
        state = ''
        try:
            state = redact(read_safe(root, directory / 'state.md'))
        except (OSError, ValueError):
            warnings.append('Estado ausente, ilegible o fuera del límite permitido.')
        match = re.search(r'^- Estado:\s*(\w+)', state, re.M)
        status = match.group(1) if match else 'unknown'
        status = {'in_progress': 'working', 'blocked': 'waiting'}.get(status, status)
        urls = re.findall(r'http://(?:localhost|127\.0\.0\.1)(?::\d+)?/[^\s]*', state)
        url = next((local_url(u.rstrip('.,)')) for u in urls if local_url(u.rstrip('.,)'))), '')
        updated = datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc).isoformat()
        state_path = directory / 'state.md'
        if state_path.exists():
            updated = datetime.fromtimestamp(state_path.stat().st_mtime, timezone.utc).isoformat()
        for folder, destination in (('events', events), ('runs', runs)):
            try:
                location = resolve_path(root, directory / folder)
                paths = sorted(location.glob('*.json'))
                if folder == 'runs':
                    global_runs = resolve_path(root, 'runs')
                    paths += sorted(global_runs.glob('*.json')) if global_runs.exists() else []
                if len(paths) > 2000:
                    warnings.append(f'{folder}: solo se leen los últimos 2000 registros.')
                for path in paths[-2000:]:
                    try:
                        raw = json.loads(read_safe(root, path))
                        if not isinstance(raw, dict):
                            raise ValueError('Objeto esperado')
                        if raw.get('project', directory.name) != directory.name:
                            continue
                        if path.parent == root / 'runs' and raw.get('project') != directory.name:
                            continue
                        if folder == 'events':
                            validate_event(raw)
                            item = {k: raw[k] for k in ('id', 'timestamp', 'project', 'role', 'type', 'status', 'task', 'message', 'files', 'command', 'returncode', 'duration_seconds', 'url') if k in raw}
                        else:
                            item = {k: raw.get(k) for k in ('timestamp', 'command', 'returncode', 'duration_seconds', 'timed_out', 'error', 'cleanup_error')}
                        stamp = datetime.fromisoformat(item['timestamp'])
                        if stamp.tzinfo is None:
                            raise ValueError('Timestamp sin zona')
                        for key, value in list(item.items()):
                            if isinstance(value, str):
                                item[key] = redact(value)
                        if 'files' in item:
                            item['files'] = [redact(f) for f in item['files'] if not Path(f.replace('\\', '/')).name.startswith('.env')]
                        if 'url' in item:
                            item['url'] = local_url(item['url'])
                        item['source'] = path.relative_to(root).as_posix()
                        destination.append(item)
                    except (OSError, ValueError, KeyError, TypeError):
                        warnings.append(f'{folder}: registro inválido omitido.')
            except (OSError, ValueError):
                warnings.append(f'{folder}: ruta inaccesible.')
        events.sort(key=lambda e: (datetime.fromisoformat(e['timestamp']), e.get('id', '')))
        runs.sort(key=lambda e: datetime.fromisoformat(e['timestamp']))
        no_agents = 'Sin subagentes:' in state
        agents = {role: dict(role=role, status=status if role == 'codex' else ('skipped' if no_agents else 'inactive'), task='', last_action='', started_at=None, finished_at=None) for role in ROLES}
        for event in events:
            agent = agents[event['role']]
            if event['type'] == 'project_started':
                for role, node in agents.items():
                    node.update(status='inactive', task='', last_action='', started_at=None, finished_at=None)
            previous_status = agent['status']
            if event['status'] != 'unknown':
                agent['status'] = event['status']
            agent['task'] = event.get('task') or agent['task']
            agent['last_action'] = event.get('message') or event['type']
            if event['status'] == 'working':
                if agent['started_at'] is None or previous_status in ('completed', 'error', 'skipped'):
                    agent['started_at'] = event['timestamp']
                agent['finished_at'] = None
            if event['status'] in ('completed', 'error', 'skipped'):
                agent['finished_at'] = event['timestamp']
            if event['type'] in ('project_started', 'project_finished'):
                status = event['status']
            if event.get('url'):
                url = event['url']
        if events:
            updated = max(updated, events[-1]['timestamp'])
        projects.append(dict(name=directory.name, status=status, state_excerpt=state, url=url, agents=list(agents.values()), events=events[-200:], runs=runs[-100:], warnings=warnings, updated_at=updated))
    projects.sort(key=lambda p: p['updated_at'], reverse=True)
    return dict(projects=projects, current_project=projects[0]['name'] if projects else None, generated_at=datetime.now(timezone.utc).isoformat())
