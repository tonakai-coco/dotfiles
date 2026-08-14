# AeroSpace: Hermes Studio をワークスペース S に自動配置する

## Context

AeroSpace でウィンドウ管理を行っているが、Hermes Studio を起動するたびに手動でワークスペース S に移動する手間があった。

ワークスペース S を Hermes Studio 専用として予約しているため、起動時に自動で配置したい。

## 対象環境

- **設定場所**: `config/aerospace/aerospace.toml`
- **ツール**: AeroSpace (https://github.com/nikitabobko/AeroSpace)
- **対応OS**: macOS のみ
- **Hermes Studio Bundle ID**: `com.hermeswebui.studio`

## 調査結果

1. AeroSpace の `on-window-detected` ルールで、アプリ起動時にワークスペースを自動振り分けできる
2. 既存のルール（Claude, Codex, Discord, WezTerm など）と同じパターンで記述可能
3. `persistent-workspaces` 配列には `S` が既に含まれている

## 実装内容

### 変更ファイル
`config/aerospace/aerospace.toml`

### 追加ルール
```toml
[[on-window-detected]]
if.app-id = 'com.hermeswebui.studio'
run = 'move-node-to-workspace S'
```

### バリデーション
- `aerospace reload-config` でエラーなく設定が反映されることを確認済み