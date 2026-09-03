import { createHash } from "node:crypto";
import { appendFile, chmod, lstat, readFile, realpath, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import * as path from "node:path";

export const TARGET_PATH_HEADING = "## 対象パス";
// Target paths are count-unbounded, but the complete-file protocol still needs
// bounded input and output sizes for the runner and model context.
export const MAX_TARGET_PATH_SPEC_BYTES = 64 * 1024;
export const MAX_SOURCE_FILE_BYTES = 128 * 1024;
export const MAX_SOURCE_TOTAL_BYTES = 512 * 1024;
export const MAX_GENERATED_FILE_BYTES = 256 * 1024;
export const MAX_GENERATED_TOTAL_BYTES = 512 * 1024;
export const MAX_ESTIMATE_PAYLOAD_BYTES = 64 * 1024;
export const MAX_ESTIMATE_SUMMARY_CHARS = 1_000;
export const MAX_ESTIMATE_REASON_CHARS = 500;
export const MAX_ESTIMATE_CHANGED_LINES = 1_000_000;
export const MAX_ESTIMATE_CONTEXT_BYTES = 96 * 1024;
export const MAX_ESTIMATE_PREVIEW_CHARS = 12_000;
// These are conservative change-budget guardrails, not human-hour estimates.
export const CHANGE_SIZE_POLICY = Object.freeze({
  review: Object.freeze({
    changedLines: 400,
    changedFiles: 5,
    changeAreas: 2,
  }),
  split: Object.freeze({
    changedLines: 800,
    changedFiles: 10,
    changeAreas: 3,
    singleFileChangedLines: 400,
  }),
});
export const ESTIMATE_PLAN_STATUS = Object.freeze({
  CHANGE_NEEDED: "change-needed",
  NO_CHANGE: "no-change",
  INSUFFICIENT_INSTRUCTIONS: "insufficient-instructions",
});
export const AUTO_PR_LABEL = "auto-pr";
export const AUTO_PR_REQUEST_KEY_VERSION = 1;
export const SAKURA_AI_DEFAULT_ENDPOINT = "https://api.ai.sakura.ad.jp/v1";
export const SAKURA_AI_DEFAULT_MODEL = "gpt-oss-120b";
export const GITHUB_API_BASE_URL = "https://api.github.com";
export const GITHUB_API_VERSION = "2022-11-28";

const PATH_CONTROL_CHARACTERS = /[\u0000-\u001f\u007f\u2028\u2029]/u;
const REPOSITORY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*$/u;
const COMMIT_SHA_PATTERN = /^[0-9a-f]{40}$/u;
const REQUEST_KEY_PATTERN = /^[0-9a-f]{64}$/u;

export class AutoPrError extends Error {
  constructor(code) {
    super(code);
    this.name = "AutoPrError";
    this.code = code;
  }
}

export class GithubApiError extends AutoPrError {
  constructor(status) {
    super("github-api-error");
    this.name = "GithubApiError";
    this.status = status;
  }
}

export function getPreflightEstimateReasonCode(level) {
  if (level === "no-change") {
    return "preflight-no-change";
  }
  if (level === "split") {
    return "preflight-too-large";
  }
  if (level === "manual-review") {
    return "preflight-review-required";
  }
  return "";
}

export const PREFLIGHT_ESTIMATE_FAILURE_MESSAGES = Object.freeze({
  "estimate-plan-empty":
    "Issue本文から具体的な変更内容を判断できないと見積もられたため、変更計画を作成できませんでした。対象パスだけでなく、変更内容と受入条件を記載してください。",
});

export function getPreflightEstimateFailureReason(error) {
  if (
    error instanceof AutoPrError &&
    Object.prototype.hasOwnProperty.call(PREFLIGHT_ESTIMATE_FAILURE_MESSAGES, error.code)
  ) {
    return error.code;
  }

  return "estimate-failed";
}

export function formatPreflightEstimateFailure(error) {
  const reason = getPreflightEstimateFailureReason(error);
  const message = PREFLIGHT_ESTIMATE_FAILURE_MESSAGES[reason];

  return message
    ? `Preflight estimate failed [${reason}]: ${message}`
    : `Preflight estimate failed [${reason}].`;
}

export function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function getRepositoryRoot() {
  return path.resolve(process.env.GITHUB_WORKSPACE || process.cwd());
}

export function validateCommitSha(commitSha) {
  if (typeof commitSha !== "string" || !COMMIT_SHA_PATTERN.test(commitSha)) {
    throw new AutoPrError("invalid-commit-sha");
  }

  return commitSha;
}

export function createAutoPrRequestKey({
  repository,
  issueNumber,
  defaultBranch,
  issueTitle,
  issueBody,
  targetPaths,
  baseCommitSha,
}) {
  if (
    typeof repository !== "string" ||
    !Number.isSafeInteger(issueNumber) ||
    issueNumber <= 0 ||
    typeof defaultBranch !== "string" ||
    typeof issueTitle !== "string" ||
    typeof issueBody !== "string" ||
    !Array.isArray(targetPaths) ||
    targetPaths.length === 0 ||
    targetPaths.some((targetPath) => typeof targetPath !== "string")
  ) {
    throw new AutoPrError("invalid-request-key-input");
  }

  validateRepositoryName(repository);
  validateCommitSha(baseCommitSha);
  const canonicalRequest = JSON.stringify({
    version: AUTO_PR_REQUEST_KEY_VERSION,
    repository,
    issueNumber,
    defaultBranch,
    issueTitle,
    issueBody,
    targetPaths,
    baseCommitSha,
  });
  return createHash("sha256").update(canonicalRequest, "utf8").digest("hex");
}

export function getAutoPrRequestMarker(requestKey) {
  if (typeof requestKey !== "string" || !REQUEST_KEY_PATTERN.test(requestKey)) {
    throw new AutoPrError("invalid-request-key");
  }

  return `<!-- sakura-auto-pr:request-key:${requestKey} -->`;
}

export function hasMatchingAutoPrRequestComment(comments, requestKey) {
  if (!Array.isArray(comments)) {
    throw new AutoPrError("github-response-invalid");
  }

  const marker = getAutoPrRequestMarker(requestKey);
  return comments.some(
    (comment) =>
      isRecord(comment) &&
      isRecord(comment.user) &&
      comment.user.login === "github-actions[bot]" &&
      typeof comment.body === "string" &&
      comment.body.includes(marker),
  );
}

export function getRepositoryHeadSha(repositoryRoot = getRepositoryRoot()) {
  return validateCommitSha(runGit(["rev-parse", "--verify", "HEAD"], repositoryRoot).trim());
}

export function getRequiredEnvironment(name) {
  const value = process.env[name];
  if (typeof value !== "string" || value.length === 0) {
    throw new AutoPrError(`missing-environment-${name}`);
  }

  return value;
}

export async function readJsonFile(filePath) {
  const content = await readFile(filePath, "utf8");
  return JSON.parse(content);
}

export async function writePrivateJson(filePath, value) {
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, {
    encoding: "utf8",
    mode: 0o600,
  });
  await chmod(filePath, 0o600);
}

