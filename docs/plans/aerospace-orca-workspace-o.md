# AeroSpace: Orca をワークスペース O に自動配置する

## Context

AeroSpace でウィンドウ管理を行っているが、Orca を起動するたびに手動でワークスペース O に移動する手間があった。

ワークスペース O を Orca 専用として予約しているため、起動時に自動で配置したい。

## 対象環境

- **設定場所**: `config/aerospace/aerospace.toml`
- **ツール**: AeroSpace (https://github.com/nikitabobko/AeroSpace)
- **対応OS**: macOS のみ
- **Orca Bundle ID**: `com.stablyai.orca`

## 調査結果

1. AeroSpace の `on-window-detected` ルールで、アプリ起動時にワークスペースを自動振り分けできる
2. 既存のルール（Claude, Codex, Discord, WezTerm, Hermes Studio など）と同じパターンで記述可能
3. `persistent-workspaces` 配列には `O` が既に含まれている
4. `aerospace list-apps` と `defaults read /Applications/Orca.app/Contents/Info CFBundleIdentifier` で Bundle ID を確認済み

## 実装内容

### 変更ファイル
`config/aerospace/aerospace.toml`

### 追加ルール
```toml
[[on-window-detected]]
if.app-id = 'com.stablyai.orca'
run = 'move-node-to-workspace O'
```

### バリデーション
- この worktree の `config/aerospace` を `~/.config/aerospace` にリンクし直した
- `aerospace reload-config --dry-run` / `aerospace reload-config` が成功したことを確認済み
- 既存ウィンドウへの遡及適用は、利用中の AeroSpace に `run-callback` が無いため未実施（新規起動時に効く）
