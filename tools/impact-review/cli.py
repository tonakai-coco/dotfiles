#!/usr/bin/env python3
"""Event → Gate → Packer → LlmClient → converge → Mapper → verify → Publisher → Approval."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from approval import ApprovalPublisher, judge
from client import DiagnosticError, GitHub, LlmClient
from converge import (
    apply_convergence, apply_verdicts, drop_unconfirmed, keep_severe_on_verification_failure,
    load_history, seal, verification_items)
from core import Config, Gate
from explore import ExploreBudget, ExploreTools
from mapper import Mapper
from packer import Packer, git
from publisher import Publisher


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--pr", type=int)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(".impact-review.yml"))
    parser.add_argument("--event", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--fetch", action="store_true", help="Fetch PR base/head into local object store")
    parser.add_argument("--pack-only", action="store_true", help="Print pack without LLM or writes")
    parser.add_argument("--dry-run", action="store_true", help="Call LLM but do not publish")
    parser.add_argument("--explore", action="store_true", default=None,
                        help="Enable bounded read-only tool-use explore loop")
    parser.add_argument("--explore-max-calls", type=int)
    parser.add_argument("--explore-max-chars", type=int)
    parser.add_argument("--explore-timeout-seconds", type=int)
    args = parser.parse_args()
    explore = bool(args.explore) if args.explore is not None else _env_flag("IMPACT_REVIEW_EXPLORE")
    if args.pack_only and explore:
        parser.error("--pack-only and --explore cannot be combined")
    event = json.loads(args.event.read_text()) if args.event else {}
    number = args.pr or event.get("pull_request", {}).get("number")
    if not number or number < 1 or not args.repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        parser.error("--repo owner/repo and positive --pr (or PR event) are required")
    github = GitHub(args.repo, os.environ["GITHUB_TOKEN"])
    pr = github.call("GET", f"/pulls/{number}")
    if not Gate.eligible(pr, args.repo):
        return 0
    config = Config.load(args.config)
    if args.fetch:
        for ref in (pr["base"]["sha"], pr["head"]["sha"]):
            if not re.fullmatch(r"[0-9a-f]{40,64}", ref):
                raise ValueError("Invalid commit SHA")
            git(args.root, "fetch", "--no-tags", "origin", ref)
    packer = Packer(args.root, config)
    changes = packer.changes(pr["base"]["sha"], pr["head"]["sha"])
    if not Gate.has_targets(changes):
        return 0
    pack = packer.build(pr, changes)
    bot = os.environ.get("IMPACT_REVIEW_BOT_LOGIN", "github-actions[bot]")
    history = load_history(github.pages(f"/pulls/{number}/reviews"), bot, pr["head"]["sha"])
    delta = None
    if history.suppress and history.prior_head and re.fullmatch(r"[0-9a-f]{40,64}", history.prior_head):
        try:
            if args.fetch and history.prior_head not in (pr["base"]["sha"], pr["head"]["sha"]):
                git(args.root, "fetch", "--no-tags", "origin", history.prior_head)
            delta = {change.path: set(change.changed_new)
                     for change in packer.changes(
                         history.prior_head, pr["head"]["sha"], direct=True)}
        except (subprocess.CalledProcessError, OSError, ValueError):
            delta = None
    pack["review_round"] = history.round
    pack["prior_findings"] = [
        {"path": item.get("path"), "line": item.get("line"), "severity": item.get("severity"),
         "title": (item.get("title") or "")[:80]}
        for item in (history.prior if history.suppress else [])[:20]]
    if delta is not None:
        pack["delta_paths"] = sorted(delta)
    if args.pack_only:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        return 0
    client = LlmClient()
    if explore:
        budget = ExploreBudget.from_values(
            args.explore_max_calls if args.explore_max_calls is not None
            else _env_int("IMPACT_REVIEW_EXPLORE_MAX_CALLS", 8),
            args.explore_max_chars if args.explore_max_chars is not None
            else _env_int("IMPACT_REVIEW_EXPLORE_MAX_CHARS", 40_000),
            args.explore_timeout_seconds if args.explore_timeout_seconds is not None
            else _env_int("IMPACT_REVIEW_EXPLORE_TIMEOUT_SECONDS", 120),
        )
        tools = ExploreTools(args.root, config, pr["base"]["sha"], pr["head"]["sha"])
        review = client.review_explore(pack, tools, budget)
    else:
        review = client.review(pack)
    review.limitations.extend(pack["limitations"])
    if history.suppress and history.prior_head and delta is None:
        review.limitations.append("delta_unavailable")
    review.round = history.round
    review = drop_unconfirmed(review, changes)
    review = apply_convergence(review, history, delta)
    review = Mapper.map(review, changes, config, github.pages(f"/pulls/{number}/files"))
    items = verification_items(review, changes)
    if items:
        try:
            review = apply_verdicts(review, client.verify(items))
        except (DiagnosticError, TimeoutError, ValueError):
            review = keep_severe_on_verification_failure(review, "unavailable")
    review = seal(review)
    approval = judge([change.path for change in changes], review)
    if args.dry_run:
        payload = asdict(review)
        payload["approval"] = asdict(approval)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    published = Publisher(github, bot).publish(pr, review)
    print(published)
    if published.startswith("skipped"):
        return 0
    print(ApprovalPublisher(github, bot).publish(pr, approval))
    return 0


def report_failure(error: BaseException) -> None:
    # No payloads, credentials, URL query strings, or tracebacks in CI logs.
    # DiagnosticError / TimeoutError messages are intentionally safe metadata only.
    if isinstance(error, DiagnosticError) or type(error) is TimeoutError:
        print(f"Impact Review failed ({type(error).__name__}): {error}", file=sys.stderr)
    else:
        print(f"Impact Review failed ({type(error).__name__}); see configuration and local tests.", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        report_failure(error)
        sys.exit(1)
