from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from dashboard.data import snapshot
from factory.knowledge import Knowledge, main, today


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.memory = Knowledge(self.root)
        (self.root / 'proof.txt').write_text('test evidence: observed assertion', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def create(self, path='patterns/example.md', **kwargs):
        return self.memory.save(path, kwargs.pop('title', 'Example'), kwargs.pop('body', '# Example\n\nReusable result.'), **kwargs)

    def test_safe_create_and_metadata(self):
        result = self.create()
        meta, body = self.memory.parse(self.memory.read(result['path']))
        self.assertEqual(meta['status'], 'experimental')
        self.assertIsNone(meta['last_validated'])
        self.assertEqual(meta['created'], today())
        self.assertIn('Reusable', body)
        self.assertFalse((self.root / 'knowledge' / '.write.lock').exists())
        self.assertEqual(len(self.memory.paths()), 1)

    def test_update_preserves_evidence_and_rejects_stale_hash(self):
        original = self.create(status='comprobado', validated='2026-09-09', evidence=['proof.txt'])
        updated = self.memory.save(original['path'], update=True, expected_sha=original['sha256'], body='More precise limitation.', status='obsoleto')
        meta, body = self.memory.parse(self.memory.read(original['path']))
        self.assertEqual(len(self.memory.paths()), 1)
        self.assertEqual(meta['status'], 'obsoleto')
        self.assertEqual(meta['evidence'], ['proof.txt'])
        self.assertIn('Reusable result.', body)
        self.assertIn('More precise limitation.', body)
        with self.assertRaises(ValueError):
            self.memory.save(original['path'], update=True, expected_sha=original['sha256'], body='Stale writer')
        self.assertEqual(hashlib.sha256(self.memory.read(original['path']).encode()).hexdigest(), updated['sha256'])

    def test_duplicate_title_and_content(self):
        self.create(title='Solución DOM')
        for title, body in [('solucion dom', 'Different body'), ('Other title', '# Example\n\nReusable result.')]:
            with self.assertRaises(ValueError):
                self.create('patterns/other.md', title=title, body=body)
        with self.assertRaises(ValueError):
            self.create()
        with self.assertRaises(ValueError):
            self.create('security/example.md', title='Another topic', body='Another result')

    def test_wikilinks_resolve_alias_heading_and_unique_basename(self):
        self.create()
        self.create('projects/project.md', title='Project', body='[[patterns/example|Example]] and [[example#Context]]')
        self.assertEqual(self.memory.check(), [])
        for link in ('[[missing]]', '[[]]', '[[broken][target]]', '[[example]', '[[../escape]]', '[[C:/escape]]'):
            with self.subTest(link=link), self.assertRaises(ValueError):
                self.create('patterns/invalid.md', title='Invalid', body=link)

    def test_outside_windows_paths_and_ads_blocked(self):
        for path in ('../escape.md', '/tmp/escape.md', 'C:/escape.md', 'C:escape.md', '//server/share/x.md', 'patterns/../../escape.md', 'patterns/x.md:stream', 'patterns/CON.md', 'patterns\\x.md', '.env', '.obsidian/x.md'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.create(path)
        self.assertFalse((self.root / 'escape.md').exists())

    def test_junction_or_symlink_escape_blocked(self):
        vault = self.root / 'knowledge'
        vault.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        link = vault / 'patterns'
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, 'Could not set up junction test')
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(list(outside.iterdir()), [])

    def test_secrets_rejected_before_write_or_read(self):
        secrets = ['password="test-only-value"', 'Bearer test-only-token', 'sk-' + 'z' * 20, '-----BEGIN PRIVATE KEY-----', 'https://user:password@example.invalid', 'eyJabc.abc.def']
        for value in secrets:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.create(body=value)
        self.assertEqual(self.memory.paths(), [])
        self.create()
        target = self.root / 'knowledge/patterns/example.md'
        target.write_text('token=test-only-value')
        with self.assertRaises(ValueError):
            self.memory.read('patterns/example.md')
        self.assertTrue(self.memory.check())

    def test_checked_requires_existing_evidence_and_date(self):
        for options in (dict(status='comprobado'), dict(status='comprobado', validated='2026-09-09'), dict(status='comprobado', validated='2026-09-09', evidence=['missing.txt']), dict(validated='9999-01-01'), dict(evidence=['../escape.txt'])):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.create(**options)
        self.create(status='comprobado', validated='2026-09-09', evidence=['proof.txt'])
        self.assertEqual(self.memory.check(), [])

    def test_search_selective_normalized_and_obsolete_excluded(self):
        first = self.create(title='Sincronización iframe', body='DOM y contexto')
        self.create('patterns/other.md', title='Other', body='Unrelated content')
        matches = self.memory.search('sincronizacion iframe')
        self.assertEqual([m['path'] for m in matches], ['patterns/example.md'])
        self.assertNotIn('content', matches[0])
        self.memory.save(first['path'], update=True, expected_sha=first['sha256'], status='obsoleto', body='Superseded')
        self.assertEqual(self.memory.search('iframe'), [])
        self.assertEqual(len(self.memory.search('iframe', include_obsolete=True)), 1)
        with self.assertRaises(ValueError):
            self.memory.search('')

    def test_no_memory_required_no_note_no_event(self):
        result = self.memory.save('patterns/nothing.md', title='No contribution', body='  \n', project='demo')
        self.assertEqual(result['action'], 'skipped')
        self.assertFalse((self.root / 'knowledge').exists())
        self.assertFalse((self.root / 'project-state').exists())
        self.assertEqual(self.memory.search('nothing'), [])

    def test_activity_integration_and_reuse_not_implied_by_read(self):
        result = self.create(project='demo', status='comprobado', validated='2026-09-09', evidence=['proof.txt'])
        self.memory.read(result['path'])
        self.memory.search('example')
        events = list((self.root / 'project-state/demo/events').glob('*.json'))
        self.assertEqual(len(events), 1)
        self.memory.save(result['path'], update=True, expected_sha=result['sha256'], body='Reviewed applicability', project='demo')
        self.memory.reuse(result['path'], 'demo', 'Same documented context')
        p = snapshot(self.root)['projects'][0]
        self.assertEqual([e['type'] for e in p['events']], ['knowledge_created', 'knowledge_updated', 'knowledge_reused'])
        self.assertEqual(p['agents'][0]['status'], 'unknown')
        self.assertEqual(p['warnings'], ['Estado ausente, ilegible o fuera del límite permitido.'])

    def test_optional_event_failure_keeps_saved_note(self):
        with patch('factory.knowledge.record_event', side_effect=OSError('unavailable')):
            result = self.create(project='demo', status='comprobado', validated='2026-09-09', evidence=['proof.txt'])
            self.assertIn('warning', result)
            self.assertIn('warning', self.memory.reuse(result['path'], 'demo', 'Same context'))
        self.assertEqual(len(self.memory.paths()), 1)

    def test_atomic_replacement_failure_preserves_previous_note(self):
        result = self.create()
        before = self.memory.read(result['path'])
        with patch.object(Path, 'replace', side_effect=OSError('simulated disk error')):
            with self.assertRaises(OSError):
                self.memory.save(result['path'], update=True, expected_sha=result['sha256'], body='New finding')
        self.assertEqual(self.memory.read(result['path']), before)
        self.assertFalse((self.root / 'knowledge/.write.lock').exists())
        self.assertEqual(list((self.root / 'knowledge/patterns').glob('*.tmp')), [])

    def test_busy_lock_and_experimental_reuse_rejected(self):
        self.create()
        with self.assertRaises(ValueError):
            self.memory.reuse('patterns/example.md', 'demo', 'Same context')
        lock = self.root / 'knowledge/.write.lock'
        lock.write_text('busy')
        with self.assertRaises(ValueError):
            self.create('patterns/second.md', title='Second', body='Different result')
        self.assertEqual(lock.read_text(), 'busy')

    def test_cli_secret_not_echoed(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch('factory.knowledge.Knowledge', return_value=self.memory), patch('sys.stdin', io.StringIO('password=test-only-secret')), redirect_stdout(output), redirect_stderr(errors):
            code = main(['create', 'patterns/private.md', '--title', 'Private'])
        self.assertEqual(code, 1)
        self.assertNotIn('test-only-secret', output.getvalue() + errors.getvalue())
        self.assertFalse((self.root / 'knowledge/patterns/private.md').exists())

    def test_real_vault_links_evidence_and_initial_selection(self):
        actual = Knowledge()
        self.assertEqual(actual.check(), [])
        notes = actual.paths()
        self.assertIn('errors-solutions/iframe-documento-inicial.md', notes)
        self.assertIn('projects/calculadora_demo.md', notes)
        self.assertTrue(any(m['path'] == 'errors-solutions/iframe-documento-inicial.md' for m in actual.search('iframe')))


if __name__ == '__main__':
    unittest.main()
