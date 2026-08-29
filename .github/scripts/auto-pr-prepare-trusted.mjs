import { chmod, mkdir, writeFile } from "node:fs/promises";
import * as path from "node:path";

import {
  AutoPrError,
  getRepositoryHeadSha,
  getRepositoryRoot,
  runGit,
  validateCommitSha,
} from "./auto-pr-common.mjs";

const TRUSTED_SCRIPT_PATHS = [
  ".github/scripts/auto-pr-common.mjs",
  ".github/scripts/auto-pr-publish.mjs",
  ".github/scripts/auto-pr-validate.mjs",
];

function getRequiredEnvironment(name) {
  const value = process.env[name];
  if (typeof value !== "string" || value.length === 0) {
    throw new AutoPrError(`missing-environment-${name}`);
  }
  return value;
}

async function main() {
  const repositoryRoot = getRepositoryRoot();
  const expectedCommitSha = validateCommitSha(getRequiredEnvironment("AUTO_PR_BASE_SHA"));
  if (getRepositoryHeadSha(repositoryRoot) !== expectedCommitSha) {
    throw new AutoPrError("trusted-base-commit-mismatch");
  }

  const trustedDirectory = path.resolve(getRequiredEnvironment("AUTO_PR_TRUSTED_DIR"));
  await mkdir(trustedDirectory, { recursive: true, mode: 0o700 });
  await chmod(trustedDirectory, 0o700);

  for (const repositoryPath of TRUSTED_SCRIPT_PATHS) {
    const trustedContent = runGit(["show", `HEAD:${repositoryPath}`], repositoryRoot);
    const targetPath = path.join(trustedDirectory, path.basename(repositoryPath));
    await writeFile(targetPath, trustedContent, { encoding: "utf8", mode: 0o400 });
    await chmod(targetPath, 0o400);
  }

  await chmod(trustedDirectory, 0o500);
  console.log("Trusted PR scripts prepared from the pinned base commit.");
}

main().catch(() => {
  console.error("Trusted PR scripts could not be prepared.");
  process.exitCode = 1;
});
