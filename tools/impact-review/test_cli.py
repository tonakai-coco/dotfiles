import io
import json
import os
import unittest
import subprocess
from pathlib import Path
import yaml
from unittest.mock import patch
import cli
from fixtures import pr, review
from fake_github import FakeGitHub
from git_fixture import GitFixture

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
            self.assertEqual(len(fake.reviews), 1)
            self.assertEqual(fake.comments[1][0]["line"], 2)


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
