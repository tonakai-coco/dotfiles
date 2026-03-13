# AGENTS.md

このファイルは、このリポジトリで作業するエージェント向けの実行手順書です。
説明よりも、実際の作業指示を優先してください。

## 0. 基本方針

- 変更前に、対象OSと変更対象ディレクトリを明確化する。
- 1つの変更で目的を1つに絞る。
- 既存の設計（OS分離・idempotent）を崩さない。
- 既存ファイルを壊さないため、検証コマンドを必ず実行する。
- 変更理由をコミットメッセージとPR本文に明記する。

## 1. リポジトリ概要

- このリポジトリは macOS / Linux / Windows 対応の dotfiles 管理。
- 管理の中心は `Makefile` のシンボリックリンク処理。
- 主要ディレクトリ:
  - `config/nvim/` : Neovim 設定（LazyVimベース）
  - `config/wezterm/` : WezTerm 設定
  - `config/fish/` : Fish 設定（主に macOS）
  - `config/tmux/` : Tmux 設定（macOS/Linux）
  - `config/aerospace/` : AeroSpace 設定（macOS）
  - `config/karabiner/` : Karabiner 設定（macOS）
  - `config/powershell/` : PowerShell 設定（Windows）
  - `config/ubuntu_nvim/` : Ubuntu向け Vim 設定（レガシー）

## 2. 作業開始チェック

- 現在ブランチ確認:
  - `git branch --show-current`
- 差分確認:
  - `git status --short`
- 変更ファイルの位置確認:
  - `rg --files config | head`
- 変更対象が OS 固有かを先に判断する。

## 3. リンク管理（Makefile）

- OS自動判定でリンク作成:
  - `make link`
- 既存ファイルを強制上書き:
  - `make link FORCE=1`
- リンク状態確認:
  - `make status`
- リンク削除:
  - `make unlink`
- OS検出結果確認:
  - `make check`

実施ルール:

- リンク定義を変更した場合は `make check` と `make status` を実行する。
- 強制上書きはローカル検証時のみ使用し、実行理由をPRに記載する。
- idempotent であること（2回実行しても破綻しないこと）を確認する。

## 4. OS別の管理対象

- 全OS共通:
  - `wezterm`
- macOS:
  - `nvim`
  - `aerospace`
  - `tmux`
  - `fish`（ファイルレベル）
  - `karabiner`（ファイルレベル）
- Linux:
  - `nvim`
  - `ubuntu_nvim`
  - `tmux`
- Windows:
  - `powershell`
  - `nvim`（`$LOCALAPPDATA/nvim`）

運用ルール:

- OS固有の変更は、対象外OSへ副作用を出さない。
- 条件分岐は既存のOS判定パターンに合わせる。

## 5. Neovim / Lua 変更ルール

- インデントは 2 スペース。
- 1行 120 文字以内を維持。
- フォーマットは `stylua.toml` 設定に従う。
- 命名は `snake_case` を使用。
- OS分岐は専用ファイルへ分離する。

OS分岐ファイル:

- `lua/config/macos.lua`
- `lua/config/windows.lua`
- `lua/config/wsl.lua`

推奨OS判定パターン（WezTerm/Lua）:

```lua
local is_mac = wezterm.target_triple:find("darwin")
local is_windows = wezterm.target_triple:find("windows")
```

## 6. コンポーネント別の検証コマンド

### 6.1 Neovim

- プラグイン同期:
  - `nvim --headless "+Lazy sync" +qa`
- Luaフォーマット:
  - `stylua --config config/nvim/stylua.toml config/nvim/lua/**/*.lua`
- ヘルスチェック:
  - `nvim --headless "+checkhealth" +qa`

実施基準:

- `config/nvim/` を変更したら、最低でもフォーマットとヘルスチェックを実行する。

### 6.2 Fish

- 整形:
  - `fish_indent --write config/fish/functions/*.fish`

実施基準:

- `config/fish/functions/*.fish` を変更したら必ず実行する。

### 6.3 Karabiner

- JSON検証:
  - `jq empty config/karabiner/numpad.json`

実施基準:

- `config/karabiner/*.json` を変更したら全対象ファイルに対して `jq empty` を実行する。

### 6.4 WezTerm

- 起動確認:
  - `wezterm --config-file config/wezterm/wezterm.lua start --always-new-process`

実施基準:

- `config/wezterm/` を変更したら実行する。
- GUI起動不可環境では、未実施理由を記録する。

### 6.5 Tmux

- 設定リロード:
  - `tmux source-file ~/.config/tmux/tmux.conf`

実施基準:

- `config/tmux/` を変更したら実行する。
- tmuxセッションがない場合は、未実施理由を記録する。

