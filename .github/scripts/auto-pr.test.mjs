import { spawnSync } from "node:child_process";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import test from "node:test";
import * as path from "node:path";
import { tmpdir } from "node:os";

import {
  AutoPrError,
  CHANGE_SIZE_POLICY,
  MAX_ESTIMATE_CONTEXT_BYTES,
  MAX_ESTIMATE_PREVIEW_CHARS,
  MAX_GENERATED_FILE_BYTES,
  MAX_GENERATED_TOTAL_BYTES,
  MAX_TARGET_PATH_SPEC_BYTES,
  assertSafeTargetPaths,
  classifyChangeSize,
  createAutoPrRequestKey,
  createComment,
  formatChangeSummary,
  formatEstimateSummary,
  formatPreflightEstimateFailure,
  getChangeMetrics,
  getAutoPrRequestMarker,
  getPreflightEstimateReasonCode,
  getPreflightEstimateFailureReason,
  hasExistingAutoPrRequest,
  hasMatchingAutoPrRequestComment,
  readTargetFilesWithinBudget,
  readTargetFilesForEstimate,
  parseStrictJsonContent,
  parseGitNumstat,
  parseTargetPaths,
  validateCommitSha,
  validateChangeEstimate,
  validateEstimateDocument,
  validateArtifact,
  validateGeneratedFiles,
} from "./auto-pr-common.mjs";
import { getValidationPlan } from "./auto-pr-validate.mjs";

const TEST_COMMIT_SHA = "a".repeat(40);

const TEST_REQUEST = {
  repository: "tonakai-coco/dotfiles",
  issueNumber: 31,
  defaultBranch: "main",
  issueTitle: "dry-runで動作確認する",
  issueBody: "## 対象パス\n- docs/agent-guides/validation.md",
  targetPaths: ["docs/agent-guides/validation.md"],
  baseCommitSha: TEST_COMMIT_SHA,
};

test("derives a stable request key from the Issue request", () => {
  const requestKey = createAutoPrRequestKey(TEST_REQUEST);

  assert.match(requestKey, /^[0-9a-f]{64}$/u);
  assert.equal(createAutoPrRequestKey(TEST_REQUEST), requestKey);
  assert.notEqual(
    createAutoPrRequestKey({ ...TEST_REQUEST, issueBody: `${TEST_REQUEST.issueBody}\n変更` }),
    requestKey,
  );
});

test("detects a completed request marker without treating a failure comment as complete", () => {
  const requestKey = createAutoPrRequestKey(TEST_REQUEST);
  const completedComment = createComment("dry-run", { requestKey });
  const failureComment = createComment("ai-failed", { requestKey });

  assert.match(completedComment, new RegExp(getAutoPrRequestMarker(requestKey), "u"));
  assert.equal(
    hasMatchingAutoPrRequestComment(
      [{ body: completedComment, user: { login: "github-actions[bot]" } }],
      requestKey,
    ),
    true,
  );
  assert.equal(
    hasMatchingAutoPrRequestComment(
      [{ body: completedComment, user: { login: "github-actions[bot]" } }],
      "b".repeat(64),
    ),
    false,
  );
  assert.equal(
    hasMatchingAutoPrRequestComment(
      [{ body: completedComment, user: { login: "human-user" } }],
      requestKey,
    ),
    false,
  );
  assert.doesNotMatch(failureComment, new RegExp(getAutoPrRequestMarker(requestKey), "u"));
});

