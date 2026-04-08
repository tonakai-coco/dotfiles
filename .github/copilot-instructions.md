# GitHub Copilot Instructions

Shared repository rules live in `docs/agent-guides/`. Keep this file short and use it as an entrypoint only.

## Read First

- `docs/agent-guides/core.md`
- `docs/agent-guides/validation.md`
- `docs/agent-guides/components.md`
- `config/AGENTS.md` for changes under `config/`

## Working Rules

- Confirm the target OS and target directory before editing.
- Keep OS-specific logic isolated to existing files or directories.
- Preserve idempotent link behavior managed by `Makefile`.
- Run validation commands that match the changed paths.
- If `Makefile` or link definitions change, run `make check` and `make status`.
- Use Conventional Commits and document validation in the PR.
