"""Shared types, configuration, and the silent eligibility gate."""
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

import yaml


LABELS = {"must": "🔴 [MUST]", "important": "🟠 [IMPORTANT]",
          "nit": "🟢 [NIT]", "note": "⚪ [NOTE]"}
RUBRIC = ["正しさ・回帰（既存呼び出し破壊）", "エラー処理・境界",
          "明確な可読性問題（過剰 nit 抑制）", "明らかなセキュリティ問題",
          "テスト不足（該当時のみ）", "影響範囲（callers から見える波及）"]
DEFAULT_IGNORE = ["*.lock", "*-lock.json", "*-lock.yaml", "yarn.lock", "go.sum", "*.min.js",
                  "*.map", "*.generated.*", "*.g.*", "vendor/**", "node_modules/**",
                  "dist/**", "build/**", "__pycache__/**", ".git/**"]


@dataclass
class Config:
    include: list[str] = field(default_factory=lambda: ["**"])
    ignore: list[str] = field(default_factory=list)
    files: int = 30
    callers: int = 10
    max_chars: int = 80_000
    must_important: int = 10
    nit: int = 5
    note: int = 3

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict) or set(raw) - {"paths", "limits"}:
            raise ValueError("Config accepts only paths and limits; credentials belong in env")
        paths, limits = raw.get("paths", {}), raw.get("limits", {})
        if not isinstance(paths, dict) or set(paths) - {"include", "ignore"}:
            raise ValueError("Invalid paths configuration")
        maxima = {"files": 300, "callers": 100, "max_chars": 500_000,
                  "must_important": 10, "nit": 5, "note": 3}
        if not isinstance(limits, dict) or set(limits) - maxima.keys():
            raise ValueError("Invalid limits configuration")
        for key, value in limits.items():
            minimum = 2000 if key == "max_chars" else 0
            if type(value) is not int or not minimum <= value <= maxima[key]:
                raise ValueError(f"Invalid limit: {key}")
        for value in paths.values():
            if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
                raise ValueError("Path patterns must be lists of strings")
        return cls(**paths, **limits)

    def accepts(self, path: str) -> bool:
        def matches(pattern):
            # Also apply directory patterns below the repository root.
            parts = path.split("/")
            return any(fnmatchcase("/".join(parts[i:]), pattern)
                       for i in range(len(parts)))
        return any(matches(p) for p in self.include) and not any(
            matches(p) for p in DEFAULT_IGNORE + self.ignore)


@dataclass
class Change:
    path: str
    patch: str
    old: str
    new: str
    right_lines: set[int]
    changed_old: set[int]
    changed_new: set[int]


@dataclass
class Finding:
    severity: str
    title: str
    body: str
    path: str | None = None
    line: int | None = None
    symbol: str | None = None
    inline: bool = False

    def text(self):
        return f"{LABELS[self.severity]} {self.title}\n\n{self.body}"


@dataclass
class Review:
    summary: str
    impact: str
    questions: list[str]
    findings: list[Finding]
    limitations: list[str] = field(default_factory=list)


class Gate:
    @staticmethod
    def eligible(pr: dict, repository: str) -> bool:
        author = pr.get("user")
        if not isinstance(author, dict) or not author.get("login"):
            return False
        return (pr.get("state") == "open" and not pr.get("draft", False)
                and author.get("type") != "Bot"
                and not author["login"].lower().endswith("[bot]")
                and (pr["head"].get("repo") or {}).get("full_name") == repository)

    @staticmethod
    def has_targets(changes: list[Change]) -> bool:
        return bool(changes)
