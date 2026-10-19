import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("bump_version", Path(__file__).resolve().parents[1] / "tools/bump_version.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VersioningTest(unittest.TestCase):
    def test_baseline_multiple_commits_rerun_and_manual_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return module.git(*args, root=root)

            def commit(message):
                git("add", ".")
                git("commit", "-m", message)

            git("init", "-b", "main")
            git("config", "user.name", "Version test")
            git("config", "user.email", "test@example.invalid")
            version = root / module.VERSION_FILE
            version.parent.mkdir()
            version.write_text('__version__ = "0.5.0"\n', encoding="utf-8")
            commit("baseline")
            self.assertEqual(module.bump(root), 0)
            for number in range(2):
                (root / "change.txt").write_text(str(number))
                commit("change")
            self.assertEqual(module.bump(root), 2)
            self.assertIn('"0.5.2"', version.read_text())
            commit("version")
            self.assertEqual(module.bump(root), 0)
            version.write_text('__version__ = "0.6.0"\n')
            commit("manual minor release")
            (root / "change.txt").write_text("next")
            commit("change")
            self.assertEqual(module.bump(root), 1)
            self.assertIn('"0.6.1"', version.read_text())


if __name__ == "__main__":
    unittest.main()
