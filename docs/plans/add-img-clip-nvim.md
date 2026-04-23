# Neovim Markdown 画像ペースト機能の調査・導入計画

## Context

NeovimでMarkdownファイルを編集中、クリップボードにコピーした画像（スクリーンショット等）を
Notionのようにペーストしたい。具体的には：

1. 画像をクリップボードにコピー
2. Neovimで `<leader>p` 等のキーを押す
3. `assets/` フォルダに画像ファイルが自動保存される
4. カーソル位置に `![](assets/画像名.png)` が挿入される

## 対象環境

- **設定場所**: `config/nvim/`
- **プラグインマネージャ**: lazy.nvim (LazyVim フレームワーク)
- **対応OS**: macOS / Linux (X11・Wayland) / Windows (WSL) - クロスプラットフォーム
- **既存のMarkdown関連プラグイン**: render-markdown.nvim, md-render.nvim, marksman LSP
- **画像系プラグイン**: 現在なし

## 調査結果：主要プラグイン比較

| プラグイン | メンテ状況 | 対応OS | ドラッグ＆ドロップ | 設定の柔軟性 | 推奨度 |
|-----------|-----------|--------|-------------------|------------|--------|
| **img-clip.nvim** | ✅ 活発 (2025/02) | Linux/macOS/Win/WSL | ✅ あり | ✅ 高い | ★★★★★ |
| pastify.nvim | 不明 | Linux/macOS/Win | ❌ なし | ✅ 高い | ★★★★ |
| clipboard-image.nvim | 不明 | Linux/macOS/Win | ❌ なし | ✅ 中程度 | ★★★ |
| pinmd.nvim | 普通 | Linux/macOS | ❌ なし | ✅ 中程度 | ★★ |

## 推奨プラグイン: img-clip.nvim

**GitHub**: `HakonHarnes/img-clip.nvim`

### 選定理由
- 最もアクティブにメンテされている（2025年2月にv0.6.0リリース）
- クロスプラットフォーム対応（既存dotfilesの方針と合致）
- ドラッグ＆ドロップ対応（クリップボード以外からも挿入可能）
- lazy.nvim ネイティブサポート
- LazyVim との統合実績あり（snacks.nvim との連携も可）
- `.img-clip.lua` でプロジェクト別設定も可能

### プラットフォーム別の依存ツール
- **Linux (X11)**: `xclip`
- **Linux (Wayland)**: `wl-clipboard`
- **macOS**: `pngpaste`
- **Windows/WSL**: 追加依存なし

## 実装内容

### 新規ファイル
`config/nvim/lua/plugins/img-paste.lua`

```lua
return {
  "HakonHarnes/img-clip.nvim",
  event = "VeryLazy",
  keys = {
    { "<leader>pi", "<cmd>PasteImage<cr>", desc = "Paste image from clipboard" },
  },
  opts = {
    default = {
      dir_path = "assets",
      file_name = "%Y%m%d%H%M%S",
      url_encode_path = true,
      use_absolute_path = false,
    },
    filetypes = {
      markdown = {
        dir_path = "assets",
        template = "![$CURSOR]($FILE_PATH)",
      },
    },
  },
}
```

### キーバインド
- `<leader>pi` → `:PasteImage` (i = image)
- 既存の `<leader>p` は yanky.nvim (yank history) に使われているため競合を避ける

## 検証手順

1. `lazy.nvim` でプラグインをインストール（`:Lazy sync`）
2. `:checkhealth img-clip` で依存ツールの確認
3. スクリーンショットをクリップボードにコピー
4. Markdownファイルを開いて `<leader>pi` を押す
5. `assets/` フォルダに画像が保存されることを確認
6. カーソル位置に `![](assets/YYYYMMDDHHMMSS.png)` が挿入されることを確認

## 作業ファイル

| ファイル | 操作 |
|---------|------|
| `config/nvim/lua/plugins/img-paste.lua` | 新規作成 |

既存ファイルの変更は不要（新ファイル追加のみ）。
