"""Replace active review content; preserve only GitHub's unavoidable review history."""
import hashlib
import json

from core import LABELS, Review


MARKER = "<!-- impact-review:v0 -->"


def safe(text: str) -> str:
    # Prevent model output from forging our markers or issuing @mentions.
    return text.replace("<!--", "&lt;!--").replace("@", "@\u200b")


def body(review: Review) -> str:
    counts = {name: sum(finding.severity == name for finding in review.findings) for name in LABELS}
    count_line = "残す指摘: " + " / ".join(f"{name} {counts[name]}" for name in LABELS)
    if not review.findings:
        count_line += "。直すものはありません。"
    parts = ["## Impact Review", " / ".join(LABELS.values()),
             f"ラウンド {review.round}", count_line,
             "### 要約", safe(review.summary), "### 影響", safe(review.impact), "### 指摘一覧"]
    for finding in review.findings:
        location = "inline" if finding.inline else "summary_only"
        anchor = f"{finding.path or '(path unspecified)'}:{finding.line or '?'}"
        symbol = f" / {finding.symbol}" if finding.symbol else ""
        parts.append(f"- {safe(finding.text())}\n\n  ({location}: {safe(anchor + symbol)})")
    if not review.findings:
        parts.append("指摘なし")
    parts += ["### 質問", *[f"- {safe(q)}" for q in review.questions],
              "### 制限", "自動レビューです。テストの実行結果ではありません。",
              *[f"- {safe(limit)}" for limit in review.limitations]]
    return "\n\n".join(parts)


class Publisher:
    def __init__(self, github, login="github-actions[bot]"):
        self.github, self.login = github, login

    def publish(self, pr: dict, review: Review):
        number, head = pr["number"], pr["head"]["sha"]
        path = f"/pulls/{number}"
        # Do not publish stale output if another push/draft transition occurred during inference.
        current = self.github.call("GET", path)
        if (current["head"]["sha"] != head or current["base"]["sha"] != pr["base"]["sha"]
                or current.get("draft") or current.get("state") != "open"):
            return "skipped: PR changed during review"
        previous = [r for r in self.github.pages(path + "/reviews")
                    if r["user"]["login"] == self.login and r.get("body", "").startswith(MARKER)
                    and r["state"] == "COMMENTED"]
        comments = [dict(path=f.path, line=f.line, side="RIGHT", body=safe(f.text()))
                    for f in review.findings if f.inline]
        content = body(review)
        digest = hashlib.sha256(json.dumps([pr["base"]["sha"], head, content, comments],
                                          ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        stamp = f"<!-- result:{digest} -->"
        from converge import state_comment
        new_body = f"{MARKER}\n{stamp}\n{state_comment(review.round, review.findings)}\n{content}"
        existing = next((r for r in previous if stamp in r["body"]), None)
        if existing:
            active = existing
        else:
            active = None
            # Same commit and same anchors: update text in place, even if LLM wording differs.
            same_head = next((r for r in reversed(previous) if r.get("commit_id") == head), None)
            if same_head:
                old_comments = self.github.pages(f"{path}/reviews/{same_head['id']}/comments")
                old_comments = [c for c in old_comments if c["user"]["login"] == self.login
                                and not c.get("in_reply_to_id")]
                def anchor(c):
                    return c["path"], c.get("line") or -1, c.get("side", "RIGHT")
                old_comments.sort(key=anchor)
                ordered = sorted(comments, key=anchor)
                if [anchor(c) for c in old_comments] == [anchor(c) for c in ordered]:
                    for old_comment, comment in zip(old_comments, ordered):
                        if old_comment["body"] != comment["body"]:
                            self.github.call("PATCH", f"/pulls/comments/{old_comment['id']}",
                                             {"body": comment["body"]})
                    self.github.call("PUT", f"{path}/reviews/{same_head['id']}", {"body": new_body})
                    active = same_head
            if active is None:
                # Create first. On HTTP/validation failure the previous review remains intact.
                active = self.github.call("POST", path + "/reviews", {
                    "commit_id": head, "event": "COMMENT", "body": new_body, "comments": comments})
        # Retrying after partial cleanup reuses the stamped review and resumes cleanup.
        for old in previous:
            if old["id"] == active["id"]:
                continue
            for comment in self.github.pages(f"{path}/reviews/{old['id']}/comments"):
                if comment["user"]["login"] == self.login:
                    self.github.call("DELETE", f"/pulls/comments/{comment['id']}")
            replacement = f"{MARKER}\n更新済み。最新レビュー: {active['html_url']}"
            if old["body"] != replacement:
                self.github.call("PUT", f"{path}/reviews/{old['id']}", {"body": replacement})
        return active["html_url"]
