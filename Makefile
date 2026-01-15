# =============================================================================
# dotfiles Makefile
# =============================================================================
# 単一の入口でOSごとの設定ファイルシンボリックリンクを管理する
# 冪等性を重視：何度実行しても同じ結果になる
# =============================================================================

# -----------------------------------------------------------------------------
# シェル設定
# -----------------------------------------------------------------------------
# SHELL: 明示的に bash を指定（POSIX sh では一部機能が使えない）
SHELL := /bin/bash

# .SHELLFLAGS: -e でエラー時即終了、-u で未定義変数エラー、-o pipefail でパイプエラー検知
.SHELLFLAGS := -eu -o pipefail -c

# .ONESHELL: 1つのターゲット内の複数行を同一シェルで実行（変数共有可能）
.ONESHELL:

# .DELETE_ON_ERROR: ターゲット実行中にエラーが発生したら生成物を削除
.DELETE_ON_ERROR:

# -----------------------------------------------------------------------------
# OS判定
# -----------------------------------------------------------------------------
UNAME_S := $(shell uname -s 2>/dev/null || echo "Unknown")

ifeq ($(UNAME_S),Darwin)
    DETECTED_OS := macos
else ifeq ($(UNAME_S),Linux)
    DETECTED_OS := linux
else ifneq (,$(findstring MINGW,$(UNAME_S)))
    DETECTED_OS := windows
else ifneq (,$(findstring MSYS,$(UNAME_S)))
    DETECTED_OS := windows
else ifneq (,$(findstring CYGWIN,$(UNAME_S)))
    DETECTED_OS := windows
else
    DETECTED_OS := unknown
endif

# -----------------------------------------------------------------------------
# パス定義
# -----------------------------------------------------------------------------
DOTFILES_DIR := $(shell pwd)
CONFIG_DIR := $(DOTFILES_DIR)/config
XDG_CONFIG_HOME := $(HOME)/.config

# -----------------------------------------------------------------------------
# リンク対象定義
# -----------------------------------------------------------------------------
# 共通設定（全OS）
COMMON_CONFIGS := nvim wezterm fish tmux

# macOS固有設定
MACOS_CONFIGS := aerospace karabiner

# Linux固有設定
LINUX_CONFIGS := ubuntu_nvim

# Windows固有設定（PowerShell）
# 注: Windowsの場合、PowerShellプロファイルパスは特殊
WINDOWS_CONFIGS := powershell

# -----------------------------------------------------------------------------
# オプションフラグ
# -----------------------------------------------------------------------------
# FORCE=1 で既存ファイル/ディレクトリを強制削除
FORCE ?= 0

# VERBOSE=1 で詳細出力
VERBOSE ?= 0

ifeq ($(VERBOSE),1)
    Q :=
    ECHO := @echo
else
    Q := @
    ECHO := @echo
endif

# -----------------------------------------------------------------------------
# カラー出力（対応ターミナル用）
# -----------------------------------------------------------------------------
COLOR_RESET := \033[0m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED := \033[31m
COLOR_CYAN := \033[36m

# -----------------------------------------------------------------------------
# PHONYターゲット宣言
# -----------------------------------------------------------------------------
.PHONY: all help link link-macos link-linux link-windows \
        unlink unlink-macos unlink-linux unlink-windows \
        check status clean

# -----------------------------------------------------------------------------
# デフォルトターゲット
# -----------------------------------------------------------------------------
all: link

# -----------------------------------------------------------------------------
# ヘルプ
# -----------------------------------------------------------------------------
help:
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)dotfiles Makefile$(COLOR_RESET)"
	$(ECHO) "================="
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)使用方法:$(COLOR_RESET)"
	$(ECHO) "  make link          - 現在のOSに合わせてシンボリックリンクを作成"
	$(ECHO) "  make link-macos    - macOS用リンクを作成"
	$(ECHO) "  make link-linux    - Linux用リンクを作成"
	$(ECHO) "  make link-windows  - Windows用リンクを作成"
	$(ECHO) ""
	$(ECHO) "  make unlink        - 現在のOSのシンボリックリンクを削除"
	$(ECHO) "  make unlink-macos  - macOS用リンクを削除"
	$(ECHO) "  make unlink-linux  - Linux用リンクを削除"
	$(ECHO) "  make unlink-windows- Windows用リンクを削除"
	$(ECHO) ""
	$(ECHO) "  make status        - 現在のリンク状態を表示"
	$(ECHO) "  make check         - OS検出結果を表示"
	$(ECHO) "  make help          - このヘルプを表示"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)オプション:$(COLOR_RESET)"
	$(ECHO) "  FORCE=1            - 既存ファイル/ディレクトリを強制上書き"
	$(ECHO) "  VERBOSE=1          - 詳細出力を有効化"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)例:$(COLOR_RESET)"
	$(ECHO) "  make link                  # 自動OS検出でリンク作成"
	$(ECHO) "  make link FORCE=1          # 既存ファイルを強制上書き"
	$(ECHO) "  make link-macos VERBOSE=1  # macOS用、詳細出力"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)検出されたOS:$(COLOR_RESET) $(DETECTED_OS)"
	$(ECHO) ""

