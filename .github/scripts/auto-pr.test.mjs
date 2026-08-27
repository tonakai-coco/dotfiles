import { spawnSync } from "node:child_process";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import test from "node:test";
import * as path from "node:path";
import { tmpdir } from "node:os";

import {
  CHANGE_SIZE_POLICY,
  MAX_GENERATED_FILE_BYTES,
  MAX_GENERATED_TOTAL_BYTES,
  MAX_TARGET_PATH_SPEC_BYTES,
  assertSafeTargetPaths,
  classifyChangeSize,
  createComment,
  formatChangeSummary,
  getChangeMetrics,
  readTargetFilesWithinBudget,
  parseStrictJsonContent,
  parseGitNumstat,
  parseTargetPaths,
  validateGeneratedFiles,
} from "./auto-pr-common.mjs";

test("parses the exact target path section", () => {
  const result = parseTargetPaths([
    "依頼内容",
    "",
    "## 対象パス",
    "- .github/workflows/make-test.yml",
    "- Makefile",
    "",
    "## 補足",
    "説明",
  ].join("\n"));

  assert.deepEqual(result, {
    ok: true,
    paths: [".github/workflows/make-test.yml", "Makefile"],
  });
});
test("rejects a missing target path section", () => {
  assert.deepEqual(parseTargetPaths("## 依頼内容\n- Makefile"), {
    ok: false,
    reason: "missing",
  });
  assert.deepEqual(parseTargetPaths("## 対象パス \n- Makefile"), {
    ok: false,
    reason: "missing",
  });
});

test("accepts more than three target paths", () => {
  const result = parseTargetPaths([
    "## 対象パス",
    "- one",
    "- two",
    "- three",
    "- four",
  ].join("\n"));

  assert.deepEqual(result, {
    ok: true,
    paths: ["one", "two", "three", "four"],
  });
});

test("rejects unsafe and duplicate target paths", () => {
  assert.equal(parseTargetPaths("## 対象パス\n- /etc/passwd").ok, false);
  assert.equal(parseTargetPaths("## 対象パス\n- src/../Makefile").ok, false);
  assert.deepEqual(parseTargetPaths("## 対象パス\n- Makefile\n- Makefile"), {
    ok: false,
    reason: "duplicate",
  });
});

test("rejects non-list content inside the target section", () => {
  assert.deepEqual(parseTargetPaths("## 対象パス\nMakefile"), {
    ok: false,
    reason: "invalid",
  });
});

test("rejects JSON wrapped in Markdown fences", () => {
  assert.throws(
    () => parseStrictJsonContent("```json\n{\"files\":[]}\n```"),
    /ai-invalid-json/,
  );
});

test("accepts exactly the requested non-empty files", () => {
  const result = validateGeneratedFiles(
    {
      files: [
        { path: "Makefile", content: "all:\n\t@true\n" },
        { path: "README.md", content: "# README\n" },
      ],
    },
    ["Makefile", "README.md"],
  );

  assert.deepEqual(result, [
    { path: "Makefile", content: "all:\n\t@true\n" },
    { path: "README.md", content: "# README\n" },
  ]);
});

test("rejects an AI output path outside the request", () => {
  assert.throws(
    () =>
      validateGeneratedFiles(
        { files: [{ path: "other.txt", content: "content" }] },
        ["Makefile"],
      ),
    /ai-unexpected-path/,
  );
});

test("rejects empty AI output content", () => {
  assert.throws(
    () => validateGeneratedFiles({ files: [{ path: "Makefile", content: "  " }] }, ["Makefile"]),
    /ai-empty-content/,
  );
});

test("rejects duplicate AI output paths", () => {
  assert.throws(
    () =>
      validateGeneratedFiles(
        {
          files: [
            { path: "Makefile", content: "one" },
            { path: "Makefile", content: "two" },
          ],
        },
        ["Makefile", "README.md"],
      ),
    /ai-duplicate-path/,
  );
});

test("rejects an oversized target path specification", () => {
  assert.throws(
    () => assertSafeTargetPaths(["a".repeat(MAX_TARGET_PATH_SPEC_BYTES)]),
    /target-paths-too-large/,
  );
});

test("rejects an oversized generated file", () => {
  assert.throws(
    () =>
      validateGeneratedFiles(
        { files: [{ path: "Makefile", content: "x".repeat(MAX_GENERATED_FILE_BYTES + 1) }] },
        ["Makefile"],
      ),
    /ai-file-too-large/,
  );
});