test("checks Issue comments for an existing auto-pr request marker", async () => {
  const requestKey = createAutoPrRequestKey(TEST_REQUEST);
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => [
      { body: createComment("dry-run", { requestKey }), user: { login: "github-actions[bot]" } },
    ],
  });

  try {
    assert.equal(
      await hasExistingAutoPrRequest({
        token: "test-token",
        repository: TEST_REQUEST.repository,
        issueNumber: TEST_REQUEST.issueNumber,
        requestKey,
      }),
      true,
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("subscribes to the auto-pr label event only", async () => {
  const workflow = await readFile(
    new URL("../workflows/auto-pr.yml", import.meta.url),
    "utf8",
  );

  assert.match(workflow, /types: \[labeled\]/u);
  assert.doesNotMatch(workflow, /types: \[opened,\s*labeled\]/u);
  assert.match(workflow, /steps\.input\.outputs\.result != 'skipped'/u);
  assert.match(
    workflow,
    /AUTO_PR_REASON: \$\{\{ steps\.estimate\.outputs\.reason_code \|\| 'estimate-failed' \}\}/u,
  );
});

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

test("validates a preflight plan and derives conservative estimate metrics", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "設定と検証手順を更新する",
      planStatus: "change-needed",
      confidence: "medium",
      plannedChanges: [
        {
          path: "config/nvim/init.lua",
          reason: "起動時設定を更新する",
          estimatedChangedLinesMax: 120,
        },
        {
          path: "Makefile",
          reason: "検証用ターゲットを調整する",
          estimatedChangedLinesMax: 80,
        },
      ],
    },
    ["config/nvim/init.lua", "Makefile"],
  );

  assert.deepEqual(estimate.metrics, {
    changedFiles: 2,
    changedLines: 200,
    changeAreas: 2,
    maxFileChangedLines: 120,
  });
  assert.deepEqual(estimate.assessment, {
    level: "proceed",
    estimatedLevel: "review",
    reasons: ["change-areas"],
    sizeScore: 0.67,
  });
});

test("stops before generation when the preflight upper estimate reaches the split budget", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "大規模な設定移行を行う",
      planStatus: "change-needed",
      confidence: "high",
      plannedChanges: [
        {
          path: "Makefile",
          reason: "多数のターゲットを移行する",
          estimatedChangedLinesMax: 800,
        },
      ],
    },
    ["Makefile"],
  );

  assert.equal(estimate.assessment.level, "split");
  assert.equal(estimate.assessment.estimatedLevel, "split");
  assert.deepEqual(estimate.assessment.reasons, ["changed-lines", "single-file-change"]);
  assert.equal(estimate.assessment.sizeScore, 2);
});

test("requires manual review when the preflight estimate has low confidence", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "対象範囲の依存関係を確認できない",
      planStatus: "change-needed",
      confidence: "low",
      plannedChanges: [
        {
          path: "Makefile",
          reason: "依存関係を調査してから変更する",
          estimatedChangedLinesMax: 40,
        },
      ],
    },
    ["Makefile"],
  );

  assert.equal(estimate.assessment.level, "manual-review");
  assert.equal(estimate.assessment.estimatedLevel, "normal");
  assert.deepEqual(estimate.assessment.reasons, ["low-confidence"]);
});

test("accepts an explicit no-change estimate without generating a plan", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "対象ファイルはIssueの要件を満たしている",
      planStatus: "no-change",
      confidence: "high",
      plannedChanges: [],
    },
    ["Makefile"],
  );

  assert.equal(estimate.planStatus, "no-change");
  assert.deepEqual(estimate.metrics, {
    changedFiles: 0,
    changedLines: 0,
    changeAreas: 0,
    maxFileChangedLines: 0,
  });
  assert.deepEqual(estimate.assessment, {
    level: "no-change",
    estimatedLevel: "normal",
    reasons: [],
    sizeScore: 0,
  });

  const comment = createComment("preflight-no-change", { estimate });
  assert.match(comment, /事前見積もりで変更不要と判定/u);
  assert.match(comment, /完全なファイル生成とPull Request作成は実行していません/u);
  assert.match(comment, /見積もり状態: 変更不要/u);
  assert.match(comment, /変更計画:\n- 変更なし/u);
});

test("reports insufficient instructions only when the estimator marks them explicitly", () => {
  assert.throws(
    () =>
      validateChangeEstimate(
        {
          summary: "Issue本文から具体的な変更内容を判断できない",
          planStatus: "insufficient-instructions",
          confidence: "low",
          plannedChanges: [],
        },
        ["Makefile"],
      ),
    /estimate-plan-empty/,
  );
});

