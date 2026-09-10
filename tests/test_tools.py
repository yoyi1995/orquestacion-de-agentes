import contextlib
import ctypes
import io
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from factory.tools import run_command


def python_command(code):
    args = [sys.executable, "-u", "-c", code]
    return subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)


class RunCommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_success_and_console_log(self):
        command = python_command("import pathlib; print(pathlib.Path.cwd().name)")
        console = io.StringIO()
        with contextlib.redirect_stdout(console):
            result = run_command(self.root, command, timeout=5)
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["stdout"].strip(), self.root.name)
        self.assertEqual(result["stderr"], "")
        self.assertGreaterEqual(result["duration_seconds"], 0)
        for value in (command, "Timeout: 5 s", "Código de salida: 0",
                      "Duración:", "stdout", "stderr", self.root.name):
            self.assertIn(value, console.getvalue())

    def test_nonzero_exit_preserves_output(self):
        result = run_command(self.root, python_command(
            "import sys; print('before failure'); print('failure', file=sys.stderr); sys.exit(7)"
        ), timeout=5)
        self.assertEqual(result["returncode"], 7)
        self.assertFalse(result["timed_out"])
        self.assertIn("before failure", result["stdout"])
        self.assertIn("failure", result["stderr"])

    def test_timeout_returns_partial_output(self):
        started = time.monotonic()
        result = run_command(self.root, python_command(
            "import time; print('started', flush=True); time.sleep(60)"
        ), timeout=1)
        self.assertLess(time.monotonic() - started, 20)
        self.assertTrue(result["timed_out"])
        self.assertIn("timeout", result["error"])
        self.assertIn("started", result["stdout"])
        self.assertIsNotNone(result["returncode"])
        self.assertNotEqual(result["returncode"], 0)
        self.assertNotIn("cleanup_error", result)

    def test_invalid_timeouts_never_launch_a_process(self):
        with patch("factory.tools.subprocess.Popen") as popen:
            for timeout in (None, True, False, "5", 1.5, 0, -1, 601, float("inf")):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    run_command(self.root, "unused", timeout=timeout)
            popen.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows process tree regression")
    def test_windows_timeout_terminates_grandchild(self):
        # The grandchild inherits output handles, reproducing the former hang.
        script = self.root / "parent.py"
        script.write_text(
            "import subprocess, sys, time\n"
            "from pathlib import Path\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "Path('child.pid').write_text(str(child.pid))\n"
            "print('child started', flush=True)\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        result = run_command(self.root, python_command(
            "exec(open('parent.py').read())"
        ), timeout=2)
        self.assertTrue(result["timed_out"])
        self.assertNotIn("cleanup_error", result)
        pid = int((self.root / "child.pid").read_text())
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel32.WaitForSingleObject.restype = ctypes.c_ulong
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            try:
                self.assertEqual(kernel32.WaitForSingleObject(handle, 0), 0)
            finally:
                kernel32.CloseHandle(handle)
        else:
            self.assertEqual(ctypes.get_last_error(), 87)  # PID no longer exists


if __name__ == "__main__":
    unittest.main()
