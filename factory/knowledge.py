"""Selective Markdown memory. No models, command execution, or mandatory writes."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import unicodedata
from uuid import uuid4

from factory.activity import ROLES, record_event
from factory.workspace import ROOT, RESERVED, validate_project_name

CATEGORIES = ('technologies', 'architectures', 'patterns', 'errors-solutions',
              'security', 'decisions', 'projects')
STATUSES = ('experimental', 'comprobado', 'obsoleto')
MAX_BYTES = 64000
SECRET_PATTERNS = (
    r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----',
    r'(?i)\b(?:bearer)\s+[A-Za-z0-9._~+/-]{6,}',
    r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,}|AKIA[A-Z0-9]{16})\b',
    r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b',
    r'(?i)\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\b["\x27]?\s*[:=]\s*["\x27]?[^\s"\x27,;<>]{4,}',
    r'(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@',
)


def today():
    return datetime.now(timezone.utc).date().isoformat()


def safe_text(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES or '\x00' in text:
        raise ValueError('Texto inválido o superior a 64 KB')
    if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
        raise ValueError('Contenido rechazado: posible secreto; no se guardó ni se muestra')
    return text


def normalized(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return ' '.join(re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c))))


class Knowledge:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.vault = self.root / 'knowledge'
        if self.vault.resolve() != self.vault:
            raise ValueError('knowledge no puede ser un enlace o junction')

    def path(self, relative):
        safe_text(relative)
        if not isinstance(relative, str) or '\\' in relative or PureWindowsPath(relative).drive:
            raise ValueError('Usa ruta Markdown relativa al vault con /')
        parts = relative.split('/')
        if any(not p or p in ('.', '..') or p.endswith((' ', '.')) or re.search(r'[<>:"|?*\x00-\x1f]', p) or p.split('.')[0].casefold() in RESERVED for p in parts):
            raise ValueError('Ruta de nota inválida')
        if not relative.endswith('.md') or any(p.startswith('.') for p in parts):
            raise ValueError('Solo notas Markdown visibles')
        target = self.vault.joinpath(*parts)
        if target.resolve() != target or self.vault not in target.resolve().parents:
            raise ValueError('Ruta fuera del vault o enlace no permitido')
        return target

    def read(self, relative):
        target = self.path(relative)
        if target.stat().st_size > MAX_BYTES:
            raise ValueError('Nota superior a 64 KB')
        return safe_text(target.read_text(encoding='utf-8-sig'))

    def paths(self, include_support=False):
        if not self.vault.exists():
            return []
        found = []
        for folder, dirs, files in os.walk(self.vault, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and (Path(folder) / d).resolve() == Path(folder) / d)
            for name in sorted(files):
                rel = (Path(folder) / name).relative_to(self.vault).as_posix()
                if name.endswith('.md') and (include_support or rel.split('/')[0] in CATEGORIES):
                    self.path(rel)
                    found.append(rel)
        return found

    @staticmethod
    def parse(content):
        if not content.startswith('---\n') or '\n---\n' not in content[4:]:
            raise ValueError('Falta cabecera de metadatos')
        header, body = content[4:].split('\n---\n', 1)
        meta = {}
        for line in header.splitlines():
            key, sep, value = line.partition(':')
            if not sep or key in meta:
                raise ValueError('Cabecera inválida')
            try:
                meta[key] = json.loads(value.strip())
            except json.JSONDecodeError:
                raise ValueError('Usa escalares JSON en la cabecera YAML; consulta plantilla') from None
        if not isinstance(meta.get('title'), str) or not meta['title'].strip() or meta.get('category') not in CATEGORIES or meta.get('status') not in STATUSES:
            raise ValueError('Título, categoría o estado inválido')
        date.fromisoformat(meta['created'])
        if meta.get('last_validated') is not None:
            date.fromisoformat(meta['last_validated'])
        if not isinstance(meta.get('evidence'), list) or any(not isinstance(v, str) for v in meta['evidence']):
            raise ValueError('evidence debe ser una lista de referencias')
        if meta['status'] == 'comprobado' and (not meta['last_validated'] or not meta['evidence']):
            raise ValueError('Comprobado exige fecha y evidencia; el autor debe verificarla')
        return meta, body

    @staticmethod
    def render(meta, body):
        return '---\n' + '\n'.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in meta.items()) + '\n---\n\n' + body.strip() + '\n'

    def links(self, content, self_path=None):
        known = self.paths(include_support=True)
        if self_path and self_path not in known:
            known.append(self_path)
        errors = []
        remaining = re.sub(r'\[\[([^\[\]\n]+)\]\]', '', content)
        if '[[' in remaining or ']]' in remaining:
            errors.append('Sintaxis de enlace incompleta')
        for link in re.findall(r'\[\[([^\[\]\n]+)\]\]', content):
            target = link.split('|', 1)[0].split('#', 1)[0].strip()
            if not target:
                if link.startswith('#'):
                    continue
                errors.append('Enlace vacío')
                continue
            rel = target if target.endswith('.md') else target + '.md'
            self.path(rel)  # Reject absolute/traversal even if unresolved.
            matches = [p for p in known if (p.casefold() == rel.casefold() if '/' in target else Path(p).name.casefold() == rel.casefold())]
            if len(matches) != 1:
                errors.append('Enlace ausente o ambiguo: ' + target)
        return errors

    @contextmanager
    def lock(self):
        self.vault.mkdir(parents=True, exist_ok=True)
        lock = self.vault / '.write.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ValueError('Hay otra escritura o un bloqueo pendiente; inspecciona .write.lock') from None
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(str(os.getpid()))
            yield
        finally:
            lock.unlink()

    def evidence(self, refs):
        for ref in refs:
            if not isinstance(ref, str) or '\\' in ref or PureWindowsPath(ref).drive or ref.startswith('/'):
                raise ValueError('Evidencia: usa ruta relativa al workspace')
            parts = ref.split('/')
            if any(p in ('', '.', '..', 'backups', '.venv', 'node_modules') or p.startswith('.') or re.search(r'[<>:"|?*\x00-\x1f]', p) for p in parts):
                raise ValueError('Evidencia no permitida')
            path = self.root.joinpath(*parts)
            if path.resolve() != path or not path.is_file():
                raise ValueError('Referencia de evidencia inexistente o enlazada')

    def save(self, relative, title=None, body='', *, update=False, expected_sha=None,
             status=None, validated=None, evidence=(), project=None, role='codex'):
        target = self.path(relative)
        if len(relative.split('/')) != 2 or relative.split('/')[0] not in CATEGORIES:
            raise ValueError('Escribe en una categoría y un archivo .md')
        safe_text(body)
        if not body.strip():
            return dict(action='skipped', reason='Sin conocimiento nuevo; no se escribe ninguna nota')
        if project:
            validate_project_name(project)
        if role not in ROLES:
            raise ValueError('Rol inválido')
        if validated and date.fromisoformat(validated) > date.fromisoformat(today()):
            raise ValueError('La validación no puede tener fecha futura')
        self.evidence(evidence)
        with self.lock():
            if update:
                old = self.read(relative)
                if not expected_sha or hashlib.sha256(old.encode('utf-8')).hexdigest() != expected_sha:
                    raise ValueError('La nota cambió o falta --expected-sha; vuelve a leerla')
                meta, old_body = self.parse(old)
                # Append-only amendments preserve prior evidence and historical context.
                meta['status'] = status or meta['status']
                meta['last_validated'] = validated or meta['last_validated']
                meta['evidence'] = list(dict.fromkeys(meta['evidence'] + list(evidence)))
                meta['updated'] = today()
                body = old_body.rstrip() + f'\n\n## Actualización {today()}\n\n' + body.strip()
            else:
                if target.exists():
                    raise ValueError('La nota ya existe; usa update')
                safe_text(title or '')
                meta = dict(title=title, category=relative.split('/')[0], created=today(),
                            last_validated=validated, status=status or 'experimental', evidence=list(evidence))
                for existing in self.paths():
                    existing_meta, existing_body = self.parse(self.read(existing))
                    if Path(existing).name.casefold() == target.name.casefold() or normalized(existing_meta['title']) == normalized(title or '') or normalized(existing_body) == normalized(body):
                        raise ValueError('Ya existe título o contenido equivalente: ' + existing)
            content = safe_text(self.render(meta, body))
            self.parse(content)
            problems = self.links(content, relative)
            if problems:
                raise ValueError('; '.join(problems))
            # Revalidate after acquiring the lock, before creating any note directories.
            target = self.path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name('.' + target.name + '-' + uuid4().hex + '.tmp')
            try:
                with temporary.open('x', encoding='utf-8', newline='\n') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        action = 'knowledge_updated' if update else 'knowledge_created'
        result = dict(action=action, path=relative, sha256=hashlib.sha256(content.encode('utf-8')).hexdigest())
        if project:
            try:
                record_event(project, role, action, root=self.root, message=f'Memoria: {relative}', files=['knowledge/' + relative])
            except (OSError, ValueError):
                result['warning'] = 'Nota guardada; falló el registro operativo'
        return result

    def search(self, query, limit=5, include_obsolete=False):
        safe_text(query)
        terms = normalized(query).split()
        if not terms or not 1 <= limit <= 20:
            raise ValueError('Consulta no vacía y límite 1–20 requeridos')
        matches = []
        for relative in self.paths():
            content = self.read(relative)
            meta, body = self.parse(content)
            if meta['status'] == 'obsoleto' and not include_obsolete:
                continue
            haystack = normalized(meta['title'] + ' ' + body)
            if all(term in haystack for term in terms):
                score = sum(term in normalized(meta['title']) for term in terms)
                matches.append(dict(path=relative, title=meta['title'], status=meta['status'], last_validated=meta['last_validated'], score=score))
        return sorted(matches, key=lambda m: (-m['score'], m['path']))[:limit]

    def reuse(self, relative, project, reason, role='codex'):
        safe_text(reason)
        if not reason.strip():
            raise ValueError('Explica brevemente la aplicabilidad, sin razonamiento privado')
        meta, _ = self.parse(self.read(relative))
        if meta['status'] != 'comprobado':
            raise ValueError('Reutilización confirmada exige nota comprobada; experimental/obsoleta solo como referencia')
        validate_project_name(project)
        if role not in ROLES:
            raise ValueError('Rol inválido')
        result = dict(action='knowledge_reused', path=relative)
        try:
            record_event(project, role, 'knowledge_reused', root=self.root,
                         message=f'{relative}: {reason}', files=['knowledge/' + relative])
        except (OSError, ValueError):
            result['warning'] = 'Reutilización confirmada; falló el registro operativo'
        return result

    def check(self):
        errors = []
        for relative in self.paths(include_support=True):
            try:
                content = self.read(relative)
                if relative.split('/')[0] in CATEGORIES:
                    meta, _ = self.parse(content)
                    self.evidence(meta['evidence'])
                errors.extend(f'{relative}: {e}' for e in self.links(content, relative))
            except (OSError, ValueError, KeyError, TypeError):
                errors.append(f'{relative}: nota, evidencia o contenido inválido')
        return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    search = sub.add_parser('search')
    search.add_argument('query')
    search.add_argument('--limit', type=int, default=5)
    search.add_argument('--include-obsolete', action='store_true')
    sub.add_parser('check')
    read = sub.add_parser('read')
    read.add_argument('path')
    for name in ('create', 'update'):
        p = sub.add_parser(name)
        p.add_argument('path')
        if name == 'create':
            p.add_argument('--title', required=True)
        else:
            p.add_argument('--expected-sha', required=True)
        p.add_argument('--status', choices=STATUSES)
        p.add_argument('--validated')
        p.add_argument('--evidence', action='append', default=[])
        p.add_argument('--project')
        p.add_argument('--role', choices=ROLES, default='codex')
    reuse = sub.add_parser('reuse')
    reuse.add_argument('path')
    reuse.add_argument('--project', required=True)
    reuse.add_argument('--reason', required=True)
    reuse.add_argument('--role', choices=ROLES, default='codex')
    args = vars(parser.parse_args(argv))
    action = args.pop('action')
    try:
        memory = Knowledge()
        if action in ('create', 'update'):
            args['relative'] = args.pop('path')
            result = memory.save(**args, update=action == 'update', body=sys.stdin.read(MAX_BYTES + 1))
        elif action == 'read':
            content = memory.read(args['path'])
            result = dict(sha256=hashlib.sha256(content.encode('utf-8')).hexdigest(), content=content)
        elif action == 'reuse':
            args['relative'] = args.pop('path')
            result = memory.reuse(**args)
        elif action == 'check':
            result = memory.check()
        else:
            result = memory.search(**args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if action == 'check' and result else 0
    except (ValueError, OSError, KeyError, TypeError):
        # Do not echo untrusted inputs, which may contain sensitive text.
        print('Operación rechazada: comprueba ruta, contenido, enlaces, evidencia y hash de la nota. No se muestran datos sensibles.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
