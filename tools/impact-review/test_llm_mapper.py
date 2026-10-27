import json
import os
import socket
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
import http.client
from client import (
    ApiConnectionError, ApiError, LlmClient, LlmContentJsonError, ResponseJsonError,
    extract_json_object_text, llm_timeout_seconds, request, sanitize_finish_reason)
from core import Change, Config, Finding, Review
from mapper import Mapper
from fixtures import review

class LlmMapperTests(unittest.TestCase):
    def test_mapper_preserves_unmappable_and_limits(self):
        changes = [Change("a.py", "", "", "", {2}, set(), {2})]
        data = Review("s", "i", [], [Finding("must", "ok", "b", "a.py", 2),
                                   Finding("important", "caller", "b", "caller.py", 2),
                                   Finding("note", "invented", "b", "a.py", 999),
                                   Finding("note", "boolean", "b", "a.py", True)])
        data.findings += [Finding("nit", "n", "b") for _ in range(9)]
        data.findings += [Finding("important", "i", "b") for _ in range(15)]
        result = Mapper.map(data, changes, Config())
        self.assertEqual(sum(f.inline for f in result.findings), 1)
        self.assertEqual(sum(f.severity in ("must", "important") for f in result.findings), 10)
        self.assertEqual(sum(f.severity == "nit" for f in result.findings), 5)
        self.assertTrue(any(f.title == "caller" and not f.inline for f in result.findings))
        self.assertTrue(result.limitations)


    def test_all_bad_anchors_retained(self):
        findings = [Finding("note", "t", "b", p, n) for p, n in
                    [("a.py", 999), ("../a.py", 2), ("a.py", -1)]]
        result = Mapper.map(Review("s", "i", [], findings),
                            [Change("a.py", "", "", "", {2}, set(), set())], Config())
        self.assertEqual(len(result.findings), 3)
        self.assertFalse(any(f.inline for f in result.findings))


    def test_github_diff_is_authoritative_for_renames_and_missing_patches(self):
        changes = [Change("a.py", "", "", "", {1, 2, 3}, set(), {2})]
        for files in ([], [{"filename": "a.py"}],
                      [{"filename": "a.py", "patch": "@@ -3 +3 @@\n-old\n+new"}]):
            result = Mapper.map(review(2), changes, Config(), files)
            self.assertFalse(result.findings[0].inline)
            self.assertEqual(len(result.findings), 1)


    def test_llm_one_call_and_replaceable_endpoint(self):
        response = json.dumps({"summary": "s", "impact": "i", "questions": [], "findings": []})
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1/",
                                     "IMPACT_REVIEW_LLM_MODEL": "example-model",
                                     "IMPACT_REVIEW_LLM_API_KEY": "private"}), \
                patch("client.request", return_value={"choices": [{"message": {"content": response},
                                                                   "finish_reason": "stop"}]}) as http:
            LlmClient().review({"diff": []})
            http.assert_called_once()
            self.assertEqual(http.call_args.args[0], "https://llm.example/v1/chat/completions")
            self.assertEqual(http.call_args.args[3]["model"], "example-model")
            self.assertEqual(http.call_args.kwargs["timeout"], llm_timeout_seconds())


    def test_llm_parse_accepts_markdown_wrapped_json(self):
        payload = {"summary": "s", "impact": "i", "questions": [], "findings": []}
        wrapped = "レビュー結果です。\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        result = LlmClient.parse(wrapped, finish_reason="stop")
        self.assertEqual(result.summary, "s")

    def test_extract_json_object_text_prose_prefix(self):
        raw = '説明文\n{"summary":"s","impact":"i","questions":[],"findings":[]}'
        self.assertTrue(extract_json_object_text(raw).startswith("{"))

    def test_malformed_llm(self):
        with self.assertRaises(LlmContentJsonError) as ctx:
            LlmClient.parse("not JSON", finish_reason="stop")
        self.assertIn("message.content is not JSON", str(ctx.exception))
        self.assertEqual(ctx.exception.finish_reason, "stop")
        with self.assertRaises(LlmContentJsonError) as ctx:
            LlmClient.parse("not JSON", finish_reason="evil\npayload")
        self.assertEqual(ctx.exception.finish_reason, "invalid")
        self.assertNotIn("evil", str(ctx.exception))
        with self.assertRaises(LlmContentJsonError):
            LlmClient.parse(None, finish_reason="length")
        for raw in ("[]", '{"summary":2}',
                    '{"summary":"s","impact":"i","questions":[],"findings":[{"severity":"critical"}]}'):
            with self.assertRaises(ValueError):
                LlmClient.parse(raw)


    def test_bad_optional_llm_anchor_is_not_dropped(self):
        data = {"summary": "s", "impact": "i", "questions": [], "findings": [
            {"severity": "must", "title": "t", "body": "b", "path": [], "line": "12"}]}
        result = LlmClient.parse(json.dumps(data))
        self.assertIsNone(result.findings[0].path)
        self.assertIsNone(result.findings[0].line)


    def test_llm_timeout_seconds_default_and_bounds(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IMPACT_REVIEW_LLM_TIMEOUT_SECONDS", None)
            self.assertEqual(llm_timeout_seconds(), 420)
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_TIMEOUT_SECONDS": "240"}):
            self.assertEqual(llm_timeout_seconds(), 240)
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_TIMEOUT_SECONDS": "10"}):
            with self.assertRaises(ValueError):
                llm_timeout_seconds()
        with patch.dict(os.environ, {"IMPACT_REVIEW_LLM_TIMEOUT_SECONDS": "600"}):
            with self.assertRaises(ValueError):
                llm_timeout_seconds()


    def test_sanitize_finish_reason(self):
        self.assertIsNone(sanitize_finish_reason(None))
        self.assertEqual(sanitize_finish_reason("stop"), "stop")
        self.assertEqual(sanitize_finish_reason("length"), "length")
        self.assertEqual(
            sanitize_finish_reason("stop\nsecret payload"), "invalid")
        self.assertEqual(sanitize_finish_reason(["stop"]), "invalid")


    def test_request_non_json_body_is_response_json_error(self):
        fake_resp = MagicMock()
        fake_resp.status = 200
        fake_resp.read.return_value = b"<html>oops</html>"
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = None
        opener = MagicMock()
        opener.open.return_value = fake_resp
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ResponseJsonError) as ctx:
                request("https://llm.example/v1/chat/completions", "tok", "POST", {"x": 1})
        self.assertEqual(ctx.exception.status, 200)
        self.assertFalse(ctx.exception.starts_with_object)

        fake_resp.read.return_value = b"\xff\xfe not utf-8 {"
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ResponseJsonError) as ctx:
                request("https://llm.example/v1/chat/completions", "tok", "POST", {"x": 1})
        self.assertEqual(ctx.exception.status, 200)
        self.assertFalse(ctx.exception.starts_with_object)


    def test_request_timeout_becomes_timeout_error(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError()
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(TimeoutError) as ctx:
                request("https://llm.example/v1/x", "tok", timeout=180)
        self.assertIn("timed out after 180s", str(ctx.exception))

        opener.open.side_effect = urllib.error.URLError(socket.timeout("timed out"))
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(TimeoutError):
                request("https://llm.example/v1/x", "tok", timeout=90)

    def test_request_remote_disconnected_omits_peer_details(self):
        opener = MagicMock()
        opener.open.side_effect = http.client.RemoteDisconnected(
            "Remote end closed connection without response from secret-host")
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ApiConnectionError) as ctx:
                request("https://llm.example/v1/x", "tok")
        self.assertNotIn("secret-host", str(ctx.exception))
        self.assertIn("connection failed", str(ctx.exception))

        opener.open.side_effect = urllib.error.URLError(OSError("reset by secret-host"))
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ApiConnectionError) as ctx:
                request("https://llm.example/v1/x", "tok")
        self.assertNotIn("secret-host", str(ctx.exception))

    def test_llm_retries_once_when_the_connection_drops(self):
        response = json.dumps({"summary": "s", "impact": "i", "questions": [], "findings": []})
        ok = {"choices": [{"message": {"content": response}, "finish_reason": "stop"}]}
        env = {"IMPACT_REVIEW_LLM_BASE_URL": "https://llm.example/v1",
               "IMPACT_REVIEW_LLM_MODEL": "example-model",
               "IMPACT_REVIEW_LLM_API_KEY": "private"}
        with patch.dict(os.environ, env), \
                patch("client.request", side_effect=[ApiConnectionError(), ok]) as http:
            LlmClient().review({"diff": []})
        self.assertEqual(http.call_count, 2)

        with patch.dict(os.environ, env), \
                patch("client.request", side_effect=ApiConnectionError()) as http:
            with self.assertRaises(ApiConnectionError):
                LlmClient().review({"diff": []})
        self.assertEqual(http.call_count, 2)

        with patch.dict(os.environ, env), \
                patch("client.request", side_effect=ApiError(502)) as http:
            with self.assertRaises(ApiError):
                LlmClient().review({"diff": []})
        self.assertEqual(http.call_count, 1)

        with patch.dict(os.environ, env), \
                patch("client.request", side_effect=TimeoutError("API request timed out after 420s")) as http:
            with self.assertRaises(TimeoutError):
                LlmClient().review({"diff": []})
        self.assertEqual(http.call_count, 1)
