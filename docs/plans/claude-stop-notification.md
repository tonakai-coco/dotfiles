# Claude Code エージェント停止通知の追加

## 目的

Claude Code でエージェントの作業が停止した際（Stop イベント）に OS ネイティブ通知を表示する。
macOS / Linux（osascript）と Windows（BurntToast）の両プラットフォームに対応する。

## 変更ファイル

| ファイル | 内容 |
|---------|------|
| `ai/claude/settings.json` | macOS / Linux 向け Stop フックを追加 |
| `ai/claude/windows/settings.json` | Windows 向け Stop フックを追加 |

## 実装内容

### macOS / Linux（osascript）

```json
"hooks": {
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "osascript -e 'display notification \"Claude Codeのエージェント作業が停止しました\" with title \"Claude Code\" sound name \"Glass\"'"
        }
      ]
    }
  ]
}
```

### Windows（BurntToast）

```json
"hooks": {
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "powershell.exe -NoProfile -Command \"Import-Module BurntToast; New-BurntToastNotification -Text 'Claude Code', 'エージェントの作業が停止しました'\""
        }
      ]
    }
  ]
}
```

## Makefile への影響

なし。`_link-claude-configs` が既に両ファイルを `~/.claude/settings.json` へリンクする。

## 検証

- `jq . ai/claude/settings.json` — JSON バリデーション
- `jq . ai/claude/windows/settings.json` — JSON バリデーション
- `make check` — リンク構成の整合性確認
- 実環境での動作確認（Claude Code でタスク完了後に OS 通知が届くことを確認）