export async function writeGithubOutput(values) {
  const outputPath = process.env.GITHUB_OUTPUT;
  if (!outputPath) {
    return;
  }

  const lines = Object.entries(values).map(([key, value]) => {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/u.test(key)) {
      throw new AutoPrError("invalid-github-output-key");
    }

    const stringValue = String(value ?? "");
    if (/[\r\n]/u.test(stringValue)) {
      throw new AutoPrError("invalid-github-output-value");
    }

    return `${key}=${stringValue}`;
  });

  await appendFile(outputPath, `${lines.join("\n")}\n`, "utf8");
}

export function validateRepositoryName(repository) {
  if (typeof repository !== "string" || !REPOSITORY_PATTERN.test(repository)) {
    throw new AutoPrError("invalid-repository");
  }

  return repository;
}

export function validateRepositoryPath(repositoryPath, repositoryRoot = getRepositoryRoot()) {
  if (
    typeof repositoryPath !== "string" ||
    repositoryPath.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(repositoryPath) ||
    repositoryPath.includes("\\") ||
    repositoryPath.startsWith("/") ||
    repositoryPath.endsWith("/") ||
    /^[A-Za-z]:/u.test(repositoryPath)
  ) {
    return { ok: false, reason: "invalid" };
  }

  const segments = repositoryPath.split("/");
  if (segments.some((segment) => segment.length === 0 || segment === "." || segment === "..")) {
    return { ok: false, reason: "invalid" };
  }

  const root = path.resolve(repositoryRoot);
  const absolutePath = path.resolve(root, ...segments);
  const relativePath = path.relative(root, absolutePath);
  if (
    relativePath.length === 0 ||
    relativePath === ".." ||
    relativePath.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relativePath)
  ) {
    return { ok: false, reason: "invalid" };
  }

  return { ok: true, path: repositoryPath };
}

export function assertSafeTargetPaths(targetPaths, repositoryRoot = getRepositoryRoot()) {
  if (!Array.isArray(targetPaths) || targetPaths.length === 0) {
    throw new AutoPrError("invalid-target-paths");
  }

  if (Buffer.byteLength(JSON.stringify(targetPaths), "utf8") > MAX_TARGET_PATH_SPEC_BYTES) {
    throw new AutoPrError("target-paths-too-large");
  }

  const seen = new Set();
  for (const targetPath of targetPaths) {
    const validation = validateRepositoryPath(targetPath, repositoryRoot);
    if (!validation.ok) {
      throw new AutoPrError("invalid-path");
    }

    if (seen.has(targetPath)) {
      throw new AutoPrError("duplicate-path");
    }
    seen.add(targetPath);
  }

  return [...targetPaths];
}

export function parseTargetPaths(issueBody) {
  if (typeof issueBody !== "string" || issueBody.length === 0) {
    return { ok: false, reason: "missing" };
  }

  const lines = issueBody.replace(/\r\n?/gu, "\n").split("\n");
  const headingIndex = lines.findIndex((line) => line === TARGET_PATH_HEADING);
  if (headingIndex === -1) {
    return { ok: false, reason: "missing" };
  }

  const paths = [];
  for (const line of lines.slice(headingIndex + 1)) {
    if (/^#{1,6}(?:\s|$)/u.test(line.trim())) {
      break;
    }

    const trimmed = line.trim();
    if (trimmed.length === 0) {
      continue;
    }

    const match = trimmed.match(/^-\s+(.+?)\s*$/u);
    if (!match || !validateRepositoryPath(match[1]).ok) {
      return { ok: false, reason: "invalid" };
    }

    paths.push(match[1]);
  }

  if (paths.length === 0) {
    return { ok: false, reason: "missing" };
  }

  if (new Set(paths).size !== paths.length) {
    return { ok: false, reason: "duplicate" };
  }

  return { ok: true, paths };
}

function getChangeArea(repositoryPath) {
  const segments = repositoryPath.split("/");
  if (segments.length === 1) {
    return "<root>";
  }
  return segments.length >= 3 ? segments.slice(0, 2).join("/") : segments[0];
}

export function parseGitNumstat(output) {
  if (typeof output !== "string") {
    throw new AutoPrError("change-metrics-invalid");
  }

  const files = [];
  for (const line of output.replace(/\r\n?/gu, "\n").split("\n")) {
    if (line.length === 0) {
      continue;
    }

    const fields = line.split("\t");
    if (fields.length !== 3 || fields[2].length === 0) {
      throw new AutoPrError("change-metrics-invalid");
    }

    if (fields[0] === "-" || fields[1] === "-") {
      throw new AutoPrError("change-metrics-binary");
    }

    if (!/^\d+$/u.test(fields[0]) || !/^\d+$/u.test(fields[1]) || !validateRepositoryPath(fields[2]).ok) {
      throw new AutoPrError("change-metrics-invalid");
    }

    const additions = Number(fields[0]);
    const deletions = Number(fields[1]);
    if (!Number.isSafeInteger(additions) || !Number.isSafeInteger(deletions)) {
      throw new AutoPrError("change-metrics-invalid");
    }

    const changedLines = additions + deletions;
    if (!Number.isSafeInteger(changedLines)) {
      throw new AutoPrError("change-metrics-invalid");
    }

    files.push({
      path: fields[2],
      additions,
      deletions,
      changedLines,
    });
  }

  const changeAreas = new Set(files.map((file) => getChangeArea(file.path)));
  return {
    files,
    additions: files.reduce((total, file) => total + file.additions, 0),
    deletions: files.reduce((total, file) => total + file.deletions, 0),
    changedFiles: files.length,
    changedLines: files.reduce((total, file) => total + file.changedLines, 0),
    changeAreas: changeAreas.size,
    maxFileChangedLines: files.reduce((maximum, file) => Math.max(maximum, file.changedLines), 0),
  };
}

