# Config Subtree Guide

このディレクトリは実際の設定資産を置く。共通ルールは `../docs/agent-guides/` を正本とする。

## この配下で特に守ること

- OS 固有変更は既存の専用ディレクトリか専用ファイルに閉じ込める。
- 既存のディレクトリ責務を壊さない。
- 検証コマンドは `../docs/agent-guides/validation.md` に従う。
- 実装プランは `../docs/plans/<task-name>.md` に保存してからコミットする。

## 主要ディレクトリ

- `nvim/`: LazyVim ベース
- `wezterm/`: 全 OS 共通の端末設定
- `fish/`: 主に macOS
- `tmux/`: macOS / Linux
- `aerospace/` `karabiner/`: macOS
- `powershell/` `autohotkey/`: Windows
- `ubuntu_nvim/`: Linux 向けレガシー Vim