test("requires an explicit preflight plan status", () => {
  assert.throws(
    () =>
      validateChangeEstimate(
        {
          summary: "変更内容を見積もる",
          confidence: "high",
          plannedChanges: [],
        },
        ["Makefile"],
      ),
    /estimate-plan-status-invalid/,
  );
});

test("rejects a change-needed estimate without a plan as invalid", () => {
  assert.throws(
    () =>
      validateChangeEstimate(
        {
          summary: "変更内容を見積もる",
          planStatus: "change-needed",
          confidence: "high",
          plannedChanges: [],
        },
        ["Makefile"],
      ),
    /estimate-plan-invalid/,
  );
});

test("maps each preflight estimate outcome to its gate reason", () => {
  assert.equal(getPreflightEstimateReasonCode("proceed"), "");
  assert.equal(getPreflightEstimateReasonCode("no-change"), "preflight-no-change");
  assert.equal(getPreflightEstimateReasonCode("split"), "preflight-too-large");
  assert.equal(getPreflightEstimateReasonCode("manual-review"), "preflight-review-required");
});

test("explains when the Issue has no concrete change plan", () => {
  const error = new AutoPrError("estimate-plan-empty");

  assert.equal(getPreflightEstimateFailureReason(error), "estimate-plan-empty");
  assert.match(formatPreflightEstimateFailure(error), /estimate-plan-empty/u);
  assert.match(formatPreflightEstimateFailure(error), /具体的な変更内容/u);
  assert.match(formatPreflightEstimateFailure(error), /受入条件/u);
  assert.match(createComment("estimate-plan-empty"), /対象パスだけでなく/u);
});

test("keeps an unknown preflight failure generic", () => {
  const error = new AutoPrError("sakura-request-failed");

  assert.equal(getPreflightEstimateFailureReason(error), "estimate-failed");
  assert.equal(
    formatPreflightEstimateFailure(error),
    "Preflight estimate failed [estimate-failed].",
  );
});

test("rejects a preflight plan that contains an unrequested path", () => {
  assert.throws(
    () =>
      validateChangeEstimate(
        {
          summary: "対象外のファイルも変更する",
          planStatus: "change-needed",
          confidence: "high",
          plannedChanges: [
            {
              path: "other.txt",
              reason: "対象外の変更",
              estimatedChangedLinesMax: 10,
            },
          ],
        },
        ["Makefile"],
      ),
    /estimate-unexpected-path/,
  );
});

test("formats a bounded preflight estimate summary", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "設定と検証手順を更新する",
      planStatus: "change-needed",
      confidence: "medium",
      plannedChanges: [
        {
          path: "config/nvim/init.lua",
          reason: "起動時設定を更新する",
          estimatedChangedLinesMax: 120,
        },
        {
          path: "Makefile",
          reason: "検証用ターゲットを調整する",
          estimatedChangedLinesMax: 80,
        },
      ],
    },
    ["config/nvim/init.lua", "Makefile"],
  );

  assert.match(
    formatEstimateSummary(estimate),
    /事前見積もり: 最大2ファイル、最大200行、2領域、1ファイル最大120行/u,
  );
  assert.match(formatEstimateSummary(estimate), /見積もりスコア: 0\.67/u);
  assert.match(formatEstimateSummary(estimate), /見積もり規模: 要確認/u);
  assert.match(formatEstimateSummary(estimate), /見積もり判定: 生成可/u);
});