export function getChangeMetrics(targetPaths, repositoryRoot = getRepositoryRoot()) {
  const expectedPaths = assertSafeTargetPaths(targetPaths, repositoryRoot);
  const output = runGit(
    ["-c", "core.quotePath=false", "diff", "--numstat", "--", ...expectedPaths],
    repositoryRoot,
  );
  const metrics = parseGitNumstat(output);
  const expected = new Set(expectedPaths);
  if (metrics.files.some((file) => !expected.has(file.path))) {
    throw new AutoPrError("change-metrics-unexpected-path");
  }
  return metrics;
}

function assertChangeMetric(name, value) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new AutoPrError(`change-metrics-invalid-${name}`);
  }
}

export function classifyChangeSize(metrics) {
  if (!isRecord(metrics)) {
    throw new AutoPrError("change-metrics-invalid");
  }

  for (const name of ["changedFiles", "changedLines", "changeAreas", "maxFileChangedLines"]) {
    assertChangeMetric(name, metrics[name]);
  }

  const reviewReasons = [];
  if (metrics.changedLines > CHANGE_SIZE_POLICY.review.changedLines) {
    reviewReasons.push("changed-lines");
  }
  if (metrics.changedFiles > CHANGE_SIZE_POLICY.review.changedFiles) {
    reviewReasons.push("changed-files");
  }
  if (metrics.changeAreas > CHANGE_SIZE_POLICY.review.changeAreas) {
    reviewReasons.push("change-areas");
  }

  const splitReasons = [];
  if (metrics.changedLines > CHANGE_SIZE_POLICY.split.changedLines) {
    splitReasons.push("changed-lines");
  }
  if (metrics.changedFiles > CHANGE_SIZE_POLICY.split.changedFiles) {
    splitReasons.push("changed-files");
  }
  if (metrics.changeAreas > CHANGE_SIZE_POLICY.split.changeAreas) {
    splitReasons.push("change-areas");
  }
  if (metrics.maxFileChangedLines > CHANGE_SIZE_POLICY.split.singleFileChangedLines) {
    splitReasons.push("single-file-change");
  }

  if (splitReasons.length > 0) {
    return { level: "split", reasons: splitReasons };
  }
  if (reviewReasons.length > 0) {
    return { level: "review", reasons: reviewReasons };
  }
  return { level: "normal", reasons: [] };
}

function assertEstimateText(value, code, maximum) {
  if (
    typeof value !== "string" ||
    value.trim().length === 0 ||
    value.length > maximum ||
    PATH_CONTROL_CHARACTERS.test(value)
  ) {
    throw new AutoPrError(code);
  }

  return value.trim();
}

function calculateEstimateScore(metrics) {
  const ratios = [
    metrics.changedLines / CHANGE_SIZE_POLICY.split.changedLines,
    metrics.changedFiles / CHANGE_SIZE_POLICY.split.changedFiles,
    metrics.changeAreas / CHANGE_SIZE_POLICY.split.changeAreas,
    metrics.maxFileChangedLines / CHANGE_SIZE_POLICY.split.singleFileChangedLines,
  ];
  return Number(Math.max(...ratios).toFixed(2));
}

