# Plan: Add md-render.nvim as a Neovim Plugin

## Context

ユーザーが https://github.com/delphinus/md-render.nvim をNeovimプラグインとして追加するよう依頼。
このプラグインはMarkdownをターミナル上でリッチ表示するレンダラー（フローティングウィンドウ/タブ/ページャー対応）。

現在のリポジトリはLazyVimベースで、lazy.nvimを使ってプラグインを管理している。
`config/nvim/lua/plugins/` 以下に機能別ファイルが存在し、同名の無効化済みmarkdownプラグイン `markview.lua` がすでにある。

## 変更対象ファイル

**新規作成:**
- `config/nvim/lua/plugins/md-render.lua`

**変更なし:**
- `config/nvim/lua/config/lazy.lua` — `{ import = "plugins" }` ディレクティブですべての plugins/*.lua を自動ロードするため変更不要

## キーバインド競合確認

調査した範囲で `<leader>m` 系バインドは以下のみ:

| キー | プラグイン | 用途 |
|------|-----------|------|
| `<leader>cp` | markdown-preview.nvim (LazyVim extra) | Markdown Preview Toggle |
| `<leader>um` | render-markdown.nvim (LazyVim extra) | Render Markdown Toggle |

**`<leader>mp`・`<leader>mt`・`<leader>md` はいずれも競合なし。**

## 実装内容

`config/nvim/lua/plugins/md-render.lua` を以下の内容で新規作成:

```lua
return {
  {
    "delphinus/md-render.nvim",
    ft = "markdown",
    dependencies = {
      "nvim-tree/nvim-web-devicons",
      { "delphinus/budoux.lua" },
    },
    keys = {
      { "<leader>mp", "<Plug>(md-render-preview)", desc = "Preview (toggle)" },
      { "<leader>mt", "<Plug>(md-render-preview-tab)", desc = "Preview in tab" },
      { "<leader>md", "<Plug>(md-render-demo)", desc = "Demo" },
    },
  },
}
```

### 設計上のポイント

- `ft = "markdown"` でMarkdownファイル時のみロード（遅延ロード）
- `version = false` がdefaultsで設定済みのため、明示不要
- `nvim-web-devicons` はすでに他プラグインの依存として存在するため重複ロードにはならない
- `budoux.lua` はCJK向け行分割ライブラリ（オプション依存だが追加して機能を有効化）
- キーバインドは公式READMEの推奨通り

## 検証手順

1. stylua でフォーマット確認:
   ```
   stylua --config config/nvim/stylua.toml config/nvim/lua/plugins/md-render.lua
   ```
2. Neovim ヘルスチェック:
   ```
   nvim --headless "+checkhealth" +qa
   ```

## 結果

- PR: https://github.com/tonakai-coco/dotfiles/pull/17
- CI: success
