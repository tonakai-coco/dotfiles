# AGENTS.md

このリポジトリのエージェント向け入口。詳細ルールの正本は `docs/agent-guides/` に置く。

## 変更前に確認すること

- 対象 OS と変更対象ディレクトリを明確化する。
- `git branch --show-current`
- `git status --short`
- 変更が OS 固有か共通かを先に判断する。

## 必須ルール

- 1 つの変更で目的を 1 つに絞る。
- OS 分離と idempotent を崩さない。
- OS 固有変更は対象外 OS に副作用を出さない。
- 変更したパスに対応する検証コマンドを必ず実行する。
- `Makefile` やリンク定義を変えたら `make check` と `make status` を実行する。
- 強制上書きは `make link FORCE=1` をローカル検証時だけで使い、理由を PR に書く。
- 認証情報、トークン、秘密鍵をコミットしない。
- Conventional Commits を使う。
- PR に変更理由、検証結果、未実施項目を書く。

## 参照先

- 共通方針: `docs/agent-guides/core.md`
- 検証コマンド: `docs/agent-guides/validation.md`
- コンポーネント規約: `docs/agent-guides/components.md`
- `config/` 配下の補足: `config/AGENTS.md`
- Claude 向け入口: `CLAUDE.md`
- GitHub Copilot 向け入口: `.github/copilot-instructions.md`

## 対象ディレクトリ

- 全 OS 共通: `config/wezterm/`
- macOS: `config/nvim/` `config/aerospace/` `config/tmux/` `config/fish/` `config/karabiner/`
- Linux: `config/nvim/` `config/ubuntu_nvim/` `config/tmux/`
- Windows: `config/powershell/` `config/nvim/`
