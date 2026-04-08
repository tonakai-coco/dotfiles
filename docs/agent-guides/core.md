# Agent Guide: Core Rules

このディレクトリをエージェント向け正本とする。`AGENTS.md` `CLAUDE.md` `.github/copilot-instructions.md` は入口だけを持つ。

## Scope

- 対象は macOS / Linux / Windows 対応の dotfiles 管理。
- 管理の中心は `Makefile` のシンボリックリンク処理。
- 変更前に対象 OS と変更対象ディレクトリを明確化する。

## Non-Negotiables

- 1 つの変更で目的を 1 つに絞る。
- 既存の設計方針である OS 分離と idempotent を崩さない。
- OS 固有変更は対象外 OS に副作用を出さない。
- 既存ファイルを壊さないため、対応する検証コマンドを必ず実行する。
- 認証情報、トークン、秘密鍵をコミットしない。
- 変更理由をコミットメッセージと PR 本文に明記する。

## Start Checklist

- `git branch --show-current`
- `git status --short`
- 変更対象が `config/` 配下のどこかを確認する。
- 変更が OS 固有か共通かを先に判断する。

## Makefile Rules

- リンク管理コマンドは `make link` `make link FORCE=1` `make status` `make unlink` `make check` を使う。
- リンク定義を変更した場合は `make check` と `make status` を実行する。
- 強制上書きはローカル検証時のみ使い、理由を PR に書く。
- idempotent 確認が必要な変更では同じコマンドを 2 回実行して破綻しないことを確認する。

## OS Ownership

- 全 OS 共通: `config/wezterm/`
- macOS: `config/nvim/` `config/aerospace/` `config/tmux/` `config/fish/` `config/karabiner/`
- Linux: `config/nvim/` `config/ubuntu_nvim/` `config/tmux/`
- Windows: `config/powershell/` `config/nvim/`

## Review And Finish

- フォーマット済みで構文エラーがない。
- 既存命名規則を壊していない。
- 既存ディレクトリ責務を壊していない。
- `git diff -- <path>` で意図した差分だけを確認する。
- Conventional Commits を使う。
- PR には「変更内容 / 検証結果 / 未実施項目」を書く。