export function validateChangeEstimate(payload, targetPaths, repositoryRoot = getRepositoryRoot()) {
  const expectedPaths = assertSafeTargetPaths(targetPaths, repositoryRoot);
  if (!isRecord(payload)) {
    throw new AutoPrError("estimate-invalid");
  }

  let payloadBytes;
  try {
    payloadBytes = Buffer.byteLength(JSON.stringify(payload), "utf8");
  } catch {
    throw new AutoPrError("estimate-invalid");
  }
  if (payloadBytes > MAX_ESTIMATE_PAYLOAD_BYTES) {
    throw new AutoPrError("estimate-too-large");
  }

  const summary = assertEstimateText(
    payload.summary,
    "estimate-summary-invalid",
    MAX_ESTIMATE_SUMMARY_CHARS,
  );
  if (!["high", "medium", "low"].includes(payload.confidence)) {
    throw new AutoPrError("estimate-confidence-invalid");
  }

  const planStatus = payload.planStatus;
  if (!Object.values(ESTIMATE_PLAN_STATUS).includes(planStatus)) {
    throw new AutoPrError("estimate-plan-status-invalid");
  }
  if (!Array.isArray(payload.plannedChanges)) {
    throw new AutoPrError("estimate-plan-invalid");
  }

  const hasPlannedChanges = payload.plannedChanges.length > 0;
  if (
    planStatus === ESTIMATE_PLAN_STATUS.INSUFFICIENT_INSTRUCTIONS &&
    hasPlannedChanges
  ) {
    throw new AutoPrError("estimate-plan-invalid");
  }
  if (planStatus === ESTIMATE_PLAN_STATUS.INSUFFICIENT_INSTRUCTIONS) {
    throw new AutoPrError("estimate-plan-empty");
  }
  if (
    (planStatus === ESTIMATE_PLAN_STATUS.NO_CHANGE && hasPlannedChanges) ||
    (planStatus === ESTIMATE_PLAN_STATUS.CHANGE_NEEDED && !hasPlannedChanges)
  ) {
    throw new AutoPrError("estimate-plan-invalid");
  }

  const expected = new Set(expectedPaths);
  const seen = new Set();
  const plannedChanges = payload.plannedChanges.map((change) => {
    if (!isRecord(change) || typeof change.path !== "string") {
      throw new AutoPrError("estimate-invalid-change");
    }
    if (!validateRepositoryPath(change.path, repositoryRoot).ok || !expected.has(change.path)) {
      throw new AutoPrError("estimate-unexpected-path");
    }
    if (seen.has(change.path)) {
      throw new AutoPrError("estimate-duplicate-path");
    }
    seen.add(change.path);

    const reason = assertEstimateText(
      change.reason,
      "estimate-reason-invalid",
      MAX_ESTIMATE_REASON_CHARS,
    );
    if (
      !Number.isSafeInteger(change.estimatedChangedLinesMax) ||
      change.estimatedChangedLinesMax <= 0 ||
      change.estimatedChangedLinesMax > MAX_ESTIMATE_CHANGED_LINES
    ) {
      throw new AutoPrError("estimate-lines-invalid");
    }

    return {
      path: change.path,
      reason,
      estimatedChangedLinesMax: change.estimatedChangedLinesMax,
    };
  });

  const changeAreas = new Set(plannedChanges.map((change) => getChangeArea(change.path)));
  const metrics = {
    changedFiles: plannedChanges.length,
    changedLines: plannedChanges.reduce(
      (total, change) => total + change.estimatedChangedLinesMax,
      0,
    ),
    changeAreas: changeAreas.size,
    maxFileChangedLines: plannedChanges.reduce(
      (maximum, change) => Math.max(maximum, change.estimatedChangedLinesMax),
      0,
    ),
  };

  assertChangeMetric("changedFiles", metrics.changedFiles);
  assertChangeMetric("changedLines", metrics.changedLines);
  assertChangeMetric("changeAreas", metrics.changeAreas);
  assertChangeMetric("maxFileChangedLines", metrics.maxFileChangedLines);

  const reviewReasons = [];
  if (metrics.changedLines >= CHANGE_SIZE_POLICY.review.changedLines) {
    reviewReasons.push("changed-lines");
  }
  if (metrics.changedFiles >= CHANGE_SIZE_POLICY.review.changedFiles) {
    reviewReasons.push("changed-files");
  }
  if (metrics.changeAreas >= CHANGE_SIZE_POLICY.review.changeAreas) {
    reviewReasons.push("change-areas");
  }

  const splitReasons = [];
  if (metrics.changedLines >= CHANGE_SIZE_POLICY.split.changedLines) {
    splitReasons.push("changed-lines");
  }
  if (metrics.changedFiles >= CHANGE_SIZE_POLICY.split.changedFiles) {
    splitReasons.push("changed-files");
  }
  if (metrics.changeAreas >= CHANGE_SIZE_POLICY.split.changeAreas) {
    splitReasons.push("change-areas");
  }
  if (metrics.maxFileChangedLines >= CHANGE_SIZE_POLICY.split.singleFileChangedLines) {
    splitReasons.push("single-file-change");
  }

  const estimatedLevel = splitReasons.length > 0
    ? "split"
    : reviewReasons.length > 0
      ? "review"
      : "normal";
  const level = planStatus === ESTIMATE_PLAN_STATUS.NO_CHANGE
    ? "no-change"
    : splitReasons.length > 0
      ? "split"
      : payload.confidence === "low"
        ? "manual-review"
        : "proceed";
  const reasons = planStatus === ESTIMATE_PLAN_STATUS.NO_CHANGE
    ? []
    : splitReasons.length > 0
      ? splitReasons
      : payload.confidence === "low"
        ? ["low-confidence"]
        : reviewReasons;

  return {
    summary,
    confidence: payload.confidence,
    planStatus,
    plannedChanges,
    metrics,
    assessment: {
      level,
      estimatedLevel,
      reasons,
      sizeScore: calculateEstimateScore(metrics),
    },
  };
}

export function validateEstimateDocument(payload, repositoryRoot = getRepositoryRoot()) {
  if (
    !isRecord(payload) ||
    payload.version !== 1 ||
    typeof payload.repository !== "string" ||
    !Number.isSafeInteger(payload.issueNumber) ||
    payload.issueNumber <= 0 ||
    typeof payload.baseCommitSha !== "string" ||
    typeof payload.defaultBranch !== "string" ||
    payload.defaultBranch.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(payload.defaultBranch) ||
    !Array.isArray(payload.targetPaths) ||
    !isRecord(payload.estimate)
  ) {
    throw new AutoPrError("invalid-estimate-document");
  }

  validateRepositoryName(payload.repository);
  const baseCommitSha = validateCommitSha(payload.baseCommitSha);
  const targetPaths = assertSafeTargetPaths(payload.targetPaths, repositoryRoot);
  const estimate = validateChangeEstimate(payload.estimate, targetPaths, repositoryRoot);
  return {
    version: 1,
    repository: payload.repository,
    issueNumber: payload.issueNumber,
    baseCommitSha,
    defaultBranch: payload.defaultBranch,
    targetPaths,
    estimate,
  };
}

const ESTIMATE_LEVEL_TEXT = Object.freeze({
  proceed: "生成可",
  split: "分割依頼",
  "manual-review": "人手確認",
  "no-change": "変更不要",
});

const ESTIMATE_SIZE_TEXT = Object.freeze({
  normal: "通常",
  review: "要確認",
  split: "分割依頼",
});

const ESTIMATE_CONFIDENCE_TEXT = Object.freeze({
  high: "高",
  medium: "中",
  low: "低",
});

const ESTIMATE_PLAN_STATUS_TEXT = Object.freeze({
  [ESTIMATE_PLAN_STATUS.CHANGE_NEEDED]: "変更あり",
  [ESTIMATE_PLAN_STATUS.NO_CHANGE]: "変更不要",
  [ESTIMATE_PLAN_STATUS.INSUFFICIENT_INSTRUCTIONS]: "指示不足",
});

export function formatEstimateSummary(estimate) {
  if (
    !isRecord(estimate) ||
    !isRecord(estimate.metrics) ||
    !isRecord(estimate.assessment) ||
    !Array.isArray(estimate.plannedChanges) ||
    typeof estimate.confidence !== "string" ||
    !ESTIMATE_PLAN_STATUS_TEXT[estimate.planStatus]
  ) {
    throw new AutoPrError("estimate-invalid");
  }

  const { metrics, assessment } = estimate;
  for (const name of ["changedFiles", "changedLines", "changeAreas", "maxFileChangedLines"]) {
    assertChangeMetric(name, metrics[name]);
  }
  if (
    !ESTIMATE_LEVEL_TEXT[assessment.level] ||
    !ESTIMATE_SIZE_TEXT[assessment.estimatedLevel] ||
    !Number.isFinite(assessment.sizeScore)
  ) {
    throw new AutoPrError("estimate-invalid");
  }
  if (!ESTIMATE_CONFIDENCE_TEXT[estimate.confidence]) {
    throw new AutoPrError("estimate-invalid");
  }

  return [
    `見積もり状態: ${ESTIMATE_PLAN_STATUS_TEXT[estimate.planStatus]}`,
    `事前見積もり: 最大${metrics.changedFiles}ファイル、最大${metrics.changedLines}行、${metrics.changeAreas}領域、1ファイル最大${metrics.maxFileChangedLines}行`,
    `見積もりスコア: ${assessment.sizeScore}`,
    `見積もり確度: ${ESTIMATE_CONFIDENCE_TEXT[estimate.confidence]}`,
    `見積もり規模: ${ESTIMATE_SIZE_TEXT[assessment.estimatedLevel]}`,
    `見積もり判定: ${ESTIMATE_LEVEL_TEXT[assessment.level]}`,
  ].join("\n");
}