test("rejects generated files whose total content exceeds the budget", () => {
  const content = "x".repeat(Math.floor(MAX_GENERATED_TOTAL_BYTES / 3) + 1);
  assert.throws(
    () =>
      validateGeneratedFiles(
        {
          files: [
            { path: "one", content },
            { path: "two", content },
            { path: "three", content },
          ],
        },
        ["one", "two", "three"],
      ),
    /ai-total-too-large/,
  );
});

test("parses git numstat into change metrics", () => {
  const result = parseGitNumstat([
    "10\t4\tconfig/nvim/init.lua",
    "2\t1\tconfig/tmux/tmux.conf",
    "5\t0\tMakefile",
  ].join("\n"));

  assert.deepEqual(result, {
    files: [
      { path: "config/nvim/init.lua", additions: 10, deletions: 4, changedLines: 14 },
      { path: "config/tmux/tmux.conf", additions: 2, deletions: 1, changedLines: 3 },
      { path: "Makefile", additions: 5, deletions: 0, changedLines: 5 },
    ],
    additions: 17,
    deletions: 5,
    changedFiles: 3,
    changedLines: 22,
    changeAreas: 3,
    maxFileChangedLines: 14,
  });
});

test("measures the actual working tree diff through the git adapter", async (t) => {
  const repositoryRoot = await mkdtemp(path.join(tmpdir(), "auto-pr-change-metrics-"));
  t.after(async () => {
    await rm(repositoryRoot, { recursive: true, force: true });
  });

  await mkdir(path.join(repositoryRoot, "config", "nvim"), { recursive: true });
  await writeFile(path.join(repositoryRoot, "config", "nvim", "init.lua"), "one\n", "utf8");

  const runGit = (args) => {
    const result = spawnSync("git", args, {
      cwd: repositoryRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    assert.equal(result.status, 0, result.stderr);
  };
  runGit(["init", "--quiet"]);
  runGit(["config", "user.name", "test"]);
  runGit(["config", "user.email", "test@example.invalid"]);
  runGit(["add", "--", "config/nvim/init.lua"]);
  runGit(["commit", "--quiet", "--message", "initial"]);

  assert.deepEqual(await readTargetFilesWithinBudget(["config/nvim/init.lua"], repositoryRoot), {
    files: [{ path: "config/nvim/init.lua", content: "one\n" }],
    totalBytes: 4,
  });

  await writeFile(
    path.join(repositoryRoot, "config", "nvim", "init.lua"),
    "one\ntwo\nthree\n",
    "utf8",
  );

  assert.deepEqual(getChangeMetrics(["config/nvim/init.lua"], repositoryRoot), {
    files: [{ path: "config/nvim/init.lua", additions: 2, deletions: 0, changedLines: 2 }],
    additions: 2,
    deletions: 0,
    changedFiles: 1,
    changedLines: 2,
    changeAreas: 1,
    maxFileChangedLines: 2,
  });
});

test("rejects invalid git numstat", () => {
  assert.throws(() => parseGitNumstat("not-numstat"), /change-metrics-invalid/);
  assert.throws(() => parseGitNumstat("-\t1\tMakefile"), /change-metrics-binary/);
});

test("classifies changes using a conservative long-term policy", () => {
  assert.deepEqual(
    classifyChangeSize({
      changedFiles: 2,
      changedLines: CHANGE_SIZE_POLICY.review.changedLines,
      changeAreas: CHANGE_SIZE_POLICY.review.changeAreas,
      maxFileChangedLines: 200,
    }),
    { level: "normal", reasons: [] },
  );

  assert.deepEqual(
    classifyChangeSize({
      changedFiles: 6,
      changedLines: 401,
      changeAreas: 3,
      maxFileChangedLines: 200,
    }),
    {
      level: "review",
      reasons: ["changed-lines", "changed-files", "change-areas"],
    },
  );

  assert.deepEqual(
    classifyChangeSize({
      changedFiles: 2,
      changedLines: 801,
      changeAreas: 1,
      maxFileChangedLines: 801,
    }),
    {
      level: "split",
      reasons: ["changed-lines", "single-file-change"],
    },
  );
});

test("formats a bounded change summary for dry-run and split comments", () => {
  const metrics = {
    additions: 20,
    deletions: 8,
    changedFiles: 4,
    changedLines: 28,
    changeAreas: 2,
    maxFileChangedLines: 20,
  };
  const assessment = { level: "split", reasons: ["changed-files"] };

  assert.equal(
    formatChangeSummary(metrics, assessment),
    "変更量: 4ファイル、+20行/-8行、2領域\n判定: 分割依頼\n判定理由: 変更ファイル数",
  );
  assert.match(
    createComment("change-too-large", { metrics, assessment }),
    /対象を1つの目的・受入条件・変更領域に分割して再依頼/u,
  );
});
