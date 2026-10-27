from pathlib import Path
import tempfile
import unittest
from core import Config, Gate
from fixtures import pr

class CoreTests(unittest.TestCase):
    def test_sample_excludes_root_and_nested_generated_paths(self):
        config = Config.load(Path(__file__).resolve().parents[2] / '.impact-review.yml')
        for path in ('generated/client.py', 'src/generated/client.py'):
            self.assertFalse(config.accepts(path))
        self.assertTrue(config.accepts('src/client.py'))

    def test_gate_rejects_missing_author(self):
        for author in (None, {}, {'login': None}):
            item = pr()
            item['user'] = author
            self.assertFalse(Gate.eligible(item, 'o/r'))
        item.pop('user')
        self.assertFalse(Gate.eligible(item, 'o/r'))

    def test_gate(self):
        self.assertTrue(Gate.eligible(pr(), "o/r"))
        for field, value in [("draft", True), ("state", "closed"),
                             ("user", {"login": "dependabot[bot]", "type": "Bot"}),
                             ("head", {"repo": None})]:
            item = pr()
            item[field] = value
            self.assertFalse(Gate.eligible(item, "o/r"))
        self.assertFalse(Gate.eligible(pr(), "other/repo"))
        self.assertFalse(Gate.has_targets([]))


    def test_config_paths(self):
        config = Config(include=["*.py"], ignore=["secret/**"])
        self.assertTrue(config.accepts("src/a.py"))
        for path in ("secret/a.py", "src/vendor/a.py", "build/a.py", "a.js"):
            self.assertFalse(config.accepts(path))
        self.assertFalse(Config().accepts("sub/pnpm-lock.yaml"))


    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            for text in ("api_key: secret", "limits: {max_chars: 1}",
                         "limits: {nit: 6}", "paths: {include: '*.py'}", "limits: {files: true}"):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    Config.load(path)
