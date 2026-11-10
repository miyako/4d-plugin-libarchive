import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "refs/heads/miyako-simplify-libarchive-workflows"
ZERO = "0" * 40


class MigrationGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.local, self.bare = directory / "local", directory / "bare.git"
        self.local.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.test",
                        GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.test",
                        PYTHONDONTWRITEBYTECODE="1")
        self.run_git("init", "-q")
        subprocess.run(["git", "init", "--bare", "-q", str(self.bare)], check=True, env=self.env)
        for path in (".github/scripts/repository.py", ".github/scripts/dependency.py", ".github/migration-hooks/pre-push"):
            target = self.local / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        self.hook = self.local / ".github/migration-hooks/pre-push"
        self.hook.chmod(0o755)
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "migration fixture")
        self.sha = self.run_git("rev-parse", "HEAD").strip()
        self.run_git("remote", "add", "origin", str(self.bare))
        self.env.update(MIGRATION_HEAD=self.sha, MIGRATION_OLD=ZERO)

    def run_git(self, *args, check=True):
        result = subprocess.run(["git", "-C", str(self.local), *args], env=self.env, check=check,
                                capture_output=True, text=True)
        return result.stdout if check else result

    def invoke(self, records):
        return subprocess.run([sys.executable, str(self.hook)], cwd=self.local, input=records,
                              env=self.env, text=True, capture_output=True)

    def test_real_push_records_one_exact_new_branch(self):
        log = self.local.parent / "advertisement.txt"
        self.env["MIGRATION_ADVERTISEMENT_LOG"] = str(log)
        self.run_git("-c", "core.hooksPath=.github/migration-hooks", "-c", "push.followTags=false",
                     "push", "--no-follow-tags", "origin", f"{self.sha}:{BRANCH}")
        self.assertEqual(log.read_text().split(), [self.sha, self.sha, BRANCH, ZERO])
        remote = subprocess.check_output(["git", "--git-dir", str(self.bare), "rev-parse", BRANCH], text=True)
        self.assertEqual(remote.strip(), self.sha)
        self.assertEqual(subprocess.check_output(["git", "--git-dir", str(self.bare), "tag"], text=True), "")

    def test_missing_multiple_wrong_literal_records(self):
        good = f"{self.sha} {self.sha} {BRANCH} {ZERO}\n"
        for records in ("", good + good, good.replace(BRANCH, "refs/heads/main"),
                        good.replace(ZERO, self.sha), good.replace(self.sha, "HEAD", 1)):
            self.assertNotEqual(self.invoke(records).returncode, 0)

    def test_executable_content_and_symlink_integrity(self):
        original = self.hook.read_bytes()
        for kind in ("content", "symlink", "nonexec"):
            if self.hook.is_symlink():
                self.hook.unlink()
            self.hook.write_bytes(original)
            self.hook.chmod(0o755)
            if kind == "content":
                self.hook.write_bytes(original + b"\n# modified\n")
            elif kind == "symlink":
                peer = self.local.parent / "same-bytes"
                peer.write_bytes(original)
                peer.chmod(0o755)
                self.hook.unlink()
                self.hook.symlink_to(peer)
            else:
                self.hook.chmod(0o644)
            self.assertNotEqual(self.invoke(f"{self.sha} {self.sha} {BRANCH} {ZERO}\n").returncode, 0)


if __name__ == "__main__":
    unittest.main()