# -----------------------------------------------------------------------------
# OS検出確認
# -----------------------------------------------------------------------------
check:
	$(ECHO) "$(COLOR_CYAN)OS検出結果$(COLOR_RESET)"
	$(ECHO) "  uname -s: $(UNAME_S)"
	$(ECHO) "  検出OS:   $(DETECTED_OS)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)パス設定$(COLOR_RESET)"
	$(ECHO) "  DOTFILES_DIR:    $(DOTFILES_DIR)"
	$(ECHO) "  CONFIG_DIR:      $(CONFIG_DIR)"
	$(ECHO) "  XDG_CONFIG_HOME: $(XDG_CONFIG_HOME)"

# -----------------------------------------------------------------------------
# リンク状態確認
# -----------------------------------------------------------------------------
status:
	$(ECHO) "$(COLOR_CYAN)シンボリックリンク状態$(COLOR_RESET)"
	$(ECHO) ""
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS) $(LINUX_CONFIGS); do \
		target="$(XDG_CONFIG_HOME)/$$config"; \
		if [ -L "$$target" ]; then \
			link_dest=$$(readlink "$$target"); \
			echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target -> $$link_dest"; \
		elif [ -e "$$target" ]; then \
			echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target (通常ファイル/ディレクトリ)"; \
		else \
			echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target (存在しない)"; \
		fi; \
	done

# -----------------------------------------------------------------------------
# メインリンクターゲット（OS自動判定）
# -----------------------------------------------------------------------------
link:
ifeq ($(DETECTED_OS),macos)
	$(ECHO) "$(COLOR_GREEN)macOSを検出しました$(COLOR_RESET)"
	$(MAKE) link-macos FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else ifeq ($(DETECTED_OS),linux)
	$(ECHO) "$(COLOR_GREEN)Linuxを検出しました$(COLOR_RESET)"
	$(MAKE) link-linux FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else ifeq ($(DETECTED_OS),windows)
	$(ECHO) "$(COLOR_GREEN)Windowsを検出しました$(COLOR_RESET)"
	$(MAKE) link-windows FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else
	$(ECHO) "$(COLOR_RED)エラー: 未対応のOS ($(UNAME_S))$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "対応OS:"
	$(ECHO) "  - macOS (Darwin)"
	$(ECHO) "  - Linux"
	$(ECHO) "  - Windows (MINGW/MSYS/CYGWIN経由)"
	$(ECHO) ""
	$(ECHO) "Windows (PowerShell/cmd.exe) から直接実行する場合は、"
	$(ECHO) "Git Bash、MSYS2、またはWSLをご利用ください。"
	exit 1
endif

