# ai/

AI エージェントツールのカスタム設定を管理するディレクトリ。

## ディレクトリ構成

```
ai/
├── skills/                          # 共有スキル定義
│   └── git-commit-jp/
│       └── SKILL.md                 # 日本語コミットスキル
└── codex/
    └── hooks.json                   # Codex CLI の通知フック
```

## シンボリックリンクのマッピング

| dotfiles ソース | リンク先 |
|---------------|---------|
| `ai/skills/` | `~/.agents/skills/` |
| `ai/skills/git-commit-jp/` | `~/.claude/skills/git-commit-jp/` |
| `ai/codex/hooks.json` | `~/.codex/hooks.json` |

リンクは `make link`（macOS）で自動適用される。

## 除外ファイル

以下は機密・自動生成のため管理しない:

- 認証情報（`auth.json`, `oauth_creds.json` 等）
- セッションデータ・キャッシュ
- `~/.codex/rules/default.rules`（過去の承認操作を自動蓄積したファイル）
- `~/.claude/skills/*.skill`（スキルディレクトリの自動生成バイナリ）

## 新しいスキルを追加する場合

1. `ai/skills/<skill-name>/SKILL.md` を作成する
2. `make link FORCE=1` を実行してリンクを適用する
3. Claude Code と Codex で `/skill-name` として使用できることを確認する
