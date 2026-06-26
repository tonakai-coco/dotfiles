# Neovim 設定

LazyVim ベースの Neovim 設定です。`init.lua` で lazy.nvim / LazyVim を読み込み、`lua/config/` と `lua/plugins/` にローカル設定を分離しています。

## 構成

| パス | 役割 |
|---|---|
| `init.lua` | エントリポイント。通常の Neovim と VS Code Neovim を分岐する |
| `lua/config/lazy.lua` | LazyVim と extras、ローカル plugin の読み込み |
| `lua/config/options.lua` | 共通 option |
| `lua/config/keymaps.lua` | 共通 keymap |
| `lua/config/autocmds.lua` | 共通 autocmd |
| `lua/config/macos.lua` | macOS 固有設定 |
| `lua/config/windows.lua` | Windows 固有設定 |
| `lua/config/wsl.lua` | WSL 固有設定 |
| `lua/config/vscode_keymap.lua` | VS Code Neovim 用 keymap |
| `lua/plugins/*.lua` | LazyVim plugin の追加・上書き |

## OS 分岐

OS 固有設定は `init.lua` の判定から専用ファイルを読み込みます。

- macOS: `lua/config/macos.lua`
- Windows: `lua/config/windows.lua`
- WSL: `lua/config/wsl.lua`

OS 固有の変更は共通ファイルへ混ぜず、上記の専用ファイルか plugin 側の局所分岐に閉じ込めます。

## Markdown 関連

Markdown では LazyVim の `lazyvim.plugins.extras.lang.markdown` に加えて、次のローカル plugin を管理しています。

| ファイル | Plugin | 用途 |
|---|---|---|
| `lua/plugins/md-render.lua` | `delphinus/md-render.nvim` | Markdown のターミナル内プレビュー |
| `lua/plugins/img-paste.lua` | `HakonHarnes/img-clip.nvim` | クリップボード画像を `assets/` に保存して Markdown link を挿入 |
| `lua/plugins/markview.lua` | `OXY2DEV/markview.nvim` | Markdown 表示系 plugin の無効化設定 |

`img-clip.nvim` は環境により外部コマンドが必要です。

- macOS: `pngpaste`
- Linux X11: `xclip`
- Linux Wayland: `wl-clipboard`
- Windows / WSL: plugin 側の対応に従う

## 検証

変更内容に応じて、リポジトリルートから実行します。

```sh
stylua --config config/nvim/stylua.toml config/nvim/lua/**/*.lua
nvim --headless "+checkhealth" +qa
```

plugin 追加や lockfile 更新が必要な場合は、必要に応じて次も実行します。

```sh
nvim --headless "+Lazy sync" +qa
```
