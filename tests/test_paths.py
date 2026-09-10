from pathlib import Path
import tempfile
import unittest

from factory.tools import list_directory, read_file, resolve_path, write_file


class FileToolsTests(unittest.TestCase):
    def test_file_operations_stay_inside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_file(root, "src/example.txt", "contenido")
            self.assertEqual(read_file(root, "src/example.txt"), "contenido")
            self.assertEqual(list_directory(root), ["[DIR] src"])
            self.assertEqual(resolve_path(root, "."), root.resolve())
            with self.assertRaises(FileNotFoundError):
                read_file(root, "missing.txt")

    def test_parent_and_absolute_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            for name in ("../outside.txt", str(Path(directory) / "outside.txt")):
                with self.subTest(path=name), self.assertRaises(ValueError):
                    write_file(root, name, "must not be written")
            self.assertFalse((Path(directory) / "outside.txt").exists())
