import unittest

from approval import ApprovalPublisher, judge
from core import Finding, Review
from fake_github import FakeGitHub
from fixtures import pr


def judged(paths, findings=(), limitations=()):
    return judge(paths, Review("s", "i", [], list(findings), list(limitations)))


class ApprovalTests(unittest.TestCase):
    def test_docs_without_findings_do_not_require_a_person(self):
        decision = judged(["docs/guide.md", "README.txt"])
        self.assertFalse(decision.required)
        self.assertEqual(decision.tier, "low")

    def test_docs_with_a_remaining_nit_or_note_require_a_person(self):
        for severity in ("nit", "note"):
            decision = judged(
                ["README.md"], [Finding(severity, "残り", "本文", confirmed=True)])
            self.assertTrue(decision.required, severity)
            self.assertEqual(decision.tier, "medium", severity)
            self.assertFalse(
                any("ありません" in reason for reason in decision.reasons), decision.reasons)

    def test_secret_and_credential_names_require_a_person_in_any_case(self):
        for path in ("Secrets.md", "CREDENTIALS.md", "docs/API_SECRET.txt"):
            decision = judged([path])
            self.assertTrue(decision.required, path)
            self.assertEqual(decision.tier, "high", path)

    def test_code_without_findings_still_requires_a_person(self):
        decision = judged(["src/app.py"])
        self.assertTrue(decision.required)
        self.assertEqual(decision.tier, "medium")

    def test_must_and_sensitive_paths_are_high(self):
        must = judged(["docs/guide.md"], [Finding("must", "嘘", "手順が違う", confirmed=True)])
        self.assertTrue(must.required)
        self.assertEqual(must.tier, "high")
        for path in ("auth.py", "auth/session.py", "src/auth.py",
                     ".github/actions/foo/action.yml", ".github/workflows/ci.yml"):
            decision = judged([path])
            self.assertTrue(decision.required, path)
            self.assertEqual(decision.tier, "high", path)
        author = judged(["docs/author.md"])
        self.assertFalse(author.required)
        self.assertEqual(author.tier, "low")

    def test_verification_failure_on_docs_still_requires_a_person(self):
        decision = judged(["README.md"], limitations=["verification_failed: unavailable"])
        self.assertTrue(decision.required)
        self.assertEqual(decision.tier, "medium")

    def test_truncated_docs_still_require_a_person(self):
        decision = judged(["README.md"], limitations=["truncated"])
        self.assertTrue(decision.required)

    def test_approval_note_is_separate_and_updated_in_place(self):
        github = FakeGitHub()
        publisher = ApprovalPublisher(github)
        first = publisher.publish(pr(), judged(["src/app.py"]))
        self.assertEqual(len(github.reviews), 0)
        self.assertEqual(len(github.issue_comments), 1)
        self.assertIn("必要", github.issue_comments[0]["body"])
        self.assertTrue(github.issue_comments[0]["body"].startswith("<!-- impact-review-approval:v0 -->"))
        again = publisher.publish(pr(), judged(["src/app.py"]))
        self.assertEqual(again, first)
        self.assertEqual(len(github.issue_comments), 1)
        publisher.publish(pr(), judged(["README.md"]))
        self.assertEqual(len(github.issue_comments), 1)
        self.assertIn("不要", github.issue_comments[0]["body"])
        self.assertNotIn("必要**", github.issue_comments[0]["body"])
