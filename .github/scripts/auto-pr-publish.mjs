import {
  AutoPrError,
  classifyChangeSize,
  createAutoPrRequestKey,
  createComment,
  createGithubIssueComment,
  createGithubPullRequest,
  findExistingWork,
  formatChangeSummary,
  formatEstimateSummary,
  getCachedPaths,
  getChangeMetrics,
  getGithubToken,
  getIssueContext,
  getRepositoryHeadSha,
  getRepositoryRoot,
  getWorkingTreePaths,
  readJsonFile,
  runGit,
  validateArtifact,
  validateEstimateDocument,
  writeTrackedTextFile,
  writeGithubOutput,
} from "./auto-pr-common.mjs";

function getMode() {
  const mode = process.argv[2];
  if (mode !== "comment" && mode !== "apply" && mode !== "assess" && mode !== "publish") {
    throw new AutoPrError("invalid-mode");
  }
  return mode;
}

async function readEventContext() {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (!eventPath) {
    throw new AutoPrError("event-environment-missing");
  }
  return getIssueContext(await readJsonFile(eventPath));
}

async function readArtifact() {
  const artifactPath = process.env.AUTO_PR_ARTIFACT_PATH;
  if (!artifactPath) {
    throw new AutoPrError("artifact-environment-missing");
  }
  return validateArtifact(await readJsonFile(artifactPath), getRepositoryRoot());
}

async function readEstimateForEvent(context) {
  const planPath = process.env.AUTO_PR_PLAN_PATH;
  if (!planPath) {
    throw new AutoPrError("estimate-environment-missing");
  }

  const estimateDocument = validateEstimateDocument(
    await readJsonFile(planPath),
    getRepositoryRoot(),
  );
  if (
    estimateDocument.repository !== context.repository ||
    estimateDocument.issueNumber !== context.issueNumber ||
    estimateDocument.defaultBranch !== context.defaultBranch
  ) {
    throw new AutoPrError("estimate-event-mismatch");
  }
  return estimateDocument.estimate;
}

function assertArtifactMatchesEvent(artifact, context) {
  if (
    artifact.repository !== context.repository ||
    artifact.issueNumber !== context.issueNumber ||
    artifact.defaultBranch !== context.defaultBranch
  ) {
    throw new AutoPrError("artifact-event-mismatch");
  }
}

function assertArtifactBaseCommit(artifact, repositoryRoot) {
  if (getRepositoryHeadSha(repositoryRoot) !== artifact.baseCommitSha) {
    throw new AutoPrError("artifact-base-commit-mismatch");
  }
}

function assertOnlyAllowedChanges(allowedPaths, repositoryRoot) {
  const allowed = new Set(allowedPaths);
  const changedPaths = getWorkingTreePaths(repositoryRoot);
  if (changedPaths.some((changedPath) => !allowed.has(changedPath))) {
    throw new AutoPrError("unexpected-working-tree-change");
  }
  return changedPaths;
}

async function applyArtifact(artifact) {
  const repositoryRoot = getRepositoryRoot();
  assertArtifactBaseCommit(artifact, repositoryRoot);
  const beforePaths = getWorkingTreePaths(repositoryRoot);
  if (beforePaths.length > 0) {
    throw new AutoPrError("working-tree-not-clean");
  }

  for (const file of artifact.files) {
    await writeTrackedTextFile(file.path, file.content, repositoryRoot);
  }

  assertOnlyAllowedChanges(artifact.targetPaths, repositoryRoot);
  console.log("Artifact applied to the isolated checkout.");
}

async function postComment(reason, details = {}) {
  const context = await readEventContext();
  const token = getGithubToken();
  if (!token) {
    throw new AutoPrError("github-token-missing");
  }

  const requestKey =
    typeof details.requestKey === "string"
      ? details.requestKey
      : await getRequestKeyForComment(context);
  const commentDetails = requestKey ? { ...details, requestKey } : details;

  await createGithubIssueComment({
    token,
    repository: context.repository,
    issueNumber: context.issueNumber,
    body: createComment(reason, commentDetails),
  });
  console.log("Issue notification sent.");
}

