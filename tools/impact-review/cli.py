#!/usr/bin/env python3
"""Event → Gate → Packer → LlmClient → Mapper → Publisher."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import sys

from client import DiagnosticError, GitHub, LlmClient
from core import Config, Gate
from mapper import Mapper
from packer import Packer, git
from publisher import Publisher


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
    args = parser.parse_args()
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
    if args.pack_only:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        return 0
    review = LlmClient().review(pack)
    review.limitations.extend(pack["limitations"])
    review = Mapper.map(review, changes, config, github.pages(f"/pulls/{number}/files"))
    if args.dry_run:
        print(json.dumps(asdict(review), ensure_ascii=False, indent=2))
    else:
        print(Publisher(github, os.environ.get("IMPACT_REVIEW_BOT_LOGIN", "github-actions[bot]")).publish(pr, review))
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
