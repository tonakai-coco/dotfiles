# Claude Code（Windows）のキーバインド変更

## 目的

Claude Code のチャット入力で、Enter を改行、Ctrl+Enter を送信に変更する。
複数行のプロンプトを書いている途中で誤って送信するのを防ぐ。

## 変更ファイル

| ファイル | 内容 |
|---------|------|
| `ai/claude/windows/keybindings.json` | `~/.claude/keybindings.json` を dotfiles 管理下に追加 |
| `ai/README.md` | ディレクトリ構成とリンク管理表に追記 |

## 実装内容

`Chat` コンテキストに次を追加する。既存の `ctrl+alt+g`（Orca 連携）は維持する。

```json
"enter": "chat:newline",
"ctrl+enter": "chat:submit"
```

- `ctrl+enter` の既定動作 `chat:sendNow` は `chat:submit` で上書きする。
- Ctrl+Enter を Enter と区別できない端末では送信できなくなるため、その場合は `ctrl+x enter` など別キーに変える。

## 対象 OS

Windows のみ。macOS / Linux は変更しない。

## 検証

- `jq empty ai/claude/windows/keybindings.json` で JSON 構文を確認
- `Makefile` とリンク定義は変更していないため `make check` / `make status` は対象外
- AI 設定は手動コピー（またはシンボリックリンク）で適用する運用のため、`~/.claude/keybindings.json` への反映は手動
