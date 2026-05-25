# ai/

AI エージェントツールのカスタム設定を管理するディレクトリ。

## ディレクトリ構成

```
ai/
├── skills/                          # 共有スキル定義
│   └── git-commit-jp/
│       └── SKILL.md                 # 日本語コミットスキル
├── claude/
│   ├── settings.json                # Claude Code ユーザー設定
│   └── statusline-command.sh        # ステータスライン表示スクリプト
├── codex/
│   └── hooks.json                   # Codex CLI の通知フック（macOS）
└── copilot/
    └── hooks/
        └── notify.json              # GitHub Copilot の通知フック（Windows）
```

## シンボリックリンクのマッピング

| dotfiles ソース | リンク先 |
|---------------|---------|
| `ai/skills/` | `~/.agents/skills/` |
| `ai/claude/settings.json` | `~/.claude/settings.json` |
| `ai/claude/statusline-command.sh` | `~/.claude/statusline-command.sh` |
| `ai/codex/hooks.json` | `~/.codex/hooks.json` |
| `ai/copilot/hooks/notify.json` | `~/.copilot/hooks/notify.json` |

リンクは `make link` で自動適用される（macOS / Linux / Windows 対応）。
Claude Code は `~/.agents/skills/` を参照するため、`~/.claude/skills/` への個別リンクは不要。

## 除外ファイル

以下は機密・自動生成のため管理しない:

- 認証情報（`auth.json`, `oauth_creds.json` 等）
- セッションデータ・キャッシュ
- `~/.codex/rules/default.rules`（過去の承認操作を自動蓄積したファイル）
- `~/.claude/skills/*.skill`（スキルディレクトリの自動生成バイナリ）
- `~/.claude/history.jsonl`, `~/.claude/stats-cache.json`（自動生成データ）
- `~/.claude/CLAUDE.md`（プロジェクト固有の指示ファイル）

## 新しいスキルを追加する場合

1. `ai/skills/<skill-name>/SKILL.md` を作成する
2. `make link FORCE=1` を実行してリンクを適用する
3. Claude Code と Codex で `/skill-name` として使用できることを確認する
