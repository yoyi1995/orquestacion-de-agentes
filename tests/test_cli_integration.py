"""Exercise the documented CLIs in a disposable workspace without site packages."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="factory integration ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for folder in ("factory", "scripts"):
            shutil.copytree(ROOT / folder, self.root / folder,
                            ignore=shutil.ignore_patterns("__pycache__"))

    def cli(self, module, *args):
        return subprocess.run(
            [sys.executable, "-B", "-S", "-m", module, *args],
            cwd=self.root, capture_output=True, text=True, timeout=25,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def command(self, *args):
        values = [sys.executable, *args]
        return subprocess.list2cmdline(values) if os.name == "nt" else shlex.join(values)

    def test_new_project_compile_record_and_collision(self):
        created = self.cli("scripts.new_project", "demo", "--request", "Un producto de prueba")
        self.assertEqual(created.returncode, 0, created.stderr)
        project = self.root / "proyectos" / "demo"
        source = project / "example.py"
        source.write_text("answer = 42\n", encoding="utf-8")
        compiled = self.cli("scripts.run_command", "--project", "demo", "--timeout", "5",
                            "--command", self.command("-m", "py_compile", "example.py"))
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        result = json.loads(compiled.stdout)
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        state = self.root / "project-state" / "demo"
        records = list((state / "runs").glob("*.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text(encoding="utf-8")), result)
        state_before = (state / "state.md").read_bytes()
        self.assertIn("Un producto de prueba", state_before.decode("utf-8"))
        collision = self.cli("scripts.new_project", "demo", "--request", "Replacement")
        self.assertNotEqual(collision.returncode, 0)
        self.assertEqual((state / "state.md").read_bytes(), state_before)
        self.assertEqual(source.read_text(), "answer = 42\n")

    def test_error_and_timeout_are_recorded_and_return_nonzero(self):
        created = self.cli("scripts.new_project", "demo", "--request", "Temporary verification")
        self.assertEqual(created.returncode, 0, created.stderr)
        for code, expected_status, timed_out in (
            ("import sys; print('failure', file=sys.stderr); sys.exit(7)", 1, False),
            ("import time; print('started', flush=True); time.sleep(60)", 124, True),
        ):
            with self.subTest(timed_out=timed_out):
                completed = self.cli("scripts.run_command", "--project", "demo", "--timeout", "1",
                                     "--command", self.command("-u", "-c", code))
                self.assertEqual(completed.returncode, expected_status, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["timed_out"], timed_out)
                self.assertNotEqual(result["returncode"], 0)
                self.assertIn("started" if timed_out else "failure",
                              result["stdout"] if timed_out else result["stderr"])
        records = list((self.root / "project-state" / "demo" / "runs").glob("*.json"))
        self.assertEqual(len(records), 2)
