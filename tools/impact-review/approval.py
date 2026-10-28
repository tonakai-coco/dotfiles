"""Decide whether a person should approve, separately from the review comment."""
from dataclasses import dataclass
from fnmatch import fnmatchcase

from core import Review
from publisher import safe


MARKER = "<!-- impact-review-approval:v0 -->"
_LOW_RISK = (".md", ".txt", ".rst", ".adoc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
_SENSITIVE = (
    ".github/workflows/*", ".github/actions/*", "*secret*", "*credential*",
    "*/auth.py", "*/auth/*", "*authentication*", "*authorization*", "*/security/*",
)
_CASEFOLD = {"*secret*", "*credential*"}
_TIER = {"high": "高", "medium": "中", "low": "低"}


@dataclass
class Approval:
    required: bool
    tier: str
    reasons: list[str]


def _matches(path: str, pattern: str) -> bool:
    # `*/auth.py` must also match a repository-root `auth.py`.
    patterns = [pattern, pattern[2:]] if pattern.startswith("*/") else [pattern]
    parts = path.split("/")
    suffixes = ["/".join(parts[i:]) for i in range(len(parts))]
    if pattern in _CASEFOLD:
        suffixes = [suffix.casefold() for suffix in suffixes]
        patterns = [candidate.casefold() for candidate in patterns]
    return any(fnmatchcase(suffix, candidate) for suffix in suffixes for candidate in patterns)


def judge(paths: list[str], review: Review) -> Approval:
    sensitive = [path for path in paths if any(_matches(path, pattern) for pattern in _SENSITIVE)]
    code = [path for path in paths if not path.lower().endswith(_LOW_RISK)]
    must = sum(finding.severity == "must" for finding in review.findings)
    important = sum(finding.severity == "important" for finding in review.findings)
    minor = sum(finding.severity in ("nit", "note") for finding in review.findings)
    hard_gaps = [item for item in review.limitations if item.startswith(("truncated", "files_truncated"))]
    soft_gaps = [item for item in review.limitations
                 if item.startswith(("verification_failed", "delta_unavailable"))]
    reasons = []
    if sensitive:
        reasons.append("人の確認を残すパスを含みます: " + ", ".join(sensitive[:5]))
    if must:
        reasons.append(f"今回の変更で入った must 指摘が {must} 件残っています")
    if important:
        reasons.append(f"important 指摘が {important} 件残っています")
    if minor:
        reasons.append(f"nit または note が {minor} 件残っています")
    if hard_gaps or soft_gaps:
        reasons.append("レビューの被覆が欠けているため、指摘がないことだけでは判断できません")
    if code and not (sensitive or must or important or minor or hard_gaps or soft_gaps):
        reasons.append("コードの変更は、指摘が残っていなくても人の承認を必要とします")
    required = bool(sensitive or must or important or minor or code or hard_gaps or soft_gaps)
    high = bool(sensitive or must or (code and (hard_gaps or soft_gaps)))
    if not required:
        reasons.append("文書などの低リスクな変更だけで、残った指摘も被覆の欠けもありません")
    tier = "high" if required and high else "medium" if required else "low"
    return Approval(required, tier, reasons)


def approval_body(approval: Approval, head: str) -> str:
    need = "必要" if approval.required else "不要"
    lines = [
        "## 人の承認判定",
        f"**{need}**（リスク: {_TIER[approval.tier]}）",
        f"対象コミット: `{head}`",
        "この判定はレビュー指摘とは別のコメントです。マージ可否はブランチ保護の設定に従います。",
        *(f"- {safe(reason)}" for reason in approval.reasons),
    ]
    return "\n\n".join(lines)


class ApprovalPublisher:
    def __init__(self, github, login="github-actions[bot]"):
        self.github, self.login = github, login

    def publish(self, pr: dict, approval: Approval) -> str:
        number, head = pr["number"], pr["head"]["sha"]
        current = self.github.call("GET", f"/pulls/{number}")
        if (current["head"]["sha"] != head or current["base"]["sha"] != pr["base"]["sha"]
                or current.get("draft") or current.get("state") != "open"):
            return "skipped: PR changed before approval note"
        body = f"{MARKER}\n{approval_body(approval, head)}"
        comments = [row for row in self.github.pages(f"/issues/{number}/comments")
                    if (row.get("user") or {}).get("login") == self.login
                    and str(row.get("body") or "").startswith(MARKER)]
        if not comments:
            created = self.github.call("POST", f"/issues/{number}/comments", {"body": body})
            return created.get("html_url") or "approval:created"
        latest = comments[-1]
        if latest.get("body") == body:
            return latest.get("html_url") or "approval:unchanged"
        updated = self.github.call("PATCH", f"/issues/comments/{latest['id']}", {"body": body})
        return (updated or {}).get("html_url") or latest.get("html_url") or "approval:updated"
