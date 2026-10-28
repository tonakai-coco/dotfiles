"""Drop repeated, pre-existing, and unconfirmed findings before publication."""
import base64
import json
import re

from core import LABELS, Change, Finding, Review
from publisher import MARKER


# After this many published rounds, only new must/important defects remain.
ROUND_CAP = 4
_LABEL_BY_TEXT = {label: severity for severity, label in LABELS.items()}


class History:
    def __init__(self, round: int, suppress: bool, prior_head: str | None, prior: list[dict]):
        self.round = round
        self.suppress = suppress
        self.prior_head = prior_head
        self.prior = prior


def _is_stub(body: str) -> bool:
    return "\n更新済み。最新レビュー:" in body and "<!-- state:" not in body


def load_history(reviews: list[dict], login: str, head: str) -> History:
    own = [row for row in reviews
           if (row.get("user") or {}).get("login") == login
           and str(row.get("body") or "").startswith(MARKER)
           and row.get("state") == "COMMENTED"
           and not _is_stub(str(row.get("body") or ""))]
    if not own:
        return History(1, False, None, [])
    current = max(own, key=lambda row: row.get("id") or 0)
    state = extract_state(current.get("body") or "")
    prior = state["findings"] if state else parse_published_findings(current.get("body") or "")
    stored = state["round"] if state else 1
    if current.get("commit_id") == head:
        return History(stored, False, None, [])
    return History(stored + 1, True, current.get("commit_id"), prior)


def extract_state(body: str):
    match = re.search(r"<!-- state:([A-Za-z0-9+/=]+) -->", body)
    if not match:
        return None
    try:
        data = json.loads(base64.b64decode(match.group(1)))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    round_n, findings = data.get("round"), data.get("findings")
    if type(round_n) is not int or not 1 <= round_n <= 100 or not isinstance(findings, list):
        return None
    clean = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        title, severity = item.get("title"), item.get("severity")
        if not isinstance(title, str) or severity not in LABELS:
            continue
        path = item.get("path") if isinstance(item.get("path"), str) else None
        line = item.get("line") if type(item.get("line")) is int else None
        clean.append({"path": path, "line": line, "severity": severity, "title": title})
    return {"round": round_n, "findings": clean}


def parse_published_findings(text: str) -> list[dict]:
    findings = []
    for block in re.split(r"\n(?=- [🔴🟠🟢⚪])", "\n" + text):
        match = re.match(r"- (🔴 \[MUST\]|🟠 \[IMPORTANT\]|🟢 \[NIT\]|⚪ \[NOTE\]) (.+)", block)
        if not match:
            continue
        loc = re.search(r"\((?:inline|summary_only): ([^:\n]+):(\d+|\?)", block)
        path = line = None
        if loc and loc.group(1) != "(path unspecified)":
            path = loc.group(1)
            if loc.group(2).isdigit():
                line = int(loc.group(2))
        findings.append({
            "path": path, "line": line,
            "severity": _LABEL_BY_TEXT[match.group(1)], "title": match.group(2).strip()})
    return findings


def state_comment(round_n: int, findings: list[Finding]) -> str:
    payload = {
        "round": round_n,
        "findings": [
            {"path": finding.path, "line": finding.line, "severity": finding.severity,
             "title": finding.title[:120]}
            for finding in findings[:40]],
    }
    blob = base64.b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).decode()
    return f"<!-- state:{blob} -->"


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", title.casefold())).strip()


def _quote_in(haystack: str, quote: str) -> bool:
    quote = quote.strip()
    if len(quote) < 8:
        return False
    return re.sub(r"\s+", " ", quote) in re.sub(r"\s+", " ", haystack)


def changed_line_text(change: Change) -> str:
    """Text of added and removed lines. Context lines and diff headers are excluded."""
    lines = []
    for row in change.patch.splitlines():
        if row.startswith(("@@", "\\", "+++ ", "--- ")):
            continue
        if row[:1] in "+-":
            lines.append(row[1:])
    return "\n".join(lines)


