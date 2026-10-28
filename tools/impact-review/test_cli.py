import io
import json
import os
import unittest
import subprocess
from pathlib import Path
import yaml
from unittest.mock import patch
import cli
from core import Finding, Review
from fixtures import pr, review
from fake_github import FakeGitHub
from git_fixture import GitFixture
from packer import git
from publisher import Publisher

class CliTests(GitFixture, unittest.TestCase):
    def test_manual_workflow_resolves_selected_pr_base(self):
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/impact-review.yml'
        steps = yaml.safe_load(workflow.read_text())['jobs']['review']['steps']
        resolve = next(s for s in steps if s.get('id') == 'manual-base')
        checkout = next(s for s in steps if s.get('uses', '').startswith('actions/checkout@'))
        self.assertIn('steps.manual-base.outputs.sha', checkout['with']['ref'])
        self.assertNotIn('default_branch', checkout['with']['ref'])
        sha = 'c' * 40  # A non-default target branch SHA returned by the API.
        gh = self.root / 'gh'
        gh.write_text('#!/bin/bash\n[[ "$*" == "api repos/o/r/pulls/42 --jq .base.sha" ]] || exit 1\necho ' + sha + '\n')
        gh.chmod(0o755)
        output = self.root / 'output'
        env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                   GITHUB_REPOSITORY='o/r', PR_NUMBER='42', GITHUB_OUTPUT=str(output))
        subprocess.run(['bash', '-e', '-c', resolve['run']], env=env, check=True)
        self.assertEqual(output.read_text(), f'sha={sha}\n')

    def test_cli_draft_is_silent(self):
        fake = FakeGitHub()
        fake.pr["draft"] = True
        with patch("cli.GitHub", return_value=fake), patch("cli.Packer") as packer, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1"]), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(cli.main(), 0)
            self.assertEqual(stdout.getvalue(), "")
            packer.assert_not_called()


    def test_cli_pack_only_no_llm_no_publish(self):
        fake = FakeGitHub()
        fake.pr = pr(self.head, self.base)
        with patch("cli.GitHub", return_value=fake), patch("cli.LlmClient") as llm, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root), "--pack-only"]), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(cli.main(), 0)
            self.assertEqual(json.loads(stdout.getvalue())["version"], 0)
            llm.assert_not_called()
            self.assertFalse(any(c[0] != "GET" for c in fake.calls))


    def test_cli_full_pipeline(self):
        fake = FakeGitHub()
        fake.pr = pr(self.head, self.base)
        with patch("cli.GitHub", return_value=fake), patch("cli.LlmClient") as llm, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root)]), \
                patch("sys.stdout", new_callable=io.StringIO):
            llm.return_value.review.return_value = review()
            self.assertEqual(cli.main(), 0)
            llm.return_value.review.assert_called_once()
            llm.return_value.verify.assert_not_called()
            self.assertEqual(len(fake.reviews), 1)
            self.assertEqual(fake.comments[1][0]["line"], 2)
            self.assertIn("必要", fake.issue_comments[0]["body"])


    def test_cli_verifies_introduced_defects_and_drops_the_rest(self):
        fake = FakeGitHub()
        fake.pr = pr(self.head, self.base)
        quote = "return 20 / x"
        findings = [
            Finding("nit", "名前", "好み", "a.py", 2, origin="style", evidence=quote, confirmed=False),
            Finding("must", "ゼロ除算", "0で落ちる", "a.py", 2, origin="introduced",
                    evidence=quote, confirmed=False),
            Finding("nit", "余白", "好み", "a.py", 2, origin="introduced", evidence=quote, confirmed=False),
        ]
        with patch("cli.GitHub", return_value=fake), patch("cli.LlmClient") as llm, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root)]), \
                patch("sys.stdout", new_callable=io.StringIO):
            llm.return_value.review.return_value = Review("要約", "影響", ["質問"], findings)
            llm.return_value.verify.return_value = [
                {"index": 0, "keep": True, "reason": "0で例外になる"},
                {"index": 1, "keep": False, "reason": "表記の好み"},
            ]
            self.assertEqual(cli.main(), 0)
        body = fake.reviews[0]["body"]
        self.assertIn("ゼロ除算", body)
        self.assertNotIn("名前", body)
        self.assertNotIn("余白", body)
        self.assertEqual(len(fake.reviews), 1)
        self.assertEqual(fake.comments[1][0]["line"], 2)

    def test_cli_second_round_drops_nits_outside_the_direct_prior_diff(self):
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
        fake = FakeGitHub()
        fake.pr = pr(prior, self.base)
        Publisher(fake).publish(pr(prior, self.base), review())
        fake.pr = pr(head, self.base)
        findings = [
            Finding("nit", "古い行", "既出", "feature.py", 1, origin="introduced",
                    evidence="stable line 01", confirmed=False),
            Finding("nit", "新しい行", "追加", "feature.py", 21, origin="introduced",
                    evidence="brand-new line", confirmed=False),
        ]
        with patch("cli.GitHub", return_value=fake), patch("cli.LlmClient") as llm, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root)]), \
                patch("sys.stdout", new_callable=io.StringIO):
            llm.return_value.review.return_value = Review("要約", "影響", [], findings)
            llm.return_value.verify.return_value = [
                {"index": 0, "keep": True, "reason": "今回入った欠落"},
            ]
            self.assertEqual(cli.main(), 0)
        active = [row for row in fake.reviews if "更新済み" not in row["body"]]
        self.assertIn("新しい行", active[-1]["body"])
        self.assertNotIn("古い行", active[-1]["body"])


    def test_cli_prints_diagnostic_detail_for_safe_failures(self):
        from client import ApiConnectionError, LlmContentJsonError, ResponseJsonError
        cases = [
            (ResponseJsonError(200, 12, False), True),
            (LlmContentJsonError("str", 8, "stop", False), True),
            (TimeoutError("API request timed out after 180s"), True),
            (ApiConnectionError(), True),
            (ValueError("Invalid commit SHA"), False),
        ]
        for error, detailed in cases:
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                cli.report_failure(error)
            text = stderr.getvalue()
            self.assertIn(type(error).__name__, text)
            if detailed:
                self.assertIn(str(error), text)
            else:
                self.assertIn("see configuration and local tests", text)
                self.assertNotIn(str(error), text)
