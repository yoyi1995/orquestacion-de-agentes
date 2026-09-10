from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_command import main


class RunCommandCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "proyectos" / "demo"
        self.project.mkdir(parents=True)
        self.state = self.root / "project-state" / "demo"
        self.paths = patch("scripts.run_command.project_paths", return_value=(self.project, self.state))
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def invoke(self, result, timeout="5"):
        stdout, stderr = io.StringIO(), io.StringIO()
        def execute(*args):
            print("command execution log")
            if isinstance(result, Exception):
                raise result
            return dict(result)
        with patch("scripts.run_command.run_command", side_effect=execute) as run:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(["--project", "demo", "--timeout", timeout, "--command", "dir"])
        return status, stdout.getvalue(), stderr.getvalue(), run

    def test_success_outputs_json_logs_stderr_and_unique_records(self):
        for _ in range(2):
            status, output, logs, run = self.invoke({"returncode": 0, "timed_out": False})
            self.assertEqual(status, 0)
            parsed = json.loads(output)
            self.assertEqual(parsed["cwd"], str(self.project))
            self.assertEqual(parsed["project"], "demo")
            self.assertIn("+00:00", parsed["timestamp"])
            self.assertIn("execution log", logs)
            run.assert_called_once_with(self.project, "dir", 5)
        self.assertEqual(len(list((self.state / "runs").glob("*.json"))), 2)

    def test_failure_timeout_and_launch_error_are_recorded(self):
        for result, expected in (({"returncode": 256}, 1), ({"returncode": None}, 1),
                                 ({"returncode": 0, "cleanup_error": "failure"}, 1),
                                 ({"returncode": 1, "timed_out": True}, 124),
                                 (OSError("launch failed"), 1)):
            with self.subTest(result=result):
                status, output, _, _ = self.invoke(result)
                self.assertEqual(status, expected)
                self.assertEqual(json.loads(output)["project"], "demo")
        self.assertEqual(len(list((self.state / "runs").glob("*.json"))), 5)

    def test_invalid_timeout_does_not_run_or_create_logs(self):
        status, _, logs, run = self.invoke({}, timeout="601")
        self.assertEqual(status, 1)
        run.assert_not_called()
        self.assertIn("timeout", logs)
        self.assertFalse(self.state.exists())

    def test_missing_project_does_not_execute(self):
        self.project.rmdir()
        status, _, logs, run = self.invoke({})
        self.assertEqual(status, 1)
        run.assert_not_called()
        self.assertIn("no existe", logs)
