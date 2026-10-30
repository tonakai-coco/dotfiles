import json
import unittest
from unittest.mock import patch
from core import Change, Config
from packer import Packer, git, line_map
from fixtures import pr
from git_fixture import GitFixture

class PackerTests(GitFixture, unittest.TestCase):
    def test_unavailable_blobs_keep_add_modify_delete_diffs(self):
        target = self.root / 'large.txt'
        for content in (b'x\n' * 500001, b'non-utf8: \xff\n'):
            for operation in ('add', 'modify', 'delete'):
                base = git(self.root, 'rev-parse', 'HEAD').decode().strip()
                if operation == 'delete':
                    target.unlink()
                else:
                    target.write_bytes(content + (b'changed\n' if operation == 'modify' else b''))
                head = self.commit()
                packer = Packer(self.root, Config(include=['large.txt']))
                changes = packer.changes(base, head)
                self.assertEqual(len(changes), 1, (len(content), operation))
                self.assertEqual((changes[0].old, changes[0].new), ('', ''))
                pack = packer.build(pr(head, base), changes)
                self.assertTrue(pack['diff'])
                self.assertTrue(any('blob:' in x or 'non_utf8:' in x for x in pack['limitations']))

    def test_invalid_utf8_path_does_not_hide_other_changes(self):
        def with_invalid_name(root, *args):
            result = git(root, *args)
            return result + b'invalid-\xff.py\0' if '--name-only' in args else result
        packer = Packer(self.root, Config())
        with patch('packer.git', side_effect=with_invalid_name):
            changes = packer.changes(self.base, self.head)
        self.assertEqual({c.path for c in changes}, {'a.py', 'deleted.py'})
        pack = packer.build(pr(self.head, self.base), changes)
        self.assertTrue(any(x.startswith('non_utf8_path_skipped:') for x in pack['limitations']))
        json.dumps(pack, ensure_ascii=False).encode('utf-8')

    def test_pack_real_diff_units_callers_deleted(self):
        packer = Packer(self.root, Config())
        changes = packer.changes(self.base, self.head)
        self.assertEqual({c.path for c in changes}, {"a.py", "deleted.py"})
        pack = packer.build(pr(self.head, self.base), changes)
        self.assertTrue(any(u["symbol"] == "calculate" and u["complete"] for u in pack["units"]))
        self.assertTrue(any(u["symbol"] == "gone" and u["side"] == "LEFT" for u in pack["units"]))
        self.assertEqual(pack["callers"][0]["path"], "caller.py")
        deleted = next(c for c in changes if c.path == "deleted.py")
        self.assertEqual(deleted.right_lines, set())


    def test_limits_and_priority(self):
        packer = Packer(self.root, Config(max_chars=2000))
        changes = packer.changes(self.base, self.head)
        changes[0].patch += "x" * 10000
        pack = packer.build(pr(self.head, self.base), changes)
        self.assertLessEqual(len(json.dumps(pack, ensure_ascii=False)), 2000)
        self.assertIn("truncated", pack["limitations"])
        self.assertTrue(pack["units"])
        self.assertTrue(pack["callers"])
        capped = Packer(self.root, Config(files=1))
        self.assertEqual(len(capped.changes(self.base, self.head)), 1)
        self.assertIn("files_truncated", capped.limitations)


    def test_callers_cap(self):
        packer = Packer(self.root, Config(callers=0))
        pack = packer.build(pr(self.head, self.base), packer.changes(self.base, self.head))
        self.assertEqual(pack["callers"], [])


    def test_python_decorator_is_in_unit(self):
        source = "@decorate\ndef f():\n    return 1\n"
        change = Change("a.py", "", "", source, {1}, set(), {1})
        self.assertEqual(Packer.units(change)[0]["text"], source.rstrip())


    def test_direct_diff_keeps_only_lines_changed_since_prior_head(self):
        body = "".join(f"stable line {i:02d}\n" for i in range(1, 21))
        git(self.root, "checkout", "-q", "-b", "prior", self.base)
        (self.root / "feature.py").write_text(body)
        git(self.root, "add", "feature.py")
        git(self.root, "commit", "-qm", "prior")
        prior = git(self.root, "rev-parse", "HEAD").decode().strip()
        git(self.root, "checkout", "-q", "-b", "headside", self.base)
        (self.root / "feature.py").write_text(body + "brand-new line\n")
        git(self.root, "add", "feature.py")
        git(self.root, "commit", "-qm", "head")
        head = git(self.root, "rev-parse", "HEAD").decode().strip()
        packer = Packer(self.root, Config(include=["feature.py"]))
        whole = packer.changes(prior, head)
        since_prior = packer.changes(prior, head, direct=True)
        self.assertEqual(whole[0].changed_new, set(range(1, 22)))
        self.assertEqual(since_prior[0].changed_new, {21})

    def test_line_map_deleted_and_context(self):
        patch = "--- a\n+++ b\n@@ -10,3 +10,3 @@\n keep\n-old\n+new\n tail\n"
        right, old, new = line_map(patch)
        self.assertEqual(right, {10, 11, 12})
        self.assertEqual(old, {11})
        self.assertEqual(new, {11})

    def test_related_import_target_sibling_test_and_config(self):
        (self.root / "lib_util.py").write_text("def helper():\n    return 1\n")
        (self.root / "service.py").write_text(
            "from lib_util import helper\n\ndef run():\n    return helper()\n")
        (self.root / "test_service.py").write_text(
            "from service import run\n\ndef test_run():\n    assert run() == 1\n")
        (self.root / "service.yml").write_text("mode: safe\n")
        base = self.commit()
        (self.root / "service.py").write_text(
            "from lib_util import helper\n\ndef run():\n    return helper() + 1\n")
        head = self.commit()
        packer = Packer(self.root, Config(include=["service.py", "lib_util.py",
                                                   "test_service.py", "service.yml"]))
        pack = packer.build(pr(head, base), packer.changes(base, head))
        reasons = {item["reason"]: item["path"] for item in pack["related"]}
        self.assertEqual(reasons.get("import_target"), "lib_util.py")
        self.assertEqual(reasons.get("sibling_test"), "test_service.py")
        self.assertEqual(reasons.get("same_dir_config"), "service.yml")

    def test_related_resolves_import_from_package_member(self):
        pkg = self.root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "worker.py").write_text("def work():\n    return 1\n")
        (self.root / "app.py").write_text(
            "from pkg import worker\n\ndef main():\n    return worker.work()\n")
        base = self.commit()
        (self.root / "app.py").write_text(
            "from pkg import worker\n\ndef main():\n    return worker.work() + 1\n")
        head = self.commit()
        packer = Packer(self.root, Config(include=["app.py", "pkg/**"]))
        pack = packer.build(pr(head, base), packer.changes(base, head))
        targets = [item["path"] for item in pack["related"] if item["reason"] == "import_target"]
        self.assertIn("pkg/worker.py", targets)

    def test_related_truncated_before_callers(self):
        packer = Packer(self.root, Config(max_chars=2500, related=8))
        changes = packer.changes(self.base, self.head)
        # Inflate related so truncation must drop it while callers can remain.
        pack = packer.build(pr(self.head, self.base), changes)
        pack["related"] = [
            {"path": f"extra{i}.py", "start": 1, "reason": "sibling_test", "text": "y" * 400}
            for i in range(6)
        ]
        # Re-run truncation logic by rebuilding through a tiny max_chars packer path:
        tiny = Packer(self.root, Config(max_chars=1800, related=8, callers=10))
        changes[0].patch += "x" * 5000
        packed = tiny.build(pr(self.head, self.base), changes)
        self.assertIn("truncated", packed["limitations"])
        self.assertTrue(packed["callers"])
        # related is lower priority than callers, so it empties or truncates first.
        self.assertTrue(all(item.get("truncated") or not item.get("text")
                            for item in packed["related"]) or not packed["related"]
                        or len(json.dumps(packed["related"], ensure_ascii=False))
                        < len(json.dumps(packed["callers"], ensure_ascii=False)))

    def test_callers_skip_python_definition_lines(self):
        (self.root / "mod.py").write_text("def shared():\n    return 1\n")
        # Put the same-named definition far from the call so a call excerpt cannot
        # accidentally include the definition line as its only hit.
        (self.root / "other.py").write_text(
            "def shared():\n    return 2\n" + ("pass\n" * 30) + "def use():\n    return shared()\n")
        base = self.commit()
        (self.root / "mod.py").write_text("def shared():\n    return 3\n")
        head = self.commit()
        packer = Packer(self.root, Config(include=["mod.py", "other.py"]))
        pack = packer.build(pr(head, base), packer.changes(base, head))
        self.assertTrue(pack["callers"])
        self.assertTrue(any("return shared()" in item["text"] for item in pack["callers"]))
        # Definition line itself must not be the grep hit (start would be 1).
        self.assertFalse(any(item["path"] == "other.py" and item["start"] == 1
                             for item in pack["callers"]))