# -----------------------------------------------------------------------------
# macOS用リンク作成
# -----------------------------------------------------------------------------
link-macos: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)macOS: シンボリックリンクを作成します$(COLOR_RESET)"
	$(ECHO) ""
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)macOS: 完了$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Linux用リンク作成
# -----------------------------------------------------------------------------
link-linux: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)Linux: シンボリックリンクを作成します$(COLOR_RESET)"
	$(ECHO) ""
	$(Q)for config in $(COMMON_CONFIGS) $(LINUX_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Linux: 完了$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Windows用リンク作成
# -----------------------------------------------------------------------------
# Windows (Git Bash/MSYS2/Cygwin) でのシンボリックリンク作成
# 注: 管理者権限が必要な場合があります
link-windows: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)Windows: シンボリックリンクを作成します$(COLOR_RESET)"
	$(ECHO) "$(COLOR_YELLOW)注: 管理者権限が必要な場合があります$(COLOR_RESET)"
	$(ECHO) ""
	$(Q)for config in $(COMMON_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	@# PowerShell プロファイル用の特殊処理
	$(ECHO) ""
	$(ECHO) "$(COLOR_YELLOW)PowerShellプロファイルは手動設定が必要な場合があります:$(COLOR_RESET)"
	$(ECHO) "  ソース: $(CONFIG_DIR)/powershell"
	$(ECHO) "  推奨先: \$$HOME\\Documents\\PowerShell"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Windows: 完了$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# リンク削除ターゲット
# -----------------------------------------------------------------------------
unlink:
ifeq ($(DETECTED_OS),macos)
	$(MAKE) unlink-macos
else ifeq ($(DETECTED_OS),linux)
	$(MAKE) unlink-linux
else ifeq ($(DETECTED_OS),windows)
	$(MAKE) unlink-windows
else
	$(ECHO) "$(COLOR_RED)エラー: 未対応のOS$(COLOR_RESET)"
	exit 1
endif

unlink-macos:
	$(ECHO) "$(COLOR_CYAN)macOS: シンボリックリンクを削除します$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(ECHO) "$(COLOR_GREEN)macOS: リンク削除完了$(COLOR_RESET)"

unlink-linux:
	$(ECHO) "$(COLOR_CYAN)Linux: シンボリックリンクを削除します$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(LINUX_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(ECHO) "$(COLOR_GREEN)Linux: リンク削除完了$(COLOR_RESET)"

unlink-windows:
	$(ECHO) "$(COLOR_CYAN)Windows: シンボリックリンクを削除します$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(ECHO) "$(COLOR_GREEN)Windows: リンク削除完了$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# 内部ターゲット: XDG_CONFIG_HOME ディレクトリ作成
# -----------------------------------------------------------------------------
_ensure-xdg-config:
	$(Q)if [ ! -d "$(XDG_CONFIG_HOME)" ]; then \
		echo -e "$(COLOR_YELLOW)$(XDG_CONFIG_HOME) を作成します$(COLOR_RESET)"; \
		mkdir -p "$(XDG_CONFIG_HOME)"; \
	fi

# -----------------------------------------------------------------------------
# 内部ターゲット: シンボリックリンク作成
# -----------------------------------------------------------------------------
# 引数: SRC=ソースパス DEST=リンク先パス FORCE=強制フラグ
_create-link:
	@# ソースの存在確認
	$(Q)if [ ! -e "$(SRC)" ]; then \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(SRC) (ソースが存在しません)"; \
		exit 0; \
	fi
	@# リンク先の状態確認と処理
	$(Q)if [ -L "$(DEST)" ]; then \
		echo -e "  $(COLOR_YELLOW)[DEL]$(COLOR_RESET)  既存リンクを削除: $(DEST)"; \
		rm "$(DEST)"; \
	elif [ -e "$(DEST)" ]; then \
		if [ "$(FORCE)" = "1" ]; then \
			echo -e "  $(COLOR_RED)[FORCE]$(COLOR_RESET) 既存を強制削除: $(DEST)"; \
			rm -rf "$(DEST)"; \
		else \
			echo -e "  $(COLOR_RED)[ERROR]$(COLOR_RESET) $(DEST) は通常ファイル/ディレクトリです"; \
			echo -e "         強制削除するには FORCE=1 を指定してください"; \
			exit 1; \
		fi; \
	fi
	@# シンボリックリンク作成
	$(Q)ln -s "$(SRC)" "$(DEST)"
	$(Q)echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $(DEST) -> $(SRC)"

# -----------------------------------------------------------------------------
# 内部ターゲット: シンボリックリンク削除
# -----------------------------------------------------------------------------
# 引数: DEST=リンクパス
_remove-link:
	$(Q)if [ -L "$(DEST)" ]; then \
		rm "$(DEST)"; \
		echo -e "  $(COLOR_GREEN)[DEL]$(COLOR_RESET)  $(DEST)"; \
	elif [ -e "$(DEST)" ]; then \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(DEST) (シンボリックリンクではありません)"; \
	else \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(DEST) (存在しません)"; \
	fi

# -----------------------------------------------------------------------------
# クリーンアップ（全リンク削除の別名）
# -----------------------------------------------------------------------------
clean: unlink
