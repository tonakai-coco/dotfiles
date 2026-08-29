import { appendFile, copyFile, mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import * as path from "node:path";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";

import {
  AutoPrError,
  getRepositoryRoot,
  getWorkingTreePaths,
  runGit,
} from "./auto-pr-common.mjs";

const VALIDATION_NAMES = Object.freeze({
  nvimFormat: "nvim-format",
  nvimHealth: "nvim-health",
  fishIndent: "fish-indent",
  karabinerJson: "karabiner-json",
  weztermStart: "wezterm-start",
  tmuxSource: "tmux-source",
});

function hasPrefix(repositoryPath, prefix) {
  return repositoryPath === prefix || repositoryPath.startsWith(`${prefix}/`);
}

export function getValidationPlan(changedPaths) {
  if (!Array.isArray(changedPaths) || changedPaths.some((repositoryPath) => typeof repositoryPath !== "string")) {
    throw new AutoPrError("validation-paths-invalid");
  }

  const plan = [];
  if (changedPaths.some((repositoryPath) => hasPrefix(repositoryPath, "config/nvim"))) {
    plan.push(VALIDATION_NAMES.nvimFormat, VALIDATION_NAMES.nvimHealth);
  }
  if (changedPaths.some((repositoryPath) => hasPrefix(repositoryPath, "config/fish"))) {
    plan.push(VALIDATION_NAMES.fishIndent);
  }
  if (changedPaths.some((repositoryPath) => /^config\/karabiner\/[^/]+\.json$/u.test(repositoryPath))) {
    plan.push(VALIDATION_NAMES.karabinerJson);
  }
  if (changedPaths.some((repositoryPath) => hasPrefix(repositoryPath, "config/wezterm"))) {
    plan.push(VALIDATION_NAMES.weztermStart);
  }
  if (changedPaths.some((repositoryPath) => hasPrefix(repositoryPath, "config/tmux"))) {
    plan.push(VALIDATION_NAMES.tmuxSource);
  }
  return plan;
}

function runCommand(name, command, args, repositoryRoot, options = {}) {
  const result = spawnSync(command, args, {
    cwd: repositoryRoot,
    env: options.env || process.env,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    timeout: options.timeout ?? 120000,
    killSignal: "SIGTERM",
  });

  if (result.error || result.status !== 0) {
    const stderr = typeof result.stderr === "string" ? result.stderr : "";
    const guiUnavailable =
      result.error?.code === "ENOENT" ||
      result.error?.code === "ETIMEDOUT" ||
      /display|wayland|x11|window server|gui|headless/iu.test(stderr);
    if (options.optional && guiUnavailable) {
      return { ok: false, reason: options.skipReason };
    }
    throw new AutoPrError(`component-validation-failed-${name}`);
  }
  return { ok: true };
}

function getTrackedLuaFiles(repositoryRoot) {
  return runGit(["ls-files", "--", "config/nvim"], repositoryRoot)
    .replace(/\r\n?/gu, "\n")
    .split("\n")
    .filter((repositoryPath) => repositoryPath.endsWith(".lua"));
}

async function runNvimFormatValidation(repositoryRoot) {
  const luaFiles = getTrackedLuaFiles(repositoryRoot);
  if (luaFiles.length === 0) {
    return;
  }
  runCommand(
    VALIDATION_NAMES.nvimFormat,
    "stylua",
    ["--check", "--config", "config/nvim/stylua.toml", ...luaFiles],
    repositoryRoot,
  );
}

async function runFishIndentValidation(repositoryRoot, changedPaths) {
  const fishFiles = changedPaths.filter((repositoryPath) => hasPrefix(repositoryPath, "config/fish") && repositoryPath.endsWith(".fish"));
  if (fishFiles.length === 0) {
    return;
  }

  const temporaryDirectory = await mkdtemp(path.join(tmpdir(), "auto-pr-fish-validation-"));
  try {
    const temporaryFiles = [];
    for (const repositoryPath of fishFiles) {
      const temporaryPath = path.join(temporaryDirectory, repositoryPath);
      await mkdir(path.dirname(temporaryPath), { recursive: true });
      await copyFile(path.join(repositoryRoot, repositoryPath), temporaryPath);
      temporaryFiles.push(temporaryPath);
    }
    const originalContents = await Promise.all(temporaryFiles.map((temporaryPath) => readFile(temporaryPath, "utf8")));
    runCommand(VALIDATION_NAMES.fishIndent, "fish_indent", ["--write", ...temporaryFiles], repositoryRoot);
    const formattedContents = await Promise.all(temporaryFiles.map((temporaryPath) => readFile(temporaryPath, "utf8")));
    if (formattedContents.some((content, index) => content !== originalContents[index])) {
      throw new AutoPrError("component-validation-failed-fish-indent");
    }
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true });
  }
}

