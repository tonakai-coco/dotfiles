# CLAUDE.md

This file is a short entrypoint for Claude Code. Shared repository rules live in `docs/agent-guides/`.

## Read First

- `docs/agent-guides/core.md`
- `docs/agent-guides/validation.md`
- `docs/agent-guides/components.md`
- `config/AGENTS.md` when changing files under `config/`

## Repository Summary

- Cross-platform dotfiles for macOS, Linux, and Windows.
- Link management is centered on `Makefile`.
- Preserve OS separation and idempotent behavior.

## Required Workflow

- Confirm target OS and target directory before editing.
- Run `git branch --show-current` and `git status --short` before changes.
- Run validation commands for the changed paths.
- If `Makefile` or link definitions change, run `make check` and `make status`.
- Use Conventional Commits.
- Record reason, validation, and any skipped checks in the PR.