async function getRequestKeyForComment(context) {
  const artifactPath = process.env.AUTO_PR_ARTIFACT_PATH;
  if (artifactPath) {
    try {
      const artifact = validateArtifact(await readJsonFile(artifactPath), getRepositoryRoot());
      if (
        artifact.repository === context.repository &&
        artifact.issueNumber === context.issueNumber &&
        artifact.defaultBranch === context.defaultBranch
      ) {
        return createAutoPrRequestKey({
          repository: context.repository,
          issueNumber: context.issueNumber,
          defaultBranch: context.defaultBranch,
          issueTitle: context.issueTitle,
          issueBody: context.issueBody,
          targetPaths: artifact.targetPaths,
          baseCommitSha: artifact.baseCommitSha,
        });
      }
    } catch {
      // Failure comments must remain available even when the artifact is invalid.
    }
  }

  const inputPath = process.env.AUTO_PR_INPUT_PATH;
  if (!inputPath) {
    return undefined;
  }

  try {
    const input = await readJsonFile(inputPath);
    if (
      input.repository === context.repository &&
      input.issueNumber === context.issueNumber &&
      input.defaultBranch === context.defaultBranch
    ) {
      return createAutoPrRequestKey({
        repository: context.repository,
        issueNumber: context.issueNumber,
        defaultBranch: context.defaultBranch,
        issueTitle: context.issueTitle,
        issueBody: context.issueBody,
        targetPaths: input.targetPaths,
        baseCommitSha: input.baseCommitSha,
      });
    }
  } catch {
    // Failure comments must remain available even when the input document is invalid.
  }

  return undefined;
}

function isDryRun() {
  return String(process.env.AUTO_PR_DRY_RUN || "true").toLowerCase() !== "false";
}

function measureArtifactChange(artifact) {
  const repositoryRoot = getRepositoryRoot();
  const changedPaths = assertOnlyAllowedChanges(artifact.targetPaths, repositoryRoot);
  const metrics = getChangeMetrics(artifact.targetPaths, repositoryRoot);
  const assessment = classifyChangeSize(metrics);
  return { repositoryRoot, changedPaths, metrics, assessment };
}

async function assessArtifact(artifact) {
  const context = await readEventContext();
  assertArtifactMatchesEvent(artifact, context);
  assertArtifactBaseCommit(artifact, getRepositoryRoot());
  const { metrics, assessment } = measureArtifactChange(artifact);
  const requestKey = createAutoPrRequestKey({
    repository: context.repository,
    issueNumber: context.issueNumber,
    defaultBranch: context.defaultBranch,
    issueTitle: context.issueTitle,
    issueBody: context.issueBody,
    targetPaths: artifact.targetPaths,
    baseCommitSha: artifact.baseCommitSha,
  });

  await writeGithubOutput({
    size_result: assessment.level,
    changed_files: metrics.changedFiles,
    changed_lines: metrics.changedLines,
    change_areas: metrics.changeAreas,
  });

  if (assessment.level === "split") {
    await postComment("change-too-large", { metrics, assessment, requestKey });
  }

  console.log(
    `Change size assessed: ${assessment.level} (${metrics.changedFiles} files, ${metrics.changedLines} lines, ${metrics.changeAreas} areas).`,
  );
  return { metrics, assessment };
}

function buildPullRequestBody(context, artifact, metrics, assessment) {
  const paths = artifact.targetPaths.map((targetPath) => `- \`${targetPath.replaceAll("`", "\\`")}\``);
  let body = [
    `Closes #${context.issueNumber}`,
    "",
    "## 対象パス",
    ...paths,
    "",
    "## 変更量",
    formatChangeSummary(metrics, assessment),
    "",
    "## 検証",
    "- Secretなしの検証Jobで `make check` と `make status` を実行",
    "- Linux向けリンク作成・確認・解除を実行",
    "- 変更対象に対応するformatter、構文確認、health checkを実行（該当時）",
  ].join("\n");
  if (artifact.estimate) {
    body += `\n\n## 事前見積もり\n${formatEstimateSummary(artifact.estimate)}`;
  }
  return body;
}

