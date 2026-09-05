# dotfiles

個人用の設定ファイル管理リポジトリです。

## 前提条件

### macOS

```bash
# Xcode Command Line Tools をインストール（make が含まれる）
xcode-select --install
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install make
```

### Windows

以下のいずれかの方法で `make` を使えるようにしてください。

**方法1: Scoop（推奨）**
```powershell
scoop install make
```

**方法2: Chocolatey**
```powershell
choco install make
```

**方法3: Git Bash / WSL を使う**
Git Bash または WSL 内で実行すれば `make` が使えます。

## 使い方

### シンボリックリンクの作成

```bash
# OS を自動判定してリンク作成
make link

# 既存ファイルがある場合は強制上書き
make link FORCE=1
```

### その他のコマンド

```bash
make help      # ヘルプ表示
make status    # 現在のリンク状態を確認
make check     # OS検出結果を確認
make unlink    # リンクを削除
```

## 管理対象

| 設定 | パス | 対象OS |
|------|------|--------|
| Neovim | `~/.config/nvim` (Windows: `$LOCALAPPDATA/nvim`) | macOS / Linux / Windows |
| WezTerm | `~/.config/wezterm` | 全OS |
| fish | `~/.config/fish` | macOS |
| tmux | `~/.config/tmux` | macOS / Linux |
| AeroSpace | `~/.config/aerospace` | macOS |
| Karabiner | `~/.config/karabiner` | macOS |
| PowerShell | `~/.config/powershell` | Windows |
| AutoHotkey | `~/.config/autohotkey` | Windows |
| ubuntu_nvim | `~/.config/ubuntu_nvim` | Linux |

## AIツール設定の管理

**AIツール（Claude、Codex、Copilot）の設定は、これまでの自動シンボリックリンク管理から除外され、各端末で手動管理するよう変更しました。**

- `ai/` ディレクトリに各ツールのサンプル設定ファイルが残っています。
- 必要な設定は `ai/` 配下から自分のホームディレクトリ（例: `~/.codex/`, `~/.claude/`, `~/.copilot/`）へ手動でコピーしてください。
- 既に作成されているシンボリックリンクは自動で通常ファイルに変換されません。既存リンクを削除し、手動でコピーしたファイルに置き換える必要があります。
- 既存の AI 設定リンクを通常ファイルへ移行する手順:
  1. `make unlink` で現在のシンボリックリンクを削除（AI 設定は対象外ですが、スキル関連の古いリンクは自動でクリーンアップされます）。
  2. `cp -r ai/claude/* ~/.claude/` など、対象ツールのディレクトリへコピー。
  3. 必要に応じて設定ファイルを編集し、動作を確認してください。

## ディレクトリ構成

```
dotfiles/
├── Makefile          # シンボリックリンク管理
├── README.md
├── config/
│   ├── nvim/         # Neovim 設定
│   ├── wezterm/      # WezTerm 設定
│   ├── fish/         # fish shell 設定
│   ├── tmux/         # tmux 設定
│   ├── aerospace/    # AeroSpace 設定 (macOS)
│   ├── karabiner/    # Karabiner 設定 (macOS)
│   ├── powershell/   # PowerShell 設定 (Windows)
│   ├── autohotkey/   # AutoHotkey 設定 (Windows)
│   └── ubuntu_nvim/  # Ubuntu用 Neovim 設定
├── ai/
│   ├── claude/
│   │   ├── settings.json
│   │   └── statusline-command.sh
│   ├── codex/
│   │   └── hooks.json
│   └── copilot/
│       ├── agents/
│       └── hooks/notify.json
└── ...
```
