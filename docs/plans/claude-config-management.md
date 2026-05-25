# Claude Code 設定ファイルの dotfiles 管理

## 目的

Claude Code のユーザー設定（`settings.json`）とステータスライン表示スクリプト（`statusline-command.sh`）を dotfiles リポジトリで管理し、シンボリックリンクで `~/.claude/` に適用する。

## 対象ファイル

| dotfiles ソース | リンク先 |
|---|---|
| `ai/claude/settings.json` | `~/.claude/settings.json` |
| `ai/claude/statusline-command.sh` | `~/.claude/statusline-command.sh` |

## 変更内容

- `ai/claude/` ディレクトリを新設し、上記2ファイルを配置
- `Makefile` に `_link-claude-configs` / `_unlink-claude-configs` ターゲットを追加
- `_link-ai-configs` / `_unlink-ai-configs` から上記ターゲットを呼び出す
- `status` ターゲットに `[File-level: Claude configs]` セクションを追加
- `ai/README.md` にマッピングと除外ファイルの説明を追記

## 除外（管理しない）ファイル

- `history.jsonl`, `stats-cache.json`（自動生成）
- `backups/`, `cache/`, `sessions/` 等（自動生成ディレクトリ）
- `CLAUDE.md`（プロジェクト固有の指示ファイル、リポジトリルートで別管理）
- `skills/*.skill`（自動生成バイナリ）

## 適用方法

```sh
make link FORCE=1
```

既存の実ファイルを上書きしてシンボリックリンクを作成する。

## 検証コマンド

```sh
make check
make status
ls -la ~/.claude/settings.json ~/.claude/statusline-command.sh
```
