"""Read Git objects only: never import or execute PR code."""
import ast
import json
import re
import subprocess
from pathlib import Path

from core import Change, Config, RUBRIC


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=60).stdout


def line_map(patch: str):
    right, old_changed, new_changed = set(), set(), set()
    old = new = None
    for row in patch.splitlines():
        match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
        if match:
            old, new = map(int, match.groups())
        elif old is not None:
            if row.startswith("+"):
                right.add(new)
                new_changed.add(new)
                new += 1
            elif row.startswith("-"):
                old_changed.add(old)
                old += 1
            elif row.startswith(" "):
                right.add(new)
                old += 1
                new += 1
    return right, old_changed, new_changed


class Packer:
    def __init__(self, root: Path, config: Config):
        self.root, self.config = root, config
        self.limitations = []

    def blob(self, ref: str, path: str) -> str:
        try:
            size = int(git(self.root, "cat-file", "-s", f"{ref}:{path}"))
            if size > 1_000_000:
                self.limitations.append(f"large_blob: {path}")
                return ""
            data = git(self.root, "show", f"{ref}:{path}")
            if b"\x00" in data:
                return ""
            return data.decode("utf-8")
        except subprocess.CalledProcessError:
            return ""  # Added/deleted paths do not exist on both sides.
        except UnicodeDecodeError:
            self.limitations.append(f"non_utf8: {path}")
            return ""

    def changes(self, base: str, head: str) -> list[Change]:
        merge_base = git(self.root, "merge-base", base, head).decode().strip()
        raw_names = git(self.root, "diff", "--no-renames", "--name-only", "-z",
                        merge_base, head, "--").split(b"\x00")
        names = []
        for raw in filter(None, raw_names):
            try:
                names.append(raw.decode("utf-8"))
            except UnicodeDecodeError:
                # Do not pass lossy or surrogate paths to GitHub or JSON APIs.
                self.limitations.append(f"non_utf8_path_skipped: {raw.hex()}")
        result = []
        for path in sorted(p for p in names if p and self.config.accepts(p)):
            patch = git(self.root, "diff", "--no-ext-diff", "--no-textconv",
                        "--no-renames", "--unified=3", merge_base, head,
                        "--", path).decode("utf-8", errors="replace")
            if not re.search(r"^@@ ", patch, re.MULTILINE):
                continue  # Binary, mode-only, submodule, etc.
            if len(result) >= self.config.files:
                self.limitations.append("files_truncated")
                break
            old, new = self.blob(merge_base, path), self.blob(head, path)
            result.append(Change(path, patch, old, new, *line_map(patch)))
        return result

    @staticmethod
    def units(change: Change):
        result = []
        for side, source, lines in [("RIGHT", change.new, change.changed_new),
                                    ("LEFT", change.old, change.changed_old)]:
            if not lines or not source:
                continue
            rows = source.splitlines()
            nodes = []
            if change.path.endswith(".py"):
                try:
                    nodes = [n for n in ast.walk(ast.parse(source))
                             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                except (SyntaxError, RecursionError):
                    pass
            spans = []
            for node in sorted(nodes, key=lambda n: n.lineno):
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                end = node.end_lineno or node.lineno
                if any(start <= line <= end for line in lines) and not any(
                        a <= start and end <= b for a, b in spans):
                    spans.append((start, end))
                    result.append(dict(path=change.path, side=side, start=start,
                                       symbol=node.name, complete=True,
                                       text="\n".join(rows[start - 1:end])))
            # Language-neutral fallback; explicitly not claimed to be a full unit.
            uncovered = sorted(n for n in lines if not any(a <= n <= b for a, b in spans))
            while uncovered:
                start, end = max(1, uncovered[0] - 15), min(len(rows), uncovered[0] + 24)
                excerpt = "\n".join(rows[start - 1:end])
                # Conservative declaration-name hints for reference search in other languages.
                symbol = re.search(r"(?:\b(?:function|class|interface|struct|enum|type)\s+"
                                   r"|\b(?:const|let|var)\s+)([A-Za-z_]\w*)", excerpt)
                result.append(dict(path=change.path, side=side, start=start,
                                   symbol=symbol.group(1) if symbol else None, complete=False,
                                   text="\n".join(rows[start - 1:end])))
                uncovered = [n for n in uncovered if n > end]
        return result

    def callers(self, head: str, units: list[dict]):
        symbols = sorted({u["symbol"] for u in units if u["symbol"]})
        if not symbols or not self.config.callers:
            return []
        # One ephemeral tracked-file search, no index or embedding database.
        proc = subprocess.Popen(["git", "-C", str(self.root), "grep", "-I", "-n",
                                 "-z", "-F", "-w", *[arg for s in symbols for arg in ("-e", s)],
                                 head, "--"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        result, seen = [], set()
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                parts = raw.decode("utf-8", errors="replace").split("\x00", 2)
                if len(parts) != 3:
                    continue
                path, line = parts[0].split(":", 1)[1], int(parts[1])
                if not self.config.accepts(path) or any(
                        u["path"] == path and u["side"] == "RIGHT"
                        and u["start"] <= line < u["start"] + len(u["text"].splitlines())
                        for u in units):
                    continue
                if any(p == path and abs(n - line) < 20 for p, n in seen):
                    continue
                source = self.blob(head, path).splitlines()
                if not source:
                    continue
                start = max(1, line - 19)
                result.append(dict(path=path, start=start,
                                   text="\n".join(source[start - 1:start + 39])))
                seen.add((path, line))
                if len(result) >= self.config.callers:
                    self.limitations.append("callers_search_capped")
                    break
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=5)
        return result

    def build(self, pr: dict, changes: list[Change]) -> dict:
        units = [unit for change in changes for unit in self.units(change)]
        pack = dict(version=0, pr={"number": pr["number"], "title": pr["title"][:1000],
                    "base": pr["base"]["sha"], "head": pr["head"]["sha"],
                    "author": pr["user"]["login"]}, rubric=RUBRIC,
                    units=units, callers=self.callers(pr["head"]["sha"], units),
                    related=[], diff=[dict(path=c.path, text=c.patch) for c in changes],
                    limitations=list(dict.fromkeys(self.limitations)))
        if any(not u["complete"] for u in units):
            pack["limitations"].append("partial_units: non-Python or module-level fallback")
        def size():
            return len(json.dumps(pack, ensure_ascii=False))
        if size() > self.config.max_chars:
            pack["limitations"].append("truncated")
        # Retention priority: units > callers > related > diff tail.
        for key in ("diff", "related", "callers", "units"):
            while pack[key] and size() > self.config.max_chars:
                item = pack[key][-1]
                original = item["text"]
                item["text"] = ""
                item["truncated"] = True
                if key == "units":
                    item["complete"] = False
                if size() >= self.config.max_chars:
                    pack[key].pop()
                    continue
                # JSON escaping can double newline-heavy diffs: budget encoded size.
                low, high = 0, len(original)
                while low < high:
                    middle = (low + high + 1) // 2
                    item["text"] = original[:middle]
                    if size() <= self.config.max_chars:
                        low = middle
                    else:
                        high = middle - 1
                item["text"] = original[:low]
        if size() > self.config.max_chars:
            raise ValueError("Pack metadata exceeds max_chars")
        return pack
