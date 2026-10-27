from pathlib import Path
import tempfile
from packer import git


class GitFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.test")
        git(self.root, "config", "user.name", "Test")
        (self.root / "a.py").write_text("def calculate(x):\n    return 10 / x\n")
        (self.root / "caller.py").write_text("from a import calculate\n\nprint(calculate(0))\n")
        (self.root / "deleted.py").write_text("def gone():\n    return 1\n")
        self.base = self.commit()
        (self.root / "a.py").write_text("def calculate(x):\n    return 20 / x\n")
        (self.root / "deleted.py").unlink()
        (self.root / "package-lock.json").write_text('{"generated":1}')
        (self.root / "binary.bin").write_bytes(b"\x00\x01")
        self.head = self.commit()


    def commit(self):
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "fixture")
        return git(self.root, "rev-parse", "HEAD").decode().strip()
