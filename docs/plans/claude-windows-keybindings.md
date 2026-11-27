# Claude Code（Windows）のキーバインド変更

## 目的

Claude Code のチャット入力で、Enter を改行、Ctrl+Enter を送信に変更する。
複数行のプロンプトを書いている途中で誤って送信するのを防ぐ。

## 変更ファイル

| ファイル | 内容 |
|---------|------|
| `ai/claude/windows/keybindings.json` | `~/.claude/keybindings.json` を dotfiles 管理下に追加 |
| `ai/README.md` | ディレクトリ構成とリンク管理表に追記、適用方法を更新 |
| `Makefile` | Windows の Claude Code 設定を `make link` / `unlink` / `status` で扱う。`_create-link` のリンク先比較を修正 |

## Makefile の変更

- `CLAUDE_WINDOWS_FILES`（`settings.json` `statusline-command.ps1` `keybindings.json`）を `~/.claude/` へファイル単位でリンクする
- `link-windows` / `unlink-windows` / `status` に Claude Code 用の処理を追加する
- `_create-link` で既存リンクの比較に `-ef` を追加する。Windows では `readlink` が `/c/PROJ/...` を返し、`SRC` が `C:/PROJ/...` になるため文字列比較が一致せず、毎回リンクを作り直していた

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
- `make check` / `make status` を実行し、Claude Code の3ファイルが `[LINK]` になることを確認
- `make _link-claude-windows-files FORCE=1` で既存の通常ファイル `~/.claude/keybindings.json` をリンクに置き換え
- `make link-windows` を再実行し、全リンクが `[OK] Already linked` になること（冪等性）を確認
