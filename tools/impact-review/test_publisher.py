import unittest
from client import ApiError
from core import Finding, Review
from fixtures import pr, review
from fake_github import FakeGitHub
from publisher import MARKER, Publisher, body


class PublisherTests(unittest.TestCase):
    def test_same_head_same_anchors_updates_text_without_new_review(self):
        github = FakeGitHub()
        publisher = Publisher(github)
        publisher.publish(pr(), review())
        changed = review()
        changed.summary = "Rephrased summary"
        changed.findings[0].body = "Rephrased finding"
        publisher.publish(pr(), changed)
        self.assertEqual(len(github.reviews), 1)
        self.assertIn("Rephrased summary", github.reviews[0]["body"])
        self.assertIn("Rephrased finding", github.comments[1][0]["body"])
        publisher.publish(pr(), changed)
        self.assertEqual(len(github.reviews), 1)

    def test_idempotent_and_replacement(self):
        github = FakeGitHub()
        publisher = Publisher(github)
        first = publisher.publish(pr(), review())
        self.assertEqual(publisher.publish(pr(), review()), first)
        self.assertEqual(len(github.reviews), 1)
        github.pr = pr("c" * 40)
        publisher.publish(github.pr, review())
        self.assertEqual(len(github.reviews), 2)
        self.assertEqual(github.comments[1], [])
        self.assertIn("更新済み", github.reviews[0]["body"])
        self.assertEqual(len(github.comments[2]), 1)
        for method, _, payload in github.calls:
            if method == "POST":
                self.assertEqual(payload["event"], "COMMENT")
                self.assertEqual(payload["comments"][0]["side"], "RIGHT")

    def test_publication_failure_keeps_old(self):
        github = FakeGitHub()
        publisher = Publisher(github)
        publisher.publish(pr(), review())
        github.fail_create = True
        with self.assertRaises(ApiError):
            publisher.publish(pr(), review(3))
        self.assertTrue(github.comments[1])
        self.assertNotIn("更新済み", github.reviews[0]["body"])

    def test_cleanup_failure_resumes_without_duplicate(self):
        github = FakeGitHub()
        publisher = Publisher(github)
        publisher.publish(pr(), review())
        github.fail_delete = True
        with self.assertRaises(ApiError):
            publisher.publish(pr(), review(3))
        github.fail_delete = False
        publisher.publish(pr(), review(3))
        self.assertEqual(len(github.reviews), 2)
        self.assertEqual(github.comments[1], [])

    def test_does_not_touch_foreign_review(self):
        github = FakeGitHub()
        Publisher(github).publish(pr(), review())
        github.reviews[0]["user"] = {"login": "human"}
        Publisher(github).publish(pr(), review(3))
        self.assertTrue(github.comments[1])

    def test_stale_or_draft_pr_no_post(self):
        for change in ({"head": {"sha": "new"}}, {"draft": True}, {"state": "closed"},
                       {"base": {"sha": "new-base"}}):
            github = FakeGitHub()
            github.pr.update(change)
            self.assertTrue(Publisher(github).publish(pr(), review()).startswith("skipped"))
            self.assertEqual(github.reviews, [])

    def test_summary_labels_and_sanitization(self):
        data = Review("<!-- impact-review:v0 --> @user", "impact", [], [
            Finding(severity, "title", "body") for severity in ("must", "important", "nit", "note")])
        content = body(data)
        for label in ("🔴 [MUST]", "🟠 [IMPORTANT]", "🟢 [NIT]", "⚪ [NOTE]"):
            self.assertGreaterEqual(content.count(label), 2)
        self.assertIn("summary_only", content)
        self.assertNotIn(MARKER, content)
        self.assertNotIn("@user", content)
