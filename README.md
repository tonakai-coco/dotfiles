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
| ubuntu_nvim | `~/.config/ubuntu_nvim` | Linux |

## ディレクトリ構成

```
dotfiles/
├── Makefile          # シンボリックリンク管理
├── README.md
└── config/
    ├── nvim/         # Neovim 設定
    ├── wezterm/      # WezTerm 設定
    ├── fish/         # fish shell 設定
    ├── tmux/         # tmux 設定
    ├── aerospace/    # AeroSpace 設定 (macOS)
    ├── karabiner/    # Karabiner 設定 (macOS)
    ├── powershell/   # PowerShell 設定 (Windows)
    └── ubuntu_nvim/  # Ubuntu用 Neovim 設定
```