## 7. レビュー観点（必須チェックリスト）

- 変更が対象OSに限定されている。
- 非対象OSの設定・リンクに影響していない。
- Makefileの挙動がidempotent。
- フォーマット済みである。
- 構文エラーがない。
- ハードコードされた秘密情報がない。
- 既存命名規則（snake_case）に従っている。
- 既存のディレクトリ責務を壊していない。

## 8. セキュリティ

- 認証情報・トークン・秘密鍵をコミットしない。
- 機密情報は `.gitignore` 対象ファイルへ保存する。
- サンプル値を使う場合は実運用値を置かない。

## 9. 変更手順テンプレート

1. `git status --short` で作業前の状態確認。
2. 変更対象ファイルを編集。
3. 対象コンポーネントの整形・検証を実行。
4. Makefile またはリンク定義を変更した場合は `make check` と `make status` を実行。
5. `git diff -- <path>` で差分確認。
6. `git add <path>` で必要ファイルのみステージ。
7. Conventional Commits 形式でコミット。
8. PR本文に「変更内容 / 検証結果 / 既知の未実施項目」を記載。

## 10. コミット規約

- Conventional Commits を使用:
  - `feat:`
  - `fix:`
  - `chore:`
  - `refactor:`
  - `docs:`
- 件名は簡潔に 1 行で目的を示す。
- 破壊的変更は本文で明示する。

例:

- `docs: add AGENTS.md from CLAUDE.md guidance`
- `fix(wezterm): isolate mac keybind handling`
- `refactor(nvim): split os-specific bootstrap logic`

## 11. PR本文テンプレート

- 概要:
  - 何を、なぜ変更したかを 2〜4 行で記載。
- 変更ファイル:
  - 主要ファイルを箇条書き。
- 検証:
  - 実行コマンドと結果（成功/未実施理由）を列挙。
- 影響範囲:
  - OS別に影響有無を明記。
- 懸念点:
  - 未解決事項や追加確認が必要な点を列挙。

## 12. Claude 固有情報の扱い

- Claude 専用ディレクトリや専用メモリ機能を前提にしない。
- 他エージェントで再現できない運用は、注記として扱う。
- 本ドキュメントはツール非依存の実行手順のみを保持する。

## 13. skills 化を検討する定型手順（提案）

- `skill: dotfiles-validation`
  - 変更パスに応じて検証コマンドを自動選択・実行。
- `skill: os-impact-check`
  - 変更差分からOS影響範囲を自動レビュー。
- `skill: make-link-smoke-test`
  - `make check/status/link` の反復テストを定型化。
- `skill: commit-pr-writer`
  - Conventional Commit とPRテンプレート生成を支援。

## 14. 非機能要件

- 手順は短い箇条書きを優先する。
- 曖昧表現を使わない。
- 例外がある場合は「条件」と「代替手順」を明記する。
- 将来の自動化を想定し、コマンドをそのまま実行可能な形で記載する。

## 15. 最低限の完了条件

- 変更ファイルが意図通りである。
- 対応する検証コマンドを実行済みである。
- 未実施項目には理由が記録されている。
- コミットメッセージが規約に準拠している。
- PR本文に変更理由と検証結果が記載されている。

## 16. Skills

A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of
skills that can be used. Each entry includes a name, description, and file path so you can open the source for
full instructions when using a specific skill.

### Available skills

- openai-docs: Use when the user asks how to build with OpenAI products or APIs and needs up-to-date official
  documentation with citations, help choosing the latest model for a use case, or explicit GPT-5.4 upgrade and
  prompt-upgrade guidance; prioritize OpenAI docs MCP tools, use bundled references only as helper context, and
  restrict any fallback browsing to official OpenAI domains. (file:
  `/Users/y_kashimura/.codex/skills/.system/openai-docs/SKILL.md`)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new
  skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows,
  or tool integrations. (file: `/Users/y_kashimura/.codex/skills/.system/skill-creator/SKILL.md`)
- skill-installer: Install Codex skills into `$CODEX_HOME/skills` from a curated list or a GitHub repo path. Use
  when a user asks to list installable skills, install a curated skill, or install a skill from another repo
  (including private repos). (file: `/Users/y_kashimura/.codex/skills/.system/skill-installer/SKILL.md`)

### How to use skills

- Discovery: The list above is the skills available in this session (name + description + file path). Skill
  bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a
  skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all.
  Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue
  with the best fallback.
- How to use a skill (progressive disclosure):
  1. After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2. When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill
     directory listed above first, and only consider other paths if needed.
  3. If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the
     request; don't bulk-load everything.
  4. If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5. If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use
    them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're
    blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that
    choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the
  issue, pick the next-best approach, and continue.
