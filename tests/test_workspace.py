from pathlib import Path
import tempfile
import unittest

from factory.workspace import new_project, project_paths, validate_project_name


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "factory").mkdir()
        (self.root / "factory" / "project-template.md").write_text(
            "{{PROJECT_NAME}}\n{{REQUEST}}\n{{CREATED_AT}}", encoding="utf-8")

    def test_create_without_stack_and_preserve_request_tokens(self):
        project, state = new_project("demo-1", "Build {{PROJECT_NAME}}", self.root)
        self.assertEqual(list(project.iterdir()), [])
        content = (state / "state.md").read_text(encoding="utf-8")
        self.assertIn("demo-1\nBuild {{PROJECT_NAME}}", content)
        self.assertIn("+00:00", content)

    def test_invalid_names_and_empty_request_write_nothing(self):
        for name in ("../escape", "x/y", "x\\y", "C:\\tmp", "", "CON", "con", "prn",
                     "aux", "nul", "com1", "lpt9", "Upper", "café", "a" * 81):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_project_name(name)
        with self.assertRaises(ValueError):
            new_project("demo", " \n", self.root)
        self.assertFalse((self.root / "proyectos").exists())

    def test_collision_does_not_overwrite_or_create_other_side(self):
        for folder, other in (("proyectos", "project-state"), ("project-state", "proyectos")):
            name = "demo-" + folder
            existing = self.root / folder / name
            existing.mkdir(parents=True)
            (existing / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                new_project(name, "request", self.root)
            self.assertEqual((existing / "keep.txt").read_text(), "keep")
            self.assertFalse((self.root / other / name).exists())

    def test_symlink_escape_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / "proyectos").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Creating symlinks requires additional Windows permissions")
            with self.assertRaises(ValueError):
                project_paths("demo", self.root)
