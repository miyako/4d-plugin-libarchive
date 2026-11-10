import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github/scripts"))
import dependency


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "root"
        self.root.mkdir()
        self.env = dict(os.environ, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.test",
                        GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.test")
        self.run_git(self.root, "init", "-q")
        self.dep = self.root / "deps/libarchive"
        self.dep.mkdir(parents=True)
        self.run_git(self.dep, "init", "-q")
        (self.dep / "source.c").write_text("int archive_fixture;\n")
        self.run_git(self.dep, "add", ".")
        self.run_git(self.dep, "commit", "-qm", "dependency")
        self.run_git(self.root, "add", "deps/libarchive")
        self.run_git(self.root, "commit", "-qm", "superproject")
        self.sha = self.run_git(self.root, "rev-parse", "HEAD").strip()

    def run_git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], env=self.env, stderr=subprocess.DEVNULL).decode()

    def test_exact_initialized_dependency(self):
        dependency.validate(self.root, self.sha)

    def test_dependency_head_drift(self):
        (self.dep / "source.c").write_text("new\n")
        self.run_git(self.dep, "commit", "-qam", "advance")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_dependency_raw_source_hidden_drift(self):
        self.run_git(self.dep, "update-index", "--assume-unchanged", "source.c")
        (self.dep / "source.c").write_text("hidden\n")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_dependency_index_drift(self):
        (self.dep / "source.c").write_text("staged\n")
        self.run_git(self.dep, "add", "source.c")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_superproject_gitlink_index_drift(self):
        self.run_git(self.dep, "commit", "--allow-empty", "-qm", "advance")
        self.run_git(self.root, "add", "deps/libarchive")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_ignored_source_rejected(self):
        (self.dep / ".git/info/exclude").write_text("evil.c\n")
        (self.dep / "evil.c").write_text("ignored source\n")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_source_symlink_rejected(self):
        (self.dep / "source.c").unlink()
        (self.dep / "source.c").symlink_to(self.root / ".git/HEAD")
        with self.assertRaises(ValueError):
            dependency.validate(self.root, self.sha)

    def test_uninitialized_gitlink_rejected(self):
        (self.dep / ".git").rename(self.root / "dependency-metadata")
        with self.assertRaisesRegex(ValueError, "Git marker"):
            dependency.validate(self.root, self.sha)

    def test_submodule_directory_symlink_rejected(self):
        destination = self.root / "dependency-copy"
        self.dep.rename(destination)
        self.dep.symlink_to(destination, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "nonsymlink"):
            dependency.validate(self.root, self.sha)


if __name__ == "__main__":
    unittest.main()