function resolveRepositoryPath(repositoryPath, repositoryRoot = getRepositoryRoot()) {
  const validation = validateRepositoryPath(repositoryPath, repositoryRoot);
  if (!validation.ok) {
    throw new AutoPrError("invalid-path");
  }

  return path.resolve(repositoryRoot, ...repositoryPath.split("/"));
}

function isPathInside(root, candidate) {
  const relativePath = path.relative(root, candidate);
  return (
    relativePath.length > 0 &&
    relativePath !== ".." &&
    !relativePath.startsWith(`..${path.sep}`) &&
    !path.isAbsolute(relativePath)
  );
}

export function runGit(args, repositoryRoot = getRepositoryRoot(), options = {}) {
  const result = spawnSync("git", args, {
    cwd: repositoryRoot,
    env: options.env || process.env,
    encoding: options.encoding || "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });

  if (result.error || result.status !== 0) {
    throw new AutoPrError("git-command-failed");
  }

  return result.stdout;
}

export async function assertTrackedRegularFile(repositoryPath, repositoryRoot = getRepositoryRoot()) {
  const absolutePath = resolveRepositoryPath(repositoryPath, repositoryRoot);
  let fileStats;

  try {
    fileStats = await lstat(absolutePath);
  } catch (error) {
    if (error?.code === "ENOENT") {
      throw new AutoPrError("file-missing");
    }
    throw new AutoPrError("file-unreadable");
  }

  if (!fileStats.isFile() || fileStats.isSymbolicLink()) {
    throw new AutoPrError("file-not-regular");
  }

  let rootRealPath;
  let targetRealPath;
  try {
    rootRealPath = await realpath(repositoryRoot);
    targetRealPath = await realpath(absolutePath);
  } catch {
    throw new AutoPrError("file-unreadable");
  }

  if (!isPathInside(rootRealPath, targetRealPath)) {
    throw new AutoPrError("file-outside-repository");
  }

  try {
    const tracked = runGit(["ls-files", "--error-unmatch", "--", repositoryPath], repositoryRoot);
    if (String(tracked).trim().length === 0) {
      throw new AutoPrError("file-untracked");
    }
  } catch (error) {
    if (error instanceof AutoPrError && error.code === "file-untracked") {
      throw error;
    }
    throw new AutoPrError("file-untracked");
  }

  return absolutePath;
}

export async function readTrackedTextFile(repositoryPath, repositoryRoot = getRepositoryRoot()) {
  const absolutePath = await assertTrackedRegularFile(repositoryPath, repositoryRoot);
  let content;

  try {
    const bytes = await readFile(absolutePath);
    if (bytes.includes(0)) {
      throw new AutoPrError("file-binary");
    }
    content = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (error) {
    if (error instanceof AutoPrError) {
      throw error;
    }
    throw new AutoPrError("file-not-utf8");
  }

  return content;
}

export async function readTargetFilesWithinBudget(targetPaths, repositoryRoot = getRepositoryRoot()) {
  const expectedPaths = assertSafeTargetPaths(targetPaths, repositoryRoot);
  const files = [];
  let totalBytes = 0;

  for (const targetPath of expectedPaths) {
    const content = await readTrackedTextFile(targetPath, repositoryRoot);
    const fileBytes = Buffer.byteLength(content, "utf8");
    if (fileBytes > MAX_SOURCE_FILE_BYTES) {
      throw new AutoPrError("source-file-too-large");
    }

    totalBytes += fileBytes;
    if (totalBytes > MAX_SOURCE_TOTAL_BYTES) {
      throw new AutoPrError("source-total-too-large");
    }

    files.push({ path: targetPath, content });
  }

  return { files, totalBytes };
}

function createEstimatePreview(content) {
  if (content.length <= MAX_ESTIMATE_PREVIEW_CHARS) {
    return content;
  }

  const headLength = Math.floor(MAX_ESTIMATE_PREVIEW_CHARS * 0.55);
  const tailLength = Math.floor(MAX_ESTIMATE_PREVIEW_CHARS * 0.35);
  return [
    content.slice(0, headLength),
    "...（省略）...",
    content.slice(-tailLength),
  ].join("\n");
}

export async function readTargetFilesForEstimate(
  targetPaths,
  repositoryRoot = getRepositoryRoot(),
) {
  const { files, totalBytes } = await readTargetFilesWithinBudget(targetPaths, repositoryRoot);
  const summaries = [];

  for (const file of files) {
    const summary = {
      path: file.path,
      bytes: Buffer.byteLength(file.content, "utf8"),
      lines: file.content.length === 0 ? 0 : file.content.split("\n").length,
      preview: createEstimatePreview(file.content),
    };
    const summaryBytes = Buffer.byteLength(JSON.stringify(summary), "utf8");
    const currentBytes = Buffer.byteLength(JSON.stringify(summaries), "utf8");

    if (currentBytes + summaryBytes > MAX_ESTIMATE_CONTEXT_BYTES) {
      summary.preview = "（コンテキスト上限のため内容を省略）";
    }
    summaries.push(summary);
  }

  if (Buffer.byteLength(JSON.stringify(summaries), "utf8") > MAX_ESTIMATE_CONTEXT_BYTES) {
    throw new AutoPrError("estimate-context-too-large");
  }

  return { files: summaries, totalBytes };
}

export async function writeTrackedTextFile(repositoryPath, content, repositoryRoot = getRepositoryRoot()) {
  if (typeof content !== "string" || content.length === 0 || content.includes("\0")) {
    throw new AutoPrError("empty-or-invalid-content");
  }

  const absolutePath = await assertTrackedRegularFile(repositoryPath, repositoryRoot);
  await writeFile(absolutePath, content, "utf8");
}

export function parseStrictJsonContent(content) {
  if (typeof content !== "string" || content.length === 0) {
    throw new AutoPrError("ai-invalid-json");
  }

  try {
    return JSON.parse(content);
  } catch {
    throw new AutoPrError("ai-invalid-json");
  }
}

export function validateGeneratedFiles(payload, targetPaths, repositoryRoot = getRepositoryRoot()) {
  const expectedPaths = assertSafeTargetPaths(targetPaths, repositoryRoot);
  if (!isRecord(payload) || !Array.isArray(payload.files)) {
    throw new AutoPrError("ai-invalid-files");
  }

  if (payload.files.length !== expectedPaths.length) {
    throw new AutoPrError("ai-file-count-mismatch");
  }

  const expected = new Set(expectedPaths);
  const seen = new Set();
  const files = payload.files.map((file) => {
    if (!isRecord(file) || typeof file.path !== "string" || typeof file.content !== "string") {
      throw new AutoPrError("ai-invalid-file-entry");
    }

    if (!validateRepositoryPath(file.path, repositoryRoot).ok || !expected.has(file.path)) {
      throw new AutoPrError("ai-unexpected-path");
    }

    if (seen.has(file.path)) {
      throw new AutoPrError("ai-duplicate-path");
    }
    seen.add(file.path);

    if (file.content.length === 0 || file.content.trim().length === 0 || file.content.includes("\0")) {
      throw new AutoPrError("ai-empty-content");
    }

    return { path: file.path, content: file.content };
  });

  let totalBytes = 0;
  for (const file of files) {
    const fileBytes = Buffer.byteLength(file.content, "utf8");
    if (fileBytes > MAX_GENERATED_FILE_BYTES) {
      throw new AutoPrError("ai-file-too-large");
    }

    totalBytes += fileBytes;
    if (totalBytes > MAX_GENERATED_TOTAL_BYTES) {
      throw new AutoPrError("ai-total-too-large");
    }
  }

  if (seen.size !== expected.size) {
    throw new AutoPrError("ai-missing-path");
  }

  return files;
}

export function validateArtifact(payload, repositoryRoot = getRepositoryRoot()) {
  if (
    !isRecord(payload) ||
    payload.version !== 1 ||
    typeof payload.repository !== "string" ||
    typeof payload.issueNumber !== "number" ||
    !Number.isSafeInteger(payload.issueNumber) ||
    payload.issueNumber <= 0 ||
    typeof payload.baseCommitSha !== "string" ||
    typeof payload.defaultBranch !== "string" ||
    payload.defaultBranch.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(payload.defaultBranch) ||
    !Array.isArray(payload.targetPaths)
  ) {
    throw new AutoPrError("invalid-artifact");
  }

  validateRepositoryName(payload.repository);
  const baseCommitSha = validateCommitSha(payload.baseCommitSha);
  if (payload.defaultBranch.includes("\0")) {
    throw new AutoPrError("invalid-artifact");
  }

  const targetPaths = assertSafeTargetPaths(payload.targetPaths, repositoryRoot);
  const files = validateGeneratedFiles(payload, targetPaths, repositoryRoot);
  const estimate = payload.estimate === undefined
    ? undefined
    : validateChangeEstimate(payload.estimate, targetPaths, repositoryRoot);
  return {
    version: 1,
    repository: payload.repository,
    issueNumber: payload.issueNumber,
    baseCommitSha,
    defaultBranch: payload.defaultBranch,
    targetPaths,
    files,
    ...(estimate ? { estimate } : {}),
  };
}

export function getIssueContext(event) {
  if (!isRecord(event) || !isRecord(event.repository) || !isRecord(event.issue)) {
    throw new AutoPrError("invalid-event");
  }

  const repository = validateRepositoryName(event.repository.full_name);
  const defaultBranch = event.repository.default_branch;
  if (
    typeof defaultBranch !== "string" ||
    defaultBranch.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(defaultBranch)
  ) {
    throw new AutoPrError("invalid-event");
  }

  const issueNumber = event.issue.number;
  if (!Number.isSafeInteger(issueNumber) || issueNumber <= 0) {
    throw new AutoPrError("invalid-event");
  }

  const labels = Array.isArray(event.issue.labels)
    ? event.issue.labels
        .filter((label) => isRecord(label) && typeof label.name === "string")
        .map((label) => label.name)
    : [];

  return {
    action: event.action,
    labelName:
      isRecord(event.label) && typeof event.label.name === "string" ? event.label.name : null,
    state: event.issue.state,
    repository,
    defaultBranch,
    issueNumber,
    issueTitle: typeof event.issue.title === "string" ? event.issue.title : "",
    issueBody: typeof event.issue.body === "string" ? event.issue.body : "",
    labels,
    isPullRequest: isRecord(event.issue.pull_request),
  };
}

export function getGithubToken() {
  return process.env.GITHUB_TOKEN || process.env.GH_TOKEN || "";
}

function splitRepository(repository) {
  validateRepositoryName(repository);
  const [owner, name] = repository.split("/");
  return { owner, name };
}

function repositoryApiPath(repository) {
  const { owner, name } = splitRepository(repository);
  return `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`;
}

function safeBranchApiPath(branch) {
  if (
    typeof branch !== "string" ||
    branch.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(branch) ||
    branch.includes("\\")
  ) {
    throw new AutoPrError("invalid-branch");
  }

  return encodeURIComponent(branch);
}

export async function githubRequest({ token, path: apiPath, method = "GET", body }) {
  if (typeof token !== "string" || token.length === 0) {
    throw new AutoPrError("github-token-missing");
  }

  const headers = {
    accept: "application/vnd.github+json",
    authorization: `Bearer ${token}`,
    "user-agent": "sakura-auto-pr-github-actions",
    "x-github-api-version": GITHUB_API_VERSION,
  };
  if (body !== undefined) {
    headers["content-type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${GITHUB_API_BASE_URL}${apiPath}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new AutoPrError("github-request-failed");
  }

  if (!response.ok) {
    throw new GithubApiError(response.status);
  }

  if (response.status === 204) {
    return undefined;
  }

  try {
    return await response.json();
  } catch {
    throw new AutoPrError("github-response-invalid");
  }
}

function hasLinkedPullRequest(events) {
  return events.some(
    (event) =>
      isRecord(event) &&
      event.event === "cross-referenced" &&
      isRecord(event.source) &&
      isRecord(event.source.issue) &&
      isRecord(event.source.issue.pull_request),
  );
}

async function hasIssueLinkedPullRequest({ token, repository, issueNumber }) {
  for (let page = 1; page <= 10; page += 1) {
    const query = new URLSearchParams({ page: String(page), per_page: "100" });
    const events = await githubRequest({
      token,
      path: `${repositoryApiPath(repository)}/issues/${issueNumber}/timeline?${query.toString()}`,
    });

    if (!Array.isArray(events)) {
      throw new AutoPrError("github-response-invalid");
    }
    if (hasLinkedPullRequest(events)) {
      return true;
    }
    if (events.length < 100) {
      return false;
    }
  }

  return false;
}

export async function findExistingWork({ token, repository, branch, issueNumber }) {
  const { owner } = splitRepository(repository);
  const query = new URLSearchParams({
    head: `${owner}:${branch}`,
    per_page: "100",
    state: "all",
  });
  const pullRequests = await githubRequest({
    token,
    path: `${repositoryApiPath(repository)}/pulls?${query.toString()}`,
  });

  if (!Array.isArray(pullRequests)) {
    throw new AutoPrError("github-response-invalid");
  }
  if (pullRequests.length > 0) {
    return { exists: true, kind: "pull-request" };
  }

  if (Number.isSafeInteger(issueNumber) && issueNumber > 0) {
    if (await hasIssueLinkedPullRequest({ token, repository, issueNumber })) {
      return { exists: true, kind: "linked-pull-request" };
    }
  }

  try {
    await githubRequest({
      token,
      path: `${repositoryApiPath(repository)}/branches/${safeBranchApiPath(branch)}`,
    });
    return { exists: true, kind: "branch" };
  } catch (error) {
    if (error instanceof GithubApiError && error.status === 404) {
      return { exists: false, kind: null };
    }
    throw error;
  }
}

export async function hasExistingAutoPrRequest({ token, repository, issueNumber, requestKey }) {
  if (!Number.isSafeInteger(issueNumber) || issueNumber <= 0) {
    throw new AutoPrError("invalid-issue-number");
  }

  getAutoPrRequestMarker(requestKey);
  for (let page = 1; page <= 10; page += 1) {
    const query = new URLSearchParams({ page: String(page), per_page: "100" });
    const comments = await githubRequest({
      token,
      path: `${repositoryApiPath(repository)}/issues/${issueNumber}/comments?${query.toString()}`,
    });

    if (!Array.isArray(comments)) {
      throw new AutoPrError("github-response-invalid");
    }
    if (hasMatchingAutoPrRequestComment(comments, requestKey)) {
      return true;
    }
    if (comments.length < 100) {
      return false;
    }
  }

  throw new AutoPrError("github-pagination-limit");
}

export async function createGithubIssueComment({ token, repository, issueNumber, body }) {
  await githubRequest({
    token,
    path: `${repositoryApiPath(repository)}/issues/${issueNumber}/comments`,
    method: "POST",
    body: { body },
  });
}

export async function createGithubPullRequest({
  token,
  repository,
  title,
  body,
  headBranch,
  baseBranch,
}) {
  const payload = await githubRequest({
    token,
    path: `${repositoryApiPath(repository)}/pulls`,
    method: "POST",
    body: {
      title,
      body,
      head: headBranch,
      base: baseBranch,
    },
  });

  if (
    !isRecord(payload) ||
    !Number.isSafeInteger(payload.number) ||
    typeof payload.html_url !== "string" ||
    !payload.html_url.startsWith("https://github.com/")
  ) {
    throw new AutoPrError("github-response-invalid");
  }

  return { number: payload.number, htmlUrl: payload.html_url };
}

export function getWorkingTreePaths(repositoryRoot = getRepositoryRoot()) {
  const output = runGit(
    ["-c", "core.quotePath=false", "status", "--porcelain=v1", "-z"],
    repositoryRoot,
    { encoding: "buffer" },
  );
  const records = output.toString("utf8").split("\0");
  const paths = [];

  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (record.length === 0) {
      continue;
    }
    if (record.length < 4 || record[2] !== " ") {
      throw new AutoPrError("git-status-invalid");
    }

    const status = record.slice(0, 2);
    paths.push(record.slice(3));
    if (status.includes("R") || status.includes("C")) {
      const renamedPath = records[index + 1];
      if (!renamedPath) {
        throw new AutoPrError("git-status-invalid");
      }
      paths.push(renamedPath);
      index += 1;
    }
  }

  return paths;
}

export function getCachedPaths(repositoryRoot = getRepositoryRoot()) {
  const output = runGit(
    ["-c", "core.quotePath=false", "diff", "--cached", "--name-only", "-z", "--"],
    repositoryRoot,
    { encoding: "buffer" },
  );
  return output
    .toString("utf8")
    .split("\0")
    .filter((repositoryPath) => repositoryPath.length > 0);
}

function escapeInlineCode(value) {
  return value.replaceAll("`", "\\`");
}

function formatPaths(paths) {
  return paths.map((repositoryPath) => `- \`${escapeInlineCode(repositoryPath)}\``).join("\n");
}

const COMMENT_TEXT = Object.freeze({
  "missing-paths": "Issue本文に `## 対象パス` と箇条書きの対象ファイルを指定してください。自動PRは開始していません。",
  "invalid-path": "対象パスが安全なリポジトリ内パスではありません。自動PRは開始していません。",
  "duplicate-path": "対象パスに重複があります。自動PRは開始していません。",
  "target-paths-too-large": "対象パスの指定が大きすぎるため、自動PRを開始していません。対象領域を整理して再依頼してください。",
  "source-file-too-large": "対象ファイルが大きすぎるため、自動PRを開始していません。対象を分割して再依頼してください。",
  "source-total-too-large": "対象ファイルの合計サイズが大きすぎるため、自動PRを開始していません。対象を分割して再依頼してください。",
  "file-missing": "対象ファイルを確認できませんでした。自動PRは開始していません。",
  "missing-label": "`auto-pr` ラベルがないため、自動PRは開始していません。",
  "unsupported-event": "対象外のIssueイベントのため、自動PRは開始していません。",
  "not-issue": "Pull Requestは自動PRの対象外です。",
  "already-processed": "同じIssue要求の自動PR処理はすでに完了しているため、重複処理をスキップしました。",
  "existing-work": "同じIssueに対応する既存のブランチまたはPull Requestがあるため、重複作成を停止しました。",
  "github-state-check-failed": "既存ブランチまたはPull Requestを確認できないため、安全側に停止しました。",
  "ai-failed": "Sakura AI Engineの生成または応答検証に失敗したため、自動PRを停止しました。",
  "validation-failed": "Secretなしの検証に失敗したため、自動PRを停止しました。",
  "publish-failed": "検証済み成果物の公開に失敗しました。自動PRを停止しました。",
  "estimate-failed": "生成前の変更計画を作成または検証できなかったため、自動PRを停止しました。",
  "estimate-plan-empty": PREFLIGHT_ESTIMATE_FAILURE_MESSAGES["estimate-plan-empty"],
  "preflight-no-change": "事前見積もりで変更不要と判定されたため、完全なファイル生成とPull Request作成は実行していません。要件を変更する場合は、具体的な変更内容を追記して再依頼してください。",
  "preflight-too-large": "生成前の変更量見積もりが自動PRの変更予算を超えたため、完成ファイルを生成せず停止しました。対象を1つの目的、受入条件、変更領域に分割して再依頼してください。",
  "preflight-review-required": "生成前の変更量見積もりの確度が低いため、完成ファイルを生成せず人手確認を依頼します。対象範囲と変更方針を具体化して再依頼してください。",
  "change-too-large": "生成された変更量が自動PRの変更予算を超えたため、自動PRを停止しました。対象を1つの目的・受入条件・変更領域に分割して再依頼してください。",
  "dry-run": "生成物とSecretなしの検証は完了しました。現在はdry-runのため、branch・push・commit・Pull Request作成は実行していません。",
  published: "Pull Requestの作成と公開が完了しました。",
  "no-change": "修正前後に差分がないため、commitとPull Request作成は実行していません。",
  "internal-error": "自動PR処理で入力または内部状態を確認できないため、安全側に停止しました。",
});

const PREFLIGHT_ESTIMATE_COMMENT_REASONS = new Set([
  "preflight-no-change",
  "preflight-too-large",
  "preflight-review-required",
]);

const IDEMPOTENT_COMMENT_REASONS = new Set([
  "preflight-no-change",
  "preflight-too-large",
  "preflight-review-required",
  "change-too-large",
  "dry-run",
  "published",
  "no-change",
]);

const CHANGE_LEVEL_TEXT = Object.freeze({
  normal: "通常",
  review: "要確認",
  split: "分割依頼",
});

const CHANGE_REASON_TEXT = Object.freeze({
  "changed-lines": "変更行数",
  "changed-files": "変更ファイル数",
  "change-areas": "変更領域数",
  "single-file-change": "単一ファイルの変更量",
});

export function formatChangeSummary(metrics, assessment) {
  if (!isRecord(metrics) || !isRecord(assessment) || !Array.isArray(assessment.reasons)) {
    throw new AutoPrError("change-assessment-invalid");
  }

  for (const name of ["additions", "deletions", "changedFiles", "changedLines", "changeAreas"]) {
    assertChangeMetric(name, metrics[name]);
  }
  if (typeof assessment.level !== "string" || !CHANGE_LEVEL_TEXT[assessment.level]) {
    throw new AutoPrError("change-assessment-invalid");
  }

  const reasons = assessment.reasons
    .map((reason) => CHANGE_REASON_TEXT[reason])
    .filter((reason) => typeof reason === "string");
  const lines = [
    `変更量: ${metrics.changedFiles}ファイル、+${metrics.additions}行/-${metrics.deletions}行、${metrics.changeAreas}領域`,
    `判定: ${CHANGE_LEVEL_TEXT[assessment.level]}`,
  ];
  if (reasons.length > 0) {
    lines.push(`判定理由: ${reasons.join("、")}`);
  }
  return lines.join("\n");
}

function formatEstimatePlan(estimate) {
  const changes = estimate.plannedChanges.slice(0, 20).map(
    (change) =>
      `- \`${escapeInlineCode(change.path)}\`: ${escapeInlineCode(change.reason)}（最大${change.estimatedChangedLinesMax}行）`,
  );
  if (estimate.plannedChanges.length > 20) {
    changes.push(`- 残り${estimate.plannedChanges.length - 20}件は省略`);
  }
  return changes.join("\n");
}

export function createComment(reason, details = {}) {
  const text = COMMENT_TEXT[reason] || COMMENT_TEXT["internal-error"];
  let body = `<!-- sakura-auto-pr:${reason} -->\n${text}`;

  if (PREFLIGHT_ESTIMATE_COMMENT_REASONS.has(reason) && isRecord(details.estimate)) {
    const plan =
      reason === "preflight-no-change" ? "- 変更なし" : formatEstimatePlan(details.estimate);
    body += `\n\n${details.estimate.summary}\n\n${formatEstimateSummary(details.estimate)}\n\n変更計画:\n${plan}`;
  }

  if ((reason === "dry-run" || reason === "published") && Array.isArray(details.paths)) {
    body += `\n\n対象パス:\n${formatPaths(details.paths)}`;
  }
  if (
    (reason === "change-too-large" || reason === "dry-run" || reason === "published") &&
    isRecord(details.metrics) &&
    isRecord(details.assessment)
  ) {
    body += `\n\n${formatChangeSummary(details.metrics, details.assessment)}`;
  }
  if (
    (reason === "dry-run" || reason === "published") &&
    isRecord(details.estimate)
  ) {
    body += `\n\n${formatEstimateSummary(details.estimate)}`;
  }
  if (reason === "published" && typeof details.pullRequestUrl === "string") {
    body += `\n\nPull Request: ${details.pullRequestUrl}`;
  }
  if (IDEMPOTENT_COMMENT_REASONS.has(reason) && typeof details.requestKey === "string") {
    body += `\n\n${getAutoPrRequestMarker(details.requestKey)}`;
  }

  return body;
}

export const INPUT_REASON_CODES = new Set([
  "missing-paths",
  "invalid-path",
  "duplicate-path",
  "target-paths-too-large",
  "source-file-too-large",
  "source-total-too-large",
  "file-missing",
  "missing-label",
  "unsupported-event",
  "not-issue",
  "already-processed",
  "existing-work",
  "github-state-check-failed",
  "internal-error",
]);
