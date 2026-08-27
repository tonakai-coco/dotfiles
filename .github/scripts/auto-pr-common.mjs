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
export const AUTO_PR_LABEL = "auto-pr";
export const SAKURA_AI_DEFAULT_ENDPOINT = "https://api.ai.sakura.ad.jp/v1";
export const SAKURA_AI_DEFAULT_MODEL = "gpt-oss-120b";
export const GITHUB_API_BASE_URL = "https://api.github.com";
export const GITHUB_API_VERSION = "2022-11-28";

const PATH_CONTROL_CHARACTERS = /[\u0000-\u001f\u007f\u2028\u2029]/u;
const REPOSITORY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*$/u;

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

export function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function getRepositoryRoot() {
  return path.resolve(process.env.GITHUB_WORKSPACE || process.cwd());
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
    typeof payload.defaultBranch !== "string" ||
    payload.defaultBranch.length === 0 ||
    PATH_CONTROL_CHARACTERS.test(payload.defaultBranch) ||
    !Array.isArray(payload.targetPaths)
  ) {
    throw new AutoPrError("invalid-artifact");
  }

  validateRepositoryName(payload.repository);
  if (payload.defaultBranch.includes("\0")) {
    throw new AutoPrError("invalid-artifact");
  }

  const targetPaths = assertSafeTargetPaths(payload.targetPaths, repositoryRoot);
  const files = validateGeneratedFiles(payload, targetPaths, repositoryRoot);
  return {
    version: 1,
    repository: payload.repository,
    issueNumber: payload.issueNumber,
    defaultBranch: payload.defaultBranch,
    targetPaths,
    files,
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
  "existing-work": "同じIssueに対応する既存のブランチまたはPull Requestがあるため、重複作成を停止しました。",
  "github-state-check-failed": "既存ブランチまたはPull Requestを確認できないため、安全側に停止しました。",
  "ai-failed": "Sakura AI Engineの生成または応答検証に失敗したため、自動PRを停止しました。",
  "validation-failed": "Secretなしの検証に失敗したため、自動PRを停止しました。",
  "publish-failed": "検証済み成果物の公開に失敗しました。自動PRを停止しました。",
  "change-too-large": "生成された変更量が自動PRの変更予算を超えたため、自動PRを停止しました。対象を1つの目的・受入条件・変更領域に分割して再依頼してください。",
  "dry-run": "生成物とSecretなしの検証は完了しました。現在はdry-runのため、branch・push・commit・Pull Request作成は実行していません。",
  "no-change": "修正前後に差分がないため、commitとPull Request作成は実行していません。",
  "internal-error": "自動PR処理で入力または内部状態を確認できないため、安全側に停止しました。",
});

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

export function createComment(reason, details = {}) {
  const text = COMMENT_TEXT[reason] || COMMENT_TEXT["internal-error"];
  let body = `<!-- sakura-auto-pr:${reason} -->\n${text}`;

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
  if (reason === "published" && typeof details.pullRequestUrl === "string") {
    body += `\n\nPull Request: ${details.pullRequestUrl}`;
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
  "existing-work",
  "github-state-check-failed",
  "internal-error",
]);
