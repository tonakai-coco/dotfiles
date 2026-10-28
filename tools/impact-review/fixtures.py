from core import Finding, Review


def pr(head="b" * 40, base="a" * 40):
    return {"number": 1, "title": "Change calculate", "state": "open", "draft": False,
            "user": {"login": "alice", "type": "User"},
            "base": {"sha": base}, "head": {"sha": head, "repo": {"full_name": "o/r"}}}


def review(line=2):
    return Review("要約", "影響", ["境界は？"], [
        Finding("must", "境界条件", "0を処理する", "a.py", line, inline=True, confirmed=True)])