function runKarabinerValidation(repositoryRoot, changedPaths) {
  for (const repositoryPath of changedPaths.filter((candidate) => /^config\/karabiner\/[^/]+\.json$/u.test(candidate))) {
    runCommand(VALIDATION_NAMES.karabinerJson, "jq", ["empty", repositoryPath], repositoryRoot);
  }
}

function runWeztermValidation(repositoryRoot) {
  return runCommand(
    VALIDATION_NAMES.weztermStart,
    "wezterm",
    ["--config-file", "config/wezterm/wezterm.lua", "start", "--always-new-process"],
    repositoryRoot,
    {
      optional: true,
      skipReason: "GUIを起動できないCI環境のため未実施",
      timeout: 30000,
    },
  );
}

function runTmuxValidation(repositoryRoot) {
  const environment = { ...process.env };
  try {
    runCommand(VALIDATION_NAMES.tmuxSource, "tmux", ["start-server"], repositoryRoot, { env: environment });
    const tmuxConfig = path.join(environment.HOME || process.env.HOME || "", ".config", "tmux", "tmux.conf");
    runCommand(VALIDATION_NAMES.tmuxSource, "tmux", ["source-file", tmuxConfig], repositoryRoot, { env: environment });
  } finally {
    spawnSync("tmux", ["kill-server"], {
      cwd: repositoryRoot,
      env: environment,
      stdio: "ignore",
    });
  }
}

async function writeValidationSummary(results) {
  const summaryPath = process.env.GITHUB_STEP_SUMMARY;
  if (!summaryPath) {
    return;
  }

  const lines = ["", "## 変更対象別の検証", ...results.map((result) => `- ${result.name}: ${result.status}`), ""];
  await appendFile(summaryPath, `${lines.join("\n")}\n`, "utf8");
}

async function main() {
  const repositoryRoot = getRepositoryRoot();
  const changedPaths = getWorkingTreePaths(repositoryRoot);
  const plan = getValidationPlan(changedPaths);
  const results = [];

  for (const name of plan) {
    if (name === VALIDATION_NAMES.nvimFormat) {
      await runNvimFormatValidation(repositoryRoot);
      results.push({ name, status: "成功" });
    } else if (name === VALIDATION_NAMES.nvimHealth) {
      runCommand(name, "nvim", ["--headless", "+checkhealth", "+qa"], repositoryRoot);
      results.push({ name, status: "成功" });
    } else if (name === VALIDATION_NAMES.fishIndent) {
      await runFishIndentValidation(repositoryRoot, changedPaths);
      results.push({ name, status: "成功" });
    } else if (name === VALIDATION_NAMES.karabinerJson) {
      runKarabinerValidation(repositoryRoot, changedPaths);
      results.push({ name, status: "成功" });
    } else if (name === VALIDATION_NAMES.weztermStart) {
      const result = runWeztermValidation(repositoryRoot);
      results.push({ name, status: result.ok ? "成功" : `未実施: ${result.reason}` });
    } else if (name === VALIDATION_NAMES.tmuxSource) {
      runTmuxValidation(repositoryRoot);
      results.push({ name, status: "成功" });
    }
  }

  if (results.length === 0) {
    results.push({ name: "該当する文書化済みコンポーネント検証", status: "対象なし" });
  }
  await writeValidationSummary(results);
  console.log(`Component validation completed: ${results.length} checks.`);
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  main().catch(() => {
    console.error("Component validation failed.");
    process.exitCode = 1;
  });
}
