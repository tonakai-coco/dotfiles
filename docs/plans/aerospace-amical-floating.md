# AeroSpace: Amical を floating にする

## Context

Fn キーで Amical を前面に出したあと閉じると、macOS が別ウィンドウ（例: Notion）にフォーカスを戻し、AeroSpace がそのワークスペースへ追従して画面が飛ぶことがある。

Amical のウィンドウがタイル配置に食い込んでいることが確認できたため、検出時に floating にする。

## 対象環境

- **設定場所**: `config/aerospace/aerospace.toml`
- **ツール**: AeroSpace
- **対応OS**: macOS のみ
- **Amical Bundle ID**: `com.amical.desktop`

## 調査結果

1. システム設定の「🌐キーを押して」は既に「何もしない」
2. `aerospace list-apps` で Bundle ID `com.amical.desktop` を確認
3. Amical ウィンドウに `layout=h_tiles` と `layout=floating` が混在
4. Notion は `move-node-to-workspace N` 済みのため、フォーカス復帰時に `N` へ飛びやすい
5. `~/.config/aerospace` が削除済み worktree への壊れたシンボリックリンクになっていた

## 実装内容

### 変更ファイル

`config/aerospace/aerospace.toml`

### 追加ルール

```toml
[[on-window-detected]]
if.app-id = 'com.amical.desktop'
run = 'layout floating'
```

### リンク修復

`make link FORCE=1` で `~/.config/aerospace` をこの worktree の `config/aerospace` に付け直す。

### バリデーション

- `make check` / `make status`
- `aerospace reload-config`
- 必要なら `aerospace list-windows --all` で Amical の layout を確認
