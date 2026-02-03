# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

macOS/Linux/Windows対応のdotfiles管理リポジトリ。Makefileによるシンボリックリンク管理でidempotentな設計。

## Build & Development Commands

### Makefile Commands
```bash
make link              # OS自動判定でリンク作成
make link FORCE=1      # 既存ファイルを強制上書き
make status            # リンク状態確認
make unlink            # リンク削除
make check             # OS検出結果確認
```

### Neovim
```bash
nvim --headless "+Lazy sync" +qa                      # プラグイン同期
stylua --config config/nvim/stylua.toml config/nvim/lua/**/*.lua  # Luaフォーマット
nvim --headless "+checkhealth" +qa                    # ヘルスチェック
```

### Fish Shell
```bash
fish_indent --write config/fish/functions/*.fish
```

### Karabiner（JSON検証）
```bash
jq empty config/karabiner/numpad.json
```

### WezTerm（テスト起動）
```bash
wezterm --config-file config/wezterm/wezterm.lua start --always-new-process
```

### Tmux（設定リロード）
```bash
tmux source-file ~/.config/tmux/tmux.conf
```

## Architecture

### Directory Structure
```
config/
├── nvim/           # LazyVimベースのNeovim設定
├── wezterm/        # WezTermターミナル設定
├── fish/           # Fish shell設定（macOSのみ）
├── tmux/           # Tmux設定（macOS/Linuxのみ）
├── aerospace/      # macOSウィンドウマネージャー
├── karabiner/      # macOSキーマップ
├── powershell/     # Windows PowerShellプロファイル
└── ubuntu_nvim/    # Ubuntu用Vim設定（レガシー）
```

### OS-Specific Configurations

**Makefile内の管理対象**:
- 全OS共通: wezterm
- macOS: nvim, aerospace, tmux, fish (ファイルレベル), karabiner (ファイルレベル)
- Linux: nvim, ubuntu_nvim, tmux
- Windows: powershell, nvim（$LOCALAPPDATA/nvim）

**Neovim内のOS分岐**:
- `lua/config/macos.lua` - macOS固有設定
- `lua/config/windows.lua` - Windows固有設定
- `lua/config/wsl.lua` - WSL固有設定

### Key Design Patterns

1. **OS固有コードの分離**: 専用ファイルに集約（例: WezTermの`keybinds_mac.lua`/`keybinds_win.lua`）
2. **ファイルレベルリンク**: fish/karabinerは環境依存ファイルを除外して個別リンク
3. **Idempotent設計**: makeコマンドは複数回実行しても同じ結果

## Coding Conventions

### Lua (Neovim/WezTerm)
- 2スペースインデント、120文字幅（stylua.toml準拠）
- 命名規則: 小文字+アンダースコア（例: `my_function`）
- 条件分岐パターン:
```lua
local is_mac = wezterm.target_triple:find("darwin")
local is_windows = wezterm.target_triple:find("windows")
```

### Git Commits
Conventional Commits形式: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`

### Security
- 環境変数やシークレットは`.gitignore`対象ファイルに記載
- ハードコードされた認証情報を含めない
