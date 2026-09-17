# AeroSpace: Cursor / Grok Bot のワークスペース自動配置

## Context

AeroSpace でウィンドウ管理を行っているが、Cursor と Grok Bot を起動するたびに手動でワークスペースへ移動する手間がある。

- Cursor → ワークスペース C（Claude / Codex と同じ AI 系）
- Grok Bot → ワークスペース G

## 対象環境

- **設定場所**: `config/aerospace/aerospace.toml`
- **ツール**: AeroSpace
- **対応OS**: macOS のみ
- **Cursor Bundle ID**: `com.todesktop.230313mzl4w4u92`
- **Grok Bot Bundle ID**: `com.anysphere.sand`

## 実装内容

### 変更ファイル

`config/aerospace/aerospace.toml`

### 追加ルール

```toml
[[on-window-detected]]
if.app-id = 'com.todesktop.230313mzl4w4u92'
run = 'move-node-to-workspace C'

[[on-window-detected]]
if.app-id = 'com.anysphere.sand'
run = 'move-node-to-workspace G'
```

### バリデーション

- `aerospace list-apps` で Bundle ID を確認
- `aerospace reload-config` でエラーなく反映されることを確認
