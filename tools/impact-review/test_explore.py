import io
import json
import os
import time
import unittest
from unittest.mock import patch

import cli
from core import Config
from explore import ExploreBudget, ExploreTools
from fake_github import FakeGitHub
from fixtures import pr, review
from git_fixture import GitFixture


class ExploreToolTests(GitFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.tools = ExploreTools(self.root, Config(), self.base, self.head)

    def test_read_path_and_reject_ignored(self):
        text = self.tools.dispatch("read_path", {"path": "a.py", "start_line": 1, "max_lines": 10})
        self.assertIn("def calculate", text)
        denied = self.tools.dispatch("read_path", {"path": "package-lock.json"})
        self.assertEqual(denied, "error: path not allowed")
        traversal = self.tools.dispatch("read_path", {"path": "../a.py"})
        self.assertEqual(traversal, "error: path not allowed")

    def test_unknown_tool_and_bad_ref(self):
        self.assertEqual(self.tools.dispatch("shell", {"cmd": "ls"}), "error: unknown tool")
        self.assertEqual(self.tools.dispatch("git_show", {"path": "a.py", "ref": "HEAD"}),
                         "error: ref must be base or head")

    def test_search_symbol_and_grep(self):
        hits = self.tools.dispatch("search_symbol", {"symbol": "calculate", "max_hits": 5})
        self.assertIn("caller.py", hits)
        grepped = self.tools.dispatch("grep", {"pattern": "return 20", "max_hits": 5})
        self.assertIn("a.py", grepped)

    def test_budget_records_and_exhausts(self):
        budget = ExploreBudget.from_values(1, 20, 30)
        first = budget.record("x" * 50)
        self.assertIn("explore_chars_truncated", first)
        self.assertTrue(budget.exhausted)
        self.assertFalse(budget.can_call())
        self.assertIn("explore_budget_exhausted", budget.limitations())


class ExploreCliTests(GitFixture, unittest.TestCase):
    def test_pack_only_with_explore_errors(self):
        fake = FakeGitHub()
        fake.pr = pr(self.head, self.base)
        with patch("cli.GitHub", return_value=fake), \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root),
                                   "--pack-only", "--explore"]), \
                patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as raised:
                cli.main()
            self.assertNotEqual(raised.exception.code, 0)

    def test_explore_dry_run_uses_review_explore(self):
        fake = FakeGitHub()
        fake.pr = pr(self.head, self.base)
        with patch("cli.GitHub", return_value=fake), patch("cli.LlmClient") as llm, \
                patch.dict(os.environ, {"GITHUB_TOKEN": "test"}), \
                patch("sys.argv", ["cli", "--repo", "o/r", "--pr", "1", "--root", str(self.root),
                                   "--explore", "--explore-max-calls", "0", "--dry-run"]), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            llm.return_value.review_explore.return_value = review()
            self.assertEqual(cli.main(), 0)
            llm.return_value.review_explore.assert_called_once()
            llm.return_value.review.assert_not_called()
            self.assertEqual(json.loads(stdout.getvalue())["summary"], review().summary)
            self.assertFalse(fake.reviews)

    def test_explore_loop_runs_tool_then_json(self):
        from client import LlmClient
        tools = ExploreTools(self.root, Config(), self.base, self.head)
        budget = ExploreBudget.from_values(2, 10_000, 60)
        empty = json.dumps({"summary": "s", "impact": "i", "questions": [], "findings": []})
        tool_response = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "1",
                        "type": "function",
                        "function": {
                            "name": "read_path",
                            "arguments": json.dumps({"path": "a.py"}),
                        },
                    }],
                },
            }]
        }
        final = {"choices": [{"finish_reason": "stop", "message": {"content": empty}}]}
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1",
                                     "IMPACT_REVIEW_LLM_MODEL": "m",
                                     "IMPACT_REVIEW_LLM_API_KEY": "k"}), \
                patch("client.request", side_effect=[tool_response, final]) as http:
            result = LlmClient().review_explore({"diff": []}, tools, budget)
        self.assertEqual(result.summary, "s")
        self.assertEqual(budget.calls, 1)
        self.assertEqual(http.call_count, 2)
        self.assertTrue(any("explore_calls:" in row for row in result.limitations))

    def test_explore_replies_to_all_tool_calls_when_budget_runs_out(self):
        from client import LlmClient
        tools = ExploreTools(self.root, Config(), self.base, self.head)
        budget = ExploreBudget.from_values(1, 10_000, 60)
        empty = json.dumps({"summary": "s", "impact": "i", "questions": [], "findings": []})
        tool_response = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "a", "type": "function",
                         "function": {"name": "read_path",
                                      "arguments": json.dumps({"path": "a.py"})}},
                        {"id": "b", "type": "function",
                         "function": {"name": "read_path",
                                      "arguments": json.dumps({"path": "caller.py"})}},
                        "not-a-dict",
                    ],
                },
            }]
        }
        final = {"choices": [{"finish_reason": "stop", "message": {"content": empty}}]}
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1",
                                     "IMPACT_REVIEW_LLM_MODEL": "m",
                                     "IMPACT_REVIEW_LLM_API_KEY": "k"}), \
                patch("client.request", side_effect=[tool_response, final]) as http:
            result = LlmClient().review_explore({"diff": []}, tools, budget)
        second = http.call_args_list[1].args[3]["messages"]
        tool_replies = [m for m in second if m.get("role") == "tool"]
        self.assertEqual({m["tool_call_id"] for m in tool_replies}, {"a", "b"})
        self.assertEqual(sum(1 for m in tool_replies if "budget exhausted" in m["content"]), 1)
        self.assertEqual(budget.calls, 1)
        self.assertTrue(budget.exhausted)
        self.assertEqual(result.summary, "s")

    def test_explore_completion_timeout_stays_inside_wall_clock(self):
        from client import LlmClient
        tools = ExploreTools(self.root, Config(), self.base, self.head)
        budget = ExploreBudget.from_values(0, 10_000, 60)
        budget.started = time.monotonic() - 55  # ~5s remaining
        empty = json.dumps({"summary": "s", "impact": "i", "questions": [], "findings": []})
        final = {"choices": [{"finish_reason": "stop", "message": {"content": empty}}]}
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1",
                                     "IMPACT_REVIEW_LLM_MODEL": "m",
                                     "IMPACT_REVIEW_LLM_API_KEY": "k",
                                     "IMPACT_REVIEW_LLM_TIMEOUT_SECONDS": "420"}), \
                patch("client.request", return_value=final) as http:
            LlmClient().review_explore({"diff": []}, tools, budget)
        self.assertLessEqual(http.call_args.kwargs["timeout"], 5)
        self.assertGreaterEqual(http.call_args.kwargs["timeout"], 1)

    def test_explore_raises_when_wall_clock_already_exhausted(self):
        from client import LlmClient
        tools = ExploreTools(self.root, Config(), self.base, self.head)
        budget = ExploreBudget.from_values(8, 10_000, 30)
        budget.started = time.monotonic() - 31
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1",
                                     "IMPACT_REVIEW_LLM_MODEL": "m",
                                     "IMPACT_REVIEW_LLM_API_KEY": "k"}), \
                patch("client.request") as http:
            with self.assertRaises(TimeoutError):
                LlmClient().review_explore({"diff": []}, tools, budget)
            http.assert_not_called()
