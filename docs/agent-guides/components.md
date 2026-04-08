# Agent Guide: Component Rules

## Neovim / Lua

- 2 スペースインデント。
- 1 行 120 文字以内。
- `stylua.toml` に従う。
- 命名は `snake_case`。
- OS 分岐は専用ファイルへ分離する。
- OS 分岐ファイルは `config/nvim/lua/config/macos.lua` `windows.lua` `wsl.lua` を使う。

## WezTerm / Lua

- OS 判定は既存パターンに合わせる。

```lua
local is_mac = wezterm.target_triple:find("darwin")
local is_windows = wezterm.target_triple:find("windows")
```

## Fish

- 関数名は `snake_case`。
- 環境依存ロジックは既存ファイル責務を崩さずに閉じ込める。

## JSON

- ダブルクォートを使う。
- 終端改行を維持する。

## Commit / PR

- Conventional Commits を使う。`feat:` `fix:` `chore:` `refactor:` `docs:`
- 件名は 1 行で目的を示す。
- 破壊的変更は本文で明示する。
- PR には概要、主要ファイル、検証結果、OS 影響、懸念点を書く。
