import unittest

from converge import (
    ROUND_CAP, History, apply_convergence, apply_verdicts, drop_unconfirmed,
    keep_severe_on_verification_failure, load_history, seal)
from core import Change, Finding, Review
from fake_github import FakeGitHub
from fixtures import pr, review
from publisher import Publisher


def change(path="a.py", added="return 20 / x", lines=None):
    patch = f"@@ -1 +1 @@\n-return 10 / x\n+{added}\n"
    return Change(path, patch, "", added + "\n", set(lines or {1}), set(), set(lines or {1}))


class ConvergeTests(unittest.TestCase):
    def test_drops_style_preexisting_and_quotes_missing_from_the_diff(self):
        data = Review("s", "i", ["q"], [
            Finding("nit", "名前", "好み", "a.py", 2, origin="style",
                    evidence="return 20 / x", confirmed=False),
            Finding("important", "以前から", "既存", "a.py", 2, origin="preexisting",
                    evidence="return 20 / x", confirmed=False),
            Finding("must", "根拠なし", "推測", "a.py", 2, origin="introduced",
                    evidence="この文言は差分に無い", confirmed=False),
            Finding("must", "ゼロ除算", "0で落ちる", "a.py", 2, origin="introduced",
                    evidence="return 20 / x", confirmed=False),
        ])
        result = drop_unconfirmed(data, [change()])
        self.assertEqual([item.title for item in result.findings], ["ゼロ除算"])
        self.assertTrue(any(item.startswith("unconfirmed_dropped:") for item in result.limitations))

    def test_evidence_must_quote_an_added_or_removed_line(self):
        patch = "@@ -1,2 +1,2 @@\n def calculate(x):\n-    return 10 / x\n+    return 20 / x\n"
        new = "def calculate(x):\n    return 20 / x\n"
        item = Change("a.py", patch, "", new, {1, 2}, {2}, {2})
        data = Review("s", "i", [], [
            Finding("must", "文脈だけ", "b", "a.py", 1, origin="introduced",
                    evidence="def calculate(x):", confirmed=False),
            Finding("must", "追加行", "b", "a.py", 2, origin="introduced",
                    evidence="return 20 / x", confirmed=False),
        ])
        result = drop_unconfirmed(data, [item])
        self.assertEqual([finding.title for finding in result.findings], ["追加行"])

    def test_second_round_drops_repeats_and_rephrased_nits(self):
        github = FakeGitHub()
        Publisher(github).publish(pr(), review())
        history = load_history(github.pages("/pulls/1/reviews"), "github-actions[bot]", "c" * 40)
        self.assertEqual(history.round, 2)
        self.assertTrue(history.suppress)
        self.assertEqual(history.prior[0]["title"], "境界条件")
        data = Review("s", "i", [], [
            review().findings[0],
            Finding("nit", "別の言い方", "好み", "a.py", 3),
            Finding("nit", "新しいファイル", "導入した欠落", "b.py", 4),
        ])
        result = apply_convergence(data, history, {"b.py": {4}})
        self.assertEqual([item.title for item in result.findings], ["新しいファイル"])
        outside = Review("s", "i", [], [Finding("nit", "差分外", "好み", "c.py", 8)])
        self.assertEqual(apply_convergence(outside, history, {"b.py": {4}}).findings, [])

    def test_same_head_does_not_suppress(self):
        github = FakeGitHub()
        Publisher(github).publish(pr(), review())
        history = load_history(github.pages("/pulls/1/reviews"), "github-actions[bot]", "b" * 40)
        self.assertEqual(history.round, 1)
        self.assertFalse(history.suppress)
        result = apply_convergence(review(), history, None)
        self.assertEqual(len(result.findings), 1)

    def test_same_head_at_round_cap_keeps_published_findings(self):
        github = FakeGitHub()
        published = review()
        published.round = ROUND_CAP
        Publisher(github).publish(pr(), published)
        history = load_history(github.pages("/pulls/1/reviews"), "github-actions[bot]", "b" * 40)
        self.assertEqual(history.round, ROUND_CAP)
        self.assertFalse(history.suppress)
        result = apply_convergence(review(), history, None)
        self.assertEqual([item.title for item in result.findings], ["境界条件"])
        self.assertFalse(any(item.startswith("round_cap:") for item in result.limitations))

    def test_round_cap_keeps_only_new_must_and_important(self):
        history = History(ROUND_CAP, True, "a" * 40, [])
        data = Review("s", "i", ["q"], [
            Finding("nit", "細かい", "好み", "a.py", 2),
            Finding("must", "古い行", "壊れ", "a.py", 9),
            Finding("important", "新しい行", "壊れ", "a.py", 4),
        ])
        result = apply_convergence(data, history, {"a.py": {4}})
        self.assertEqual([item.title for item in result.findings], ["新しい行"])
        self.assertTrue(any(item.startswith("round_cap:") for item in result.limitations))
        unknown = apply_convergence(Review("s", "i", [], [
            Finding("must", "場所不明", "壊れ", "a.py", 4)]), history, None)
        self.assertEqual(unknown.findings, [])
        unnumbered = apply_convergence(Review("s", "i", [], [
            Finding("must", "行なし", "壊れ", "a.py", None),
            Finding("important", "新しい行", "壊れ", "a.py", 4),
        ]), history, {"a.py": {4}})
        self.assertEqual([item.title for item in unnumbered.findings], ["新しい行"])

    def test_verdict_keeps_only_agreed_defects_and_seal_clears_empty_questions(self):
        data = Review("要約", "影響", ["境界は？"], [
            Finding("must", "残す", "理由", confirmed=False),
            Finding("nit", "捨てる", "好み", confirmed=False),
        ])
        result = seal(apply_verdicts(data, [
            {"index": 0, "keep": True, "reason": "0で例外になる"},
            {"index": 1, "keep": False, "reason": "表記の好み"},
            {"index": 2, "keep": True, "reason": "余分"},
        ]))
        self.assertEqual([item.title for item in result.findings], ["残す"])
        self.assertTrue(result.findings[0].confirmed)
        self.assertEqual(result.summary, "要約")

        empty = seal(apply_verdicts(Review("要約", "影響", ["q"], [
            Finding("nit", "捨てる", "好み", confirmed=False)]), []))
        self.assertEqual(empty.findings, [])
        self.assertEqual(empty.questions, [])
        self.assertIn("残っていません", empty.summary)
        short = apply_verdicts(Review("要約", "影響", [], [
            Finding("must", "短い理由", "落ちる", confirmed=False)]), [
            {"index": 0, "keep": True, "reason": "バグ"}])
        self.assertEqual([item.title for item in short.findings], ["短い理由"])
        self.assertTrue(short.findings[0].confirmed)

    def test_verification_failure_keeps_severe_findings_unconfirmed(self):
        data = Review("要約", "影響", ["q"], [
            Finding("must", "残す", "理由", confirmed=False),
            Finding("nit", "捨てる", "好み", confirmed=False),
        ])
        result = keep_severe_on_verification_failure(data, "unavailable")
        self.assertEqual([item.title for item in result.findings], ["残す"])
        self.assertFalse(result.findings[0].confirmed)
        self.assertTrue(any(item.startswith("verification_failed:") for item in result.limitations))
