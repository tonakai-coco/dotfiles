"""Read Git objects only: never import or execute PR code."""
import ast
import heapq
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

    def changes(self, base: str, head: str, *, direct: bool = False) -> list[Change]:
        # Review packs use the merge-base. Convergence uses the previous head itself.
        start = base if direct else git(self.root, "merge-base", base, head).decode().strip()
        raw_names = git(self.root, "diff", "--no-renames", "--name-only", "-z",
                        start, head, "--").split(b"\x00")
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
                        "--no-renames", "--unified=3", start, head,
                        "--", path).decode("utf-8", errors="replace")
            if not re.search(r"^@@ ", patch, re.MULTILINE):
                continue  # Binary, mode-only, submodule, etc.
            if len(result) >= self.config.files:
                self.limitations.append("files_truncated")
                break
            old, new = self.blob(start, path), self.blob(head, path)
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

    @staticmethod
    def _python_definition_lines(source: str) -> set[int]:
        try:
            tree = ast.parse(source)
        except (SyntaxError, RecursionError, ValueError):
            return set()
        lines = set()

        def add_target(node, lineno):
            if isinstance(node, ast.Name):
                lines.add(lineno)
            elif isinstance(node, (ast.Tuple, ast.List)):
                for elt in node.elts:
                    add_target(elt, lineno)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lines.add(node.lineno)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    add_target(target, node.lineno)
            elif isinstance(node, ast.AnnAssign) and node.target is not None:
                add_target(node.target, node.lineno)
        return lines

    @staticmethod
    def _module_stems(units: list[dict], symbol: str) -> set[str]:
        return {Path(u["path"]).stem for u in units if u.get("symbol") == symbol and u.get("path")}

    @classmethod
    def _caller_rank(cls, path: str, row: str, symbols: list[str], units: list[dict]) -> int:
        # Higher ranks (qualified use) are preferred over bare word matches.
        best = 0
        for symbol in symbols:
            if not re.search(rf"\b{re.escape(symbol)}\b", row):
                continue
            best = max(best, 1)
            if re.search(rf"\b{re.escape(symbol)}\s*\(", row):
                best = max(best, 3)
            for stem in cls._module_stems(units, symbol):
                if re.search(rf"\b{re.escape(stem)}\.{re.escape(symbol)}\b", row):
                    best = max(best, 4)
                if re.search(rf"\bfrom\s+{re.escape(stem)}\s+import\b.*\b{re.escape(symbol)}\b", row):
                    best = max(best, 4)
                if re.search(rf"\bimport\s+{re.escape(stem)}\b", row) and symbol in row:
                    best = max(best, 2)
            if path.endswith(".py") and re.match(
                    rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(symbol)}\b", row):
                best = min(best, 0)
        return best

    def callers(self, head: str, units: list[dict]):
        symbols = sorted({u["symbol"] for u in units if u["symbol"]})
        if not symbols or not self.config.callers:
            return []
        # Bound scan memory/time: keep only the best ranked hits while streaming grep.
        scan_cap = max(self.config.callers * 20, 50)
        scan_limit = max(self.config.callers * 50, 200)
        # One ephemeral tracked-file search, no index or embedding database.
        proc = subprocess.Popen(["git", "-C", str(self.root), "grep", "-I", "-n",
                                 "-z", "-F", "-w", *[arg for s in symbols for arg in ("-e", s)],
                                 head, "--"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        # Min-heap of (rank, path, line); drop the worst when over scan_cap.
        heap, def_cache, scanned, capped = [], {}, 0, False
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                parts = raw.decode("utf-8", errors="replace").split("\x00", 2)
                if len(parts) != 3:
                    continue
                path, line, row = parts[0].split(":", 1)[1], int(parts[1]), parts[2].rstrip("\n")
                if not self.config.accepts(path) or any(
                        u["path"] == path and u["side"] == "RIGHT"
                        and u["start"] <= line < u["start"] + len(u["text"].splitlines())
                        for u in units):
                    continue
                if path.endswith(".py"):
                    if path not in def_cache:
                        def_cache[path] = self._python_definition_lines(self.blob(head, path))
                    if line in def_cache[path]:
                        continue
                rank = self._caller_rank(path, row, symbols, units)
                if rank <= 0:
                    continue
                item = (rank, path, line)
                if len(heap) < scan_cap:
                    heapq.heappush(heap, item)
                elif item > heap[0]:
                    heapq.heapreplace(heap, item)
                scanned += 1
                if scanned >= scan_limit:
                    capped = True
                    break
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=5)
        candidates = sorted(heap, key=lambda item: (-item[0], item[1], item[2]))
        result, seen = [], set()
        for _, path, line in candidates:
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
                capped = True
                break
        if capped:
            self.limitations.append("callers_search_capped")
        return result

    def _blob_exists(self, ref: str, path: str) -> bool:
        try:
            git(self.root, "cat-file", "-e", f"{ref}:{path}")
            return True
        except subprocess.CalledProcessError:
            return False

    def _resolve_python_module(self, head: str, module: str, from_path: str) -> str | None:
        if not module or module.startswith("."):
            return None  # Relative / empty: drop per SPEC.
        parts = module.split(".")
        candidates = ["/".join(parts) + ".py", "/".join(parts) + "/__init__.py"]
        parent = str(Path(from_path).parent)
        if parent != ".":
            candidates.extend([
                f"{parent}/{'/'.join(parts)}.py",
                f"{parent}/{'/'.join(parts)}/__init__.py",
            ])
        for candidate in candidates:
            normalized = str(Path(candidate))
            if (self.config.accepts(normalized) and normalized != from_path
                    and self._blob_exists(head, normalized)):
                return normalized
        return None

    def _import_targets(self, head: str, changes: list[Change], units: list[dict],
                         seen: set[str]) -> list[dict]:
        # Prefer full RIGHT file text so module-level imports are visible; units alone often omit them.
        right_paths = {u["path"] for u in units if u.get("side") == "RIGHT" and u["path"].endswith(".py")}
        symbols = [u.get("symbol") for u in units if u.get("side") == "RIGHT" and u.get("symbol")]
        result = []
        for change in changes:
            if change.path not in right_paths or not change.new:
                continue
            try:
                tree = ast.parse(change.new)
            except (SyntaxError, RecursionError, ValueError):
                continue
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    modules.append(node.module)
                    # from pkg import worker → also try pkg.worker → pkg/worker.py
                    for alias in node.names:
                        if alias.name != "*":
                            modules.append(f"{node.module}.{alias.name}")
            for module in modules:
                if len(result) >= 5:
                    return result
                path = self._resolve_python_module(head, module, change.path)
                if not path or path in seen:
                    continue
                source = self.blob(head, path).splitlines()
                if not source:
                    continue
                start = 1
                look_for = [module.rsplit(".", 1)[-1], *symbols]
                for symbol in look_for:
                    if not symbol:
                        continue
                    for index, row in enumerate(source, 1):
                        if re.search(rf"\b(?:def|class)\s+{re.escape(symbol)}\b", row):
                            start = max(1, index - 5)
                            break
                    if start != 1:
                        break
                seen.add(path)
                result.append(dict(path=path, start=start, reason="import_target",
                                   text="\n".join(source[start - 1:start + 39])))
        return result

    @staticmethod
    def _sibling_test_candidates(path: str) -> list[str]:
        if not path.endswith(".py"):
            return []
        parent = Path(path).parent
        stem = Path(path).stem
        if stem.startswith("test_") or stem.endswith("_test"):
            return []
        parent_s = "" if str(parent) == "." else str(parent) + "/"
        names = [
            f"{parent_s}test_{stem}.py",
            f"{parent_s}{stem}_test.py",
            f"{parent_s}tests/test_{stem}.py",
            f"tests/{parent_s}test_{stem}.py",
        ]
        return list(dict.fromkeys(names))

    def _sibling_tests(self, head: str, changes: list[Change], units: list[dict],
                       seen: set[str]) -> list[dict]:
        symbols = sorted({u["symbol"] for u in units if u.get("symbol") and u.get("side") == "RIGHT"})
        result = []
        for change in changes:
            for candidate in self._sibling_test_candidates(change.path):
                if len(result) >= 3:
                    return result
                if candidate in seen or not self.config.accepts(candidate):
                    continue
                if not self._blob_exists(head, candidate):
                    continue
                source = self.blob(head, candidate).splitlines()
                if not source:
                    continue
                start = 1
                for symbol in symbols:
                    for index, row in enumerate(source, 1):
                        if re.search(rf"\b{re.escape(symbol)}\b", row):
                            start = max(1, index - 19)
                            break
                    if start != 1:
                        break
                seen.add(candidate)
                result.append(dict(path=candidate, start=start, reason="sibling_test",
                                   text="\n".join(source[start - 1:start + 39])))
        return result

    def _same_dir_configs(self, head: str, changes: list[Change], seen: set[str]) -> list[dict]:
        suffixes = (".yml", ".yaml", ".toml", ".json", ".ini")
        result = []
        dirs = sorted({str(Path(c.path).parent) for c in changes})
        for directory in dirs:
            if len(result) >= 2:
                break
            prefix = "" if directory == "." else directory + "/"
            try:
                listing = git(self.root, "ls-tree", "-r", "--name-only", "-z", head, "--",
                              prefix or ".").split(b"\x00")
            except subprocess.CalledProcessError:
                continue
            for raw in listing:
                if len(result) >= 2:
                    break
                try:
                    path = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if not path or path in seen or Path(path).parent != Path(directory):
                    continue
                if not path.endswith(suffixes) or not self.config.accepts(path):
                    continue
                source = self.blob(head, path).splitlines()
                if not source:
                    continue
                seen.add(path)
                result.append(dict(path=path, start=1, reason="same_dir_config",
                                   text="\n".join(source[:40])))
        return result

    def related(self, head: str, changes: list[Change], units: list[dict]) -> list[dict]:
        if not self.config.related:
            return []
        seen, result = set(), []
        for path in {c.path for c in changes}:
            seen.add(path)
        for item in (self._import_targets(head, changes, units, seen)
                     + self._sibling_tests(head, changes, units, seen)
                     + self._same_dir_configs(head, changes, seen)):
            result.append(item)
            if len(result) >= self.config.related:
                break
        return result

    def build(self, pr: dict, changes: list[Change]) -> dict:
        units = [unit for change in changes for unit in self.units(change)]
        head = pr["head"]["sha"]
        pack = dict(version=0, pr={"number": pr["number"], "title": pr["title"][:1000],
                    "base": pr["base"]["sha"], "head": head,
                    "author": pr["user"]["login"]}, rubric=RUBRIC,
                    units=units, callers=self.callers(head, units),
                    related=self.related(head, changes, units),
                    diff=[dict(path=c.path, text=c.patch) for c in changes],
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