test("formats a preflight split comment with the plan and without generated contents", () => {
  const estimate = validateChangeEstimate(
    {
      summary: "大規模な設定移行を行う",
      planStatus: "change-needed",
      confidence: "high",
      plannedChanges: [
        {
          path: "Makefile",
          reason: "多数のターゲットを移行する",
          estimatedChangedLinesMax: 800,
        },
      ],
    },
    ["Makefile"],
  );

  const comment = createComment("preflight-too-large", { estimate });
  assert.match(comment, /完成ファイルを生成せず停止/u);
  assert.match(comment, /Makefile/u);
  assert.match(comment, /最大800行/u);
  assert.doesNotMatch(comment, /source code|```/u);
});

test("validates an estimate document before passing it between workflow jobs", () => {
  const document = validateEstimateDocument({
    version: 1,
    repository: "tonakai-coco/dotfiles",
    issueNumber: 10,
    baseCommitSha: TEST_COMMIT_SHA,
    defaultBranch: "main",
    targetPaths: ["Makefile"],
    estimate: {
      summary: "検証用ターゲットを更新する",
      planStatus: "change-needed",
      confidence: "high",
      plannedChanges: [
        {
          path: "Makefile",
          reason: "検証用ターゲットを更新する",
          estimatedChangedLinesMax: 20,
        },
      ],
    },
  });

  assert.equal(document.estimate.assessment.level, "proceed");
  assert.equal(document.estimate.metrics.changedLines, 20);
});

test("validates the immutable base commit SHA", () => {
  assert.equal(validateCommitSha(TEST_COMMIT_SHA), TEST_COMMIT_SHA);
  assert.throws(() => validateCommitSha("not-a-commit"), /invalid-commit-sha/);
});

test("carries the immutable base commit in the generated artifact", () => {
  const artifact = validateArtifact({
    version: 1,
    repository: "tonakai-coco/dotfiles",
    issueNumber: 10,
    baseCommitSha: TEST_COMMIT_SHA,
    defaultBranch: "main",
    targetPaths: ["Makefile"],
    files: [{ path: "Makefile", content: "all:\n\t@true\n" }],
  });

  assert.equal(artifact.baseCommitSha, TEST_COMMIT_SHA);
});

test("selects documented component validations from changed paths", () => {
  assert.deepEqual(
    getValidationPlan([
      "config/nvim/lua/config/options.lua",
      "config/fish/functions/cd.fish",
      "config/karabiner/numpad.json",
      "config/wezterm/wezterm.lua",
      "config/tmux/tmux.conf",
      ".github/workflows/auto-pr.yml",
    ]),
    ["nvim-format", "nvim-health", "fish-indent", "karabiner-json", "wezterm-start", "tmux-source"],
  );
  assert.deepEqual(getValidationPlan([".github/workflows/auto-pr.yml", "docs/README.md"]), []);
});

test("builds bounded file context for a preflight estimate", async (t) => {
  const repositoryRoot = await mkdtemp(path.join(tmpdir(), "auto-pr-estimate-context-"));
  t.after(async () => {
    await rm(repositoryRoot, { recursive: true, force: true });
  });

  const content = `${"line\n".repeat(MAX_ESTIMATE_PREVIEW_CHARS)}tail\n`;
  await writeFile(path.join(repositoryRoot, "target.txt"), content, "utf8");
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
  runGit(["add", "--", "target.txt"]);
  runGit(["commit", "--quiet", "--message", "initial"]);

  const result = await readTargetFilesForEstimate(["target.txt"], repositoryRoot);
  assert.equal(result.totalBytes, Buffer.byteLength(content, "utf8"));
  assert.equal(result.files[0].path, "target.txt");
  assert.equal(result.files[0].bytes, Buffer.byteLength(content, "utf8"));
  assert.equal(result.files[0].lines, content.split("\n").length);
  assert.match(result.files[0].preview, /省略/u);
  assert.ok(Buffer.byteLength(JSON.stringify(result.files), "utf8") <= MAX_ESTIMATE_CONTEXT_BYTES);
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

test("uses a success message for published comments", () => {
  const comment = createComment("published", {
    pullRequestUrl: "https://github.com/tonakai-coco/dotfiles/pull/31",
  });

  assert.match(comment, /Pull Requestの作成と公開が完了しました/u);
  assert.match(comment, /https:\/\/github\.com\/tonakai-coco\/dotfiles\/pull\/31/u);
  assert.doesNotMatch(comment, /内部エラー/u);
});
