from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from factory.activity import record_event
from dashboard.data import snapshot, local_url
from dashboard.server import Handler, ThreadingHTTPServer


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / 'project-state' / 'demo'
        self.state.mkdir(parents=True)
        (self.state / 'state.md').write_text('- Estado: completed\nSin subagentes:\nhttp://localhost:8765/\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, **kwargs):
        return record_event('demo', kwargs.pop('role', 'codex'), kwargs.pop('event_type', 'agent_working'), root=self.root, **kwargs)

    def test_historical_data_does_not_invent_agents(self):
        p = snapshot(self.root)['projects'][0]
        self.assertEqual(p['status'], 'completed')
        self.assertEqual(p['events'], [])
        self.assertTrue(all(a['status'] == 'skipped' for a in p['agents'][1:]))
        self.assertEqual(p['url'], 'http://localhost:8765/')

    def test_concurrent_atomic_events(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            paths = list(pool.map(lambda i: self.event(message=f'file {i}'), range(40)))
        self.assertEqual(len(set(paths)), 40)
        self.assertEqual(len(snapshot(self.root)['projects'][0]['events']), 40)
        self.assertEqual(list((self.state / 'events').glob('*.tmp')), [])

    def test_lifecycle_and_project_reset(self):
        self.event(event_type='project_started', status='working')
        self.event(role='frontend', status='working', task='UI')
        self.event(role='frontend', event_type='agent_finished', status='completed')
        p = snapshot(self.root)['projects'][0]
        frontend = next(a for a in p['agents'] if a['role'] == 'frontend')
        self.assertEqual(frontend['status'], 'completed')
        self.assertTrue(frontend['started_at'] and frontend['finished_at'])
        self.event(event_type='project_finished', status='completed')
        self.assertEqual(snapshot(self.root)['projects'][0]['status'], 'completed')
        self.event(event_type='project_started', status='working')
        self.assertEqual(snapshot(self.root)['projects'][0]['agents'][3]['status'], 'inactive')

    def test_secrets_and_malformed_records(self):
        self.event(message='token=secret123 Bearer abcdef', files=['.env', 'app.js'])
        (self.state / 'events' / 'bad.json').write_text('{')
        (self.state / 'events' / 'unfinished.tmp').write_text('{')
        p = snapshot(self.root)['projects'][0]
        serialized = json.dumps(p)
        self.assertNotIn('secret123', serialized)
        self.assertNotIn('abcdef', serialized)
        self.assertEqual(p['events'][0]['files'], ['app.js'])
        self.assertEqual(len(p['warnings']), 1)

    def test_new_task_clears_previous_finish(self):
        self.event(role='frontend', status='working', task='First task')
        self.event(role='frontend', event_type='agent_finished', status='completed')
        self.event(role='frontend', status='working', task='Second task')
        node = snapshot(self.root)['projects'][0]['agents'][3]
        self.assertEqual(node['task'], 'Second task')
        self.assertIsNone(node['finished_at'])

    def test_global_runs_are_scoped(self):
        runs = self.root / 'runs'
        runs.mkdir()
        raw = dict(timestamp='2026-09-09T00:00:00+00:00', command='test', returncode=0)
        (runs / 'no-project.json').write_text(json.dumps(raw))
        (runs / 'other.json').write_text(json.dumps(dict(raw, project='other')))
        (runs / 'demo.json').write_text(json.dumps(dict(raw, project='demo')))
        self.assertEqual(len(snapshot(self.root)['projects'][0]['runs']), 1)

    def test_invalid_inputs_and_local_url(self):
        for name in ('../escape', 'CON', 'con', 'x/y'):
            with self.assertRaises(ValueError):
                record_event(name, 'codex', 'error', root=self.root)
        with self.assertRaises(ValueError):
            self.event(duration_seconds=float('nan'))
        for value in ('javascript:alert(1)', 'https://example.com', 'http://localhost.evil/', 'http://user:password@localhost/', 'http://localhost/?token=x'):
            self.assertEqual(local_url(value), '')

    def test_run_allowlist_and_failure_preserved(self):
        runs = self.state / 'runs'
        runs.mkdir()
        (runs / 'run.json').write_text(json.dumps(dict(timestamp='2026-09-09T00:00:00+00:00', command='node --test', returncode=1, timed_out=True, duration_seconds=2, stdout='private', stderr='private')))
        p = snapshot(self.root)['projects'][0]
        self.assertEqual(p['runs'][0]['returncode'], 1)
        self.assertTrue(p['runs'][0]['timed_out'])
        self.assertNotIn('private', json.dumps(p))
        self.assertEqual(p['events'], [])

    def test_real_calculadora_demo(self):
        p = next((p for p in snapshot()['projects'] if p['name'] == 'calculadora_demo'), None)
        if p is None:
            self.skipTest('Integración local opcional: calculadora_demo no se publica con la fábrica')
        self.assertEqual(p['status'], 'completed')
        self.assertTrue(any(r['command'] == 'node --test tests/calculator.test.js' and r['returncode'] == 0 for r in p['runs']))
        self.assertTrue(all(a['status'] == 'skipped' for a in p['agents'][1:]))

    def test_read_only_http_and_host(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch('dashboard.server.snapshot', return_value=snapshot(self.root)):
                for method, path, expected in [('GET', '/api/snapshot', 200), ('GET', '/', 200), ('GET', '/.env', 404), ('GET', '/../AGENTS.md', 404), ('POST', '/api/snapshot', 501)]:
                    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                    conn.request(method, path)
                    response = conn.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                    conn.close()
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                conn.request('GET', '/api/snapshot', headers={'Host': 'evil.example'})
                self.assertEqual(conn.getresponse().status, 403)
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
