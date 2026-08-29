import {
  AUTO_PR_LABEL,
  AutoPrError,
  GithubApiError,
  INPUT_REASON_CODES,
  findExistingWork,
  getGithubToken,
  getIssueContext,
  getRepositoryHeadSha,
  getRepositoryRoot,
  parseTargetPaths,
  readTargetFilesWithinBudget,
  readJsonFile,
  writeGithubOutput,
  writePrivateJson,
} from "./auto-pr-common.mjs";

const INPUT_REASON_MAP = Object.freeze({
  missing: "missing-paths",
  invalid: "invalid-path",
  duplicate: "duplicate-path",
});

const FILE_CHECK_ERROR_CODES = new Set([
  "file-binary",
  "file-not-regular",
  "file-not-utf8",
  "file-outside-repository",
  "file-unreadable",
  "file-untracked",
  "file-missing",
]);

function getEventPath() {
  return process.env.GITHUB_EVENT_PATH;
}

function getInputPath() {
  return process.env.AUTO_PR_INPUT_PATH;
}

async function main() {
  const eventPath = getEventPath();
  const inputPath = getInputPath();
  if (!eventPath || !inputPath) {
    throw new AutoPrError("input-environment-missing");
  }

  let result = "invalid";
  let reasonCode = "internal-error";

  try {
    const event = await readJsonFile(eventPath);
    const context = getIssueContext(event);
    if (context.isPullRequest) {
      throw new AutoPrError("not-issue");
    }
    if (context.action !== "opened" && context.action !== "labeled") {
      throw new AutoPrError("unsupported-event");
    }
    if (context.action === "labeled" && context.labelName !== AUTO_PR_LABEL) {
      throw new AutoPrError("unsupported-event");
    }
    if (context.state !== "open") {
      throw new AutoPrError("unsupported-event");
    }
    if (!context.labels.includes(AUTO_PR_LABEL)) {
      throw new AutoPrError("missing-label");
    }

    const parsedPaths = parseTargetPaths(context.issueBody);
    if (!parsedPaths.ok) {
      throw new AutoPrError(INPUT_REASON_MAP[parsedPaths.reason] || "invalid-path");
    }

    const repositoryRoot = getRepositoryRoot();
    await readTargetFilesWithinBudget(parsedPaths.paths, repositoryRoot);

    const token = getGithubToken();
    if (!token) {
      throw new AutoPrError("github-state-check-failed");
    }

    const branch = `auto-fix/${context.issueNumber}`;
    let existingWork;
    try {
      existingWork = await findExistingWork({
        token,
        repository: context.repository,
        branch,
        issueNumber: context.issueNumber,
      });
    } catch (error) {
      if (error instanceof GithubApiError || error instanceof AutoPrError) {
        throw new AutoPrError("github-state-check-failed");
      }
      throw error;
    }

    if (existingWork.exists) {
      throw new AutoPrError("existing-work");
    }

    const baseCommitSha = getRepositoryHeadSha(repositoryRoot);
    await writePrivateJson(inputPath, {
      version: 1,
      repository: context.repository,
      issueNumber: context.issueNumber,
      baseCommitSha,
      issueTitle: context.issueTitle,
      issueBody: context.issueBody,
      defaultBranch: context.defaultBranch,
      targetPaths: parsedPaths.paths,
    });
    result = "ready";
    reasonCode = "";
  } catch (error) {
    if (error instanceof AutoPrError && INPUT_REASON_CODES.has(error.code)) {
      reasonCode = error.code;
    } else if (error instanceof AutoPrError && FILE_CHECK_ERROR_CODES.has(error.code)) {
      reasonCode = "file-missing";
    } else if (error instanceof GithubApiError) {
      reasonCode = "github-state-check-failed";
    }
  }

  await writeGithubOutput({ result, reason_code: reasonCode });
  if (result === "ready") {
    console.log("Issue input accepted.");
  } else {
    console.log(`Issue input rejected: ${reasonCode}`);
  }
}

main().catch(() => {
  console.error("Issue input validation failed.");
  process.exitCode = 1;
});