def drop_unconfirmed(review: Review, changes: list[Change]) -> Review:
    corpus = {change.path: changed_line_text(change) for change in changes}
    everything = "\n".join(corpus.values())
    kept, dropped = [], 0
    for finding in review.findings:
        if finding.confirmed:
            kept.append(finding)
            continue
        haystack = corpus.get(finding.path, everything) if finding.path else everything
        if finding.origin != "introduced" or not _quote_in(haystack, finding.evidence):
            dropped += 1
            continue
        kept.append(finding)
    if dropped:
        review.limitations.append(f"unconfirmed_dropped: {dropped}")
    review.findings = kept
    return review


def apply_convergence(review: Review, history: History, delta: dict[str, set[int]] | None) -> Review:
    # Same head republish keeps the stored round and must not drop findings.
    if not history.suppress:
        return review
    prior_fp = {(item.get("path"), item.get("severity"), _norm(item.get("title") or ""))
                for item in history.prior}
    kept, dropped = [], 0
    for finding in review.findings:
        if history.suppress and _repeated(finding, history.prior, prior_fp, delta):
            dropped += 1
            continue
        if history.round >= ROUND_CAP and not _within_cap(finding, delta):
            dropped += 1
            continue
        kept.append(finding)
    if dropped:
        review.limitations.append(f"converged: {dropped}")
    if history.round >= ROUND_CAP:
        review.limitations.append(
            "round_cap: 4回目以降は新しい差分の must と important だけを残します。"
            "同じ指摘が続く場合は実装方針を見直してください。")
    review.findings = kept
    return review


def _repeated(finding: Finding, prior: list[dict], prior_fp: set, delta) -> bool:
    if (finding.path, finding.severity, _norm(finding.title)) in prior_fp:
        return True
    if finding.line and any(
            item.get("path") == finding.path and item.get("line") == finding.line
            and item.get("severity") == finding.severity for item in prior):
        return True
    if finding.severity not in ("nit", "note"):
        return False
    if finding.line and any(
            item.get("path") == finding.path and type(item.get("line")) is int
            and abs(item["line"] - finding.line) <= 3 for item in prior):
        return True
    # A nit stays only when its line is in the new delta. Missing delta is not evidence.
    lines = None if delta is None else delta.get(finding.path)
    return not lines or not finding.line or finding.line not in lines


def _within_cap(finding: Finding, delta) -> bool:
    if finding.severity in ("nit", "note"):
        return False
    if not delta or finding.path not in delta:
        return False
    lines = delta.get(finding.path) or set()
    return type(finding.line) is int and finding.line in lines


def verification_items(review: Review, changes: list[Change]) -> list[dict]:
    by_path = {change.path: change for change in changes}
    items = []
    for finding in review.findings:
        if finding.confirmed:
            continue
        patch = by_path[finding.path].patch if finding.path in by_path else ""
        items.append({
            "index": len(items), "severity": finding.severity, "title": finding.title,
            "body": finding.body[:800], "path": finding.path, "line": finding.line,
            "evidence": finding.evidence, "patch": patch[:4000]})
    return items


def apply_verdicts(review: Review, verdicts: list) -> Review:
    keep = set()
    for verdict in verdicts:
        if not isinstance(verdict, dict) or type(verdict.get("index")) is not int:
            continue
        reason = verdict.get("reason")
        if verdict.get("keep") is True and isinstance(reason, str) and reason.strip():
            keep.add(verdict["index"])
    kept, dropped, pending = [], 0, 0
    for finding in review.findings:
        if finding.confirmed:
            kept.append(finding)
            continue
        if pending in keep:
            finding.confirmed = True
            kept.append(finding)
        else:
            dropped += 1
        pending += 1
    if dropped:
        review.limitations.append(f"verification_dropped: {dropped}")
    review.findings = kept
    return review


def keep_severe_on_verification_failure(review: Review, error_name: str) -> Review:
    kept, dropped = [], 0
    for finding in review.findings:
        if finding.confirmed or finding.severity in ("must", "important"):
            kept.append(finding)
        else:
            dropped += 1
    review.findings = kept
    review.limitations.append(f"verification_failed: {error_name}")
    if dropped:
        review.limitations.append(f"verification_failed_dropped: {dropped}")
    return review


def seal(review: Review) -> Review:
    if not review.findings:
        review.summary = "今回の変更で入った不具合は残っていません。"
        review.questions = []
    return review
