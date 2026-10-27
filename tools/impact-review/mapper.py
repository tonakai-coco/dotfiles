"""Validate anchors against actual diff lines, never trust model coordinates."""
from core import Change, Config, LABELS, Review
from packer import line_map


class Mapper:
    @staticmethod
    def map(review: Review, changes: list[Change], config: Config, github_files=None) -> Review:
        allowed = {c.path: c.right_lines for c in changes}
        if github_files is not None:
            # GitHub may detect renames differently or omit large file patches.
            # Only coordinates visible in both diffs may be published inline.
            actual = {f["filename"]: line_map(f.get("patch") or "")[0] for f in github_files}
            allowed = {path: lines & actual.get(path, set()) for path, lines in allowed.items()}
        counts = {"must_important": 0, "nit": 0, "note": 0}
        kept = []
        for finding in sorted(review.findings, key=lambda f: list(LABELS).index(f.severity)):
            bucket = "must_important" if finding.severity in ("must", "important") else finding.severity
            if counts[bucket] >= getattr(config, bucket):
                continue
            counts[bucket] += 1
            finding.inline = (type(finding.line) is int and finding.line > 0
                              and finding.path in allowed
                              and finding.line in allowed[finding.path])
            kept.append(finding)
        if len(kept) < len(review.findings):
            review.limitations.append(f"finding_limits: {len(review.findings) - len(kept)} omitted")
        review.findings = kept
        return review
