# ai/

AI エージェントツールの設定ファイルを管理するディレクトリです。

スキル本体は `/Users/y_kashimura/Documents/ai-plugins` で管理します。このリポジトリにはスキルを重複して保持せず、必要なプロジェクトへ手動でコピーします。

## ディレクトリ構成

```
ai/
├── claude/
│   ├── settings.json                # Claude Code ユーザー設定（macOS / Linux）
│   ├── statusline-command.sh        # ステータスライン表示スクリプト（macOS / Linux）
│   └── windows/
│       ├── settings.json            # Claude Code ユーザー設定（Windows）
│       └── statusline-command.ps1   # ステータスライン表示スクリプト（Windows / pwsh）
├── codex/
│   ├── hooks.json                   # Codex CLI の通知フック（macOS / Linux）
│   └── windows/
│       └── hooks.json               # Codex CLI の通知フック（Windows）
└── copilot/
    ├── agents/                      # GitHub Copilot カスタムエージェント
    └── hooks/
        └── notify.json              # GitHub Copilot の通知フック（Windows）
```

## 設定ファイルのリンク管理

| dotfiles ソース | リンク先 | 対応OS |
|---------------|---------|--------|
| `ai/claude/settings.json` | `~/.claude/settings.json` | macOS / Linux |
| `ai/claude/statusline-command.sh` | `~/.claude/statusline-command.sh` | macOS / Linux |
| `ai/claude/windows/settings.json` | `~/.claude/settings.json` | Windows |
| `ai/claude/windows/statusline-command.ps1` | `~/.claude/statusline-command.ps1` | Windows |
| `ai/codex/hooks.json` | `~/.codex/hooks.json` | macOS / Linux |
| `ai/codex/windows/hooks.json` | `~/.codex/hooks.json` | Windows |
| `ai/copilot/agents/` | `~/.copilot/agents/` | Windows |
| `ai/copilot/hooks/notify.json` | `~/.copilot/hooks/notify.json` | Windows |

上記の非スキル設定・フックは `make link` で自動適用します。スキルについてはMakefileからリンクせず、`/Users/y_kashimura/Documents/ai-plugins` のplugin内スキルを必要なプロジェクトへ手動でコピーします。

## 除外ファイル

以下は機密・自動生成のため管理しない:

- 認証情報（`auth.json`, `oauth_creds.json` 等）
- セッションデータ・キャッシュ
- `~/.codex/rules/default.rules`（過去の承認操作を自動蓄積したファイル）
- `~/.claude/skills/*.skill`（スキルディレクトリの自動生成バイナリ）
- `~/.claude/history.jsonl`, `~/.claude/stats-cache.json`（自動生成データ）
- `~/.claude/CLAUDE.md`（プロジェクト固有の指示ファイル）

## スキルを追加・利用する場合

1. `/Users/y_kashimura/Documents/ai-plugins/plugins/<plugin-name>/skills/<skill-name>/` を更新する
2. 必要なプロジェクトへスキルディレクトリを手動でコピーする
3. 対象プロジェクト側でスキルが読み込まれることを確認する