function getPushEnvironment(token) {
  const basicToken = Buffer.from(`x-access-token:${token}`, "utf8").toString("base64");
  const environment = { ...process.env };
  delete environment.GITHUB_TOKEN;
  delete environment.GH_TOKEN;
  delete environment.SAKURA_AI_API_KEY;
  return {
    ...environment,
    GIT_CONFIG_COUNT: "1",
    GIT_CONFIG_KEY_0: "http.https://github.com/.extraheader",
    GIT_CONFIG_VALUE_0: `AUTHORIZATION: basic ${basicToken}`,
    GIT_TERMINAL_PROMPT: "0",
  };
}

async function publishArtifact(artifact) {
  const context = await readEventContext();
  assertArtifactMatchesEvent(artifact, context);
  assertArtifactBaseCommit(artifact, getRepositoryRoot());
  const { repositoryRoot, changedPaths, metrics, assessment } = measureArtifactChange(artifact);
  const token = getGithubToken();
  if (!token) {
    throw new AutoPrError("github-token-missing");
  }

  const branch = `auto-fix/${context.issueNumber}`;
  const requestKey = createAutoPrRequestKey({
    repository: context.repository,
    issueNumber: context.issueNumber,
    defaultBranch: context.defaultBranch,
    issueTitle: context.issueTitle,
    issueBody: context.issueBody,
    targetPaths: artifact.targetPaths,
    baseCommitSha: artifact.baseCommitSha,
  });
  const existingWork = await findExistingWork({
    token,
    repository: context.repository,
    branch,
    issueNumber: context.issueNumber,
  });
  if (existingWork.exists) {
    await postComment("existing-work");
    return;
  }

  if (changedPaths.length === 0) {
    await postComment("no-change", { requestKey });
    return;
  }

  if (assessment.level === "split") {
    await postComment("change-too-large", { metrics, assessment, requestKey });
    return;
  }

  if (isDryRun()) {
    await postComment("dry-run", {
      paths: changedPaths,
      metrics,
      assessment,
      estimate: artifact.estimate,
      requestKey,
    });
    return;
  }

  runGit(["switch", "--create", branch], repositoryRoot);
  runGit(["config", "user.name", "github-actions[bot]"], repositoryRoot);
  runGit(["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], repositoryRoot);
  runGit(["add", "--", ...changedPaths], repositoryRoot);

  const cachedPaths = getCachedPaths(repositoryRoot);
  if (cachedPaths.some((cachedPath) => !artifact.targetPaths.includes(cachedPath))) {
    throw new AutoPrError("unexpected-staged-change");
  }
  if (cachedPaths.length === 0) {
    await postComment("no-change");
    return;
  }

  const commitMessage = `fix: Issue #${context.issueNumber} の修正を適用`;
  runGit(
    ["-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", commitMessage],
    repositoryRoot,
  );

  runGit(
    ["remote", "set-url", "origin", `https://github.com/${context.repository}.git`],
    repositoryRoot,
  );
  runGit(["push", "--set-upstream", "origin", branch], repositoryRoot, {
    env: getPushEnvironment(token),
  });

  const pullRequest = await createGithubPullRequest({
    token,
    repository: context.repository,
    title: commitMessage,
    body: buildPullRequestBody(context, artifact, metrics, assessment),
    headBranch: branch,
    baseBranch: context.defaultBranch,
  });
  await postComment("published", {
    paths: changedPaths,
    metrics,
    assessment,
    estimate: artifact.estimate,
    pullRequestUrl: pullRequest.htmlUrl,
    requestKey,
  });
}

async function main() {
  const mode = getMode();
  if (mode === "comment") {
    const reason = process.env.AUTO_PR_REASON;
    if (typeof reason !== "string" || reason.length === 0) {
      throw new AutoPrError("comment-reason-missing");
    }
    const context = await readEventContext();
    const details =
      reason === "preflight-too-large" || reason === "preflight-review-required"
        ? { estimate: await readEstimateForEvent(context) }
        : {};
    await postComment(reason, details);
    return;
  }

  const artifact = await readArtifact();
  const context = await readEventContext();
  assertArtifactMatchesEvent(artifact, context);
  if (mode === "apply") {
    await applyArtifact(artifact);
    return;
  }
  if (mode === "assess") {
    await assessArtifact(artifact);
    return;
  }

  await publishArtifact(artifact);
}

main().catch(() => {
  console.error("Auto PR publish step failed.");
  process.exitCode = 1;
});
