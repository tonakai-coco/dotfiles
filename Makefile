# =============================================================================
# dotfiles Makefile
# =============================================================================
# Orchestrate dotfiles symlink management from a single entry point
# Idempotent: running multiple times always produces the same result
# =============================================================================

# -----------------------------------------------------------------------------
# Shell settings
# -----------------------------------------------------------------------------
# SHELL: Use bash explicitly (some features require more than POSIX sh)
SHELL := /bin/bash

# .SHELLFLAGS: -e exits on error, -u errors on undefined vars, -o pipefail catches pipe errors
.SHELLFLAGS := -eu -o pipefail -c

# .ONESHELL: Run all lines in a target within the same shell (enables variable sharing)
.ONESHELL:

# .DELETE_ON_ERROR: Remove target files if a recipe fails
.DELETE_ON_ERROR:

# -----------------------------------------------------------------------------
# OS detection
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
# Path definitions
# -----------------------------------------------------------------------------
DOTFILES_DIR := $(shell pwd)
CONFIG_DIR := $(DOTFILES_DIR)/config
XDG_CONFIG_HOME := $(HOME)/.config

# Windows: Neovim uses $LOCALAPPDATA/nvim (e.g. C:\Users\<user>\AppData\Local\nvim)
LOCALAPPDATA ?= $(HOME)/AppData/Local

# -----------------------------------------------------------------------------
# Link targets
# -----------------------------------------------------------------------------
# Directory-level symlinks (all OS)
COMMON_CONFIGS := wezterm

# Directory-level symlinks (macOS only)
MACOS_CONFIGS := nvim aerospace tmux

# Directory-level symlinks (Linux only)
LINUX_CONFIGS := nvim ubuntu_nvim tmux

# Directory-level symlinks (Windows only)
# Note: PowerShell profile path is special on Windows
WINDOWS_CONFIGS := powershell

# -----------------------------------------------------------------------------
# File-level link targets
# -----------------------------------------------------------------------------
# fish: Linked per-file to exclude env-dependent files (fish_variables, etc.)
# Note: Files in functions/, completions/, conf.d/ are also linked individually
FISH_FILES := config.fish abbr.fish
FISH_SUBDIRS := functions completions conf.d

# karabiner: Only custom rules are managed (karabiner.json is env-dependent)
KARABINER_FILES := numpad.json

# -----------------------------------------------------------------------------
# Option flags
# -----------------------------------------------------------------------------
# FORCE=1 to force-remove existing files/directories
FORCE ?= 0

# VERBOSE=1 for verbose output
VERBOSE ?= 0

ifeq ($(VERBOSE),1)
    Q :=
    ECHO := @echo -e
else
    Q := @
    ECHO := @echo -e
endif

# -----------------------------------------------------------------------------
# Color output (for supported terminals)
# -----------------------------------------------------------------------------
COLOR_RESET := \033[0m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED := \033[31m
COLOR_CYAN := \033[36m

# -----------------------------------------------------------------------------
# PHONY targets
# -----------------------------------------------------------------------------
.PHONY: all help link link-macos link-linux link-windows \
        unlink unlink-macos unlink-linux unlink-windows \
        check status clean \
        _ensure-xdg-config _create-link _remove-link \
        _link-fish-files _unlink-fish-files \
        _link-karabiner-files _unlink-karabiner-files

# -----------------------------------------------------------------------------
# Default target
# -----------------------------------------------------------------------------
all: link

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
help:
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)dotfiles Makefile$(COLOR_RESET)"
	$(ECHO) "================="
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Usage:$(COLOR_RESET)"
	$(ECHO) "  make link          - Create symlinks for the detected OS"
	$(ECHO) "  make link-macos    - Create symlinks for macOS"
	$(ECHO) "  make link-linux    - Create symlinks for Linux"
	$(ECHO) "  make link-windows  - Create symlinks for Windows"
	$(ECHO) ""
	$(ECHO) "  make unlink        - Remove symlinks for the detected OS"
	$(ECHO) "  make unlink-macos  - Remove symlinks for macOS"
	$(ECHO) "  make unlink-linux  - Remove symlinks for Linux"
	$(ECHO) "  make unlink-windows- Remove symlinks for Windows"
	$(ECHO) ""
	$(ECHO) "  make status        - Show current symlink status"
	$(ECHO) "  make check         - Show OS detection result"
	$(ECHO) "  make help          - Show this help"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Options:$(COLOR_RESET)"
	$(ECHO) "  FORCE=1            - Force overwrite existing files/directories"
	$(ECHO) "  VERBOSE=1          - Enable verbose output"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Examples:$(COLOR_RESET)"
	$(ECHO) "  make link                  # Auto-detect OS and create links"
	$(ECHO) "  make link FORCE=1          # Force overwrite existing files"
	$(ECHO) "  make link-macos VERBOSE=1  # macOS links with verbose output"
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Detected OS:$(COLOR_RESET) $(DETECTED_OS)"
	$(ECHO) ""

# -----------------------------------------------------------------------------
# OS detection check
# -----------------------------------------------------------------------------
check:
	$(ECHO) "$(COLOR_CYAN)OS Detection$(COLOR_RESET)"
	$(ECHO) "  uname -s:    $(UNAME_S)"
	$(ECHO) "  Detected OS: $(DETECTED_OS)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)Paths$(COLOR_RESET)"
	$(ECHO) "  DOTFILES_DIR:    $(DOTFILES_DIR)"
	$(ECHO) "  CONFIG_DIR:      $(CONFIG_DIR)"
	$(ECHO) "  XDG_CONFIG_HOME: $(XDG_CONFIG_HOME)"

# -----------------------------------------------------------------------------
# Symlink status
# -----------------------------------------------------------------------------
status:
	$(ECHO) "$(COLOR_CYAN)Symlink Status$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[Directory-level]$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS) $(LINUX_CONFIGS) $(WINDOWS_CONFIGS); do \
		target="$(XDG_CONFIG_HOME)/$$config"; \
		if [ -L "$$target" ]; then \
			link_dest=$$(readlink "$$target"); \
			echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target -> $$link_dest"; \
		elif [ -e "$$target" ]; then \
			echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target (regular file/directory)"; \
		else \
			echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target (not found)"; \
		fi; \
	done
	@# Windows: Neovim uses $LOCALAPPDATA/nvim
	$(Q)target="$(LOCALAPPDATA)/nvim"; \
	if [ -L "$$target" ]; then \
		link_dest=$$(readlink "$$target"); \
		echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target -> $$link_dest"; \
	elif [ -e "$$target" ]; then \
		echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target (regular file/directory)"; \
	else \
		echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target (not found)"; \
	fi
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[File-level: fish]$(COLOR_RESET)"
	$(Q)for file in $(FISH_FILES); do \
		target="$(XDG_CONFIG_HOME)/fish/$$file"; \
		if [ -L "$$target" ]; then \
			link_dest=$$(readlink "$$target"); \
			echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target -> $$link_dest"; \
		elif [ -e "$$target" ]; then \
			echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target (regular file)"; \
		else \
			echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target (not found)"; \
		fi; \
	done
	$(Q)for subdir in $(FISH_SUBDIRS); do \
		src_dir="$(CONFIG_DIR)/fish/$$subdir"; \
		if [ -d "$$src_dir" ]; then \
			for file in "$$src_dir"/*; do \
				[ -e "$$file" ] || continue; \
				filename=$$(basename "$$file"); \
				target="$(XDG_CONFIG_HOME)/fish/$$subdir/$$filename"; \
				if [ -L "$$target" ]; then \
					echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target"; \
				elif [ -e "$$target" ]; then \
					echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target"; \
				else \
					echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target"; \
				fi; \
			done; \
		fi; \
	done
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[File-level: karabiner]$(COLOR_RESET)"
	$(Q)for file in $(KARABINER_FILES); do \
		target="$(XDG_CONFIG_HOME)/karabiner/$$file"; \
		if [ -L "$$target" ]; then \
			link_dest=$$(readlink "$$target"); \
			echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $$target -> $$link_dest"; \
		elif [ -e "$$target" ]; then \
			echo -e "  $(COLOR_YELLOW)[FILE]$(COLOR_RESET) $$target (regular file)"; \
		else \
			echo -e "  $(COLOR_RED)[NONE]$(COLOR_RESET) $$target (not found)"; \
		fi; \
	done

# -----------------------------------------------------------------------------
# Main link target (auto-detect OS)
# -----------------------------------------------------------------------------
link:
ifeq ($(DETECTED_OS),macos)
	$(ECHO) "$(COLOR_GREEN)Detected macOS$(COLOR_RESET)"
	$(MAKE) link-macos FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else ifeq ($(DETECTED_OS),linux)
	$(ECHO) "$(COLOR_GREEN)Detected Linux$(COLOR_RESET)"
	$(MAKE) link-linux FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else ifeq ($(DETECTED_OS),windows)
	$(ECHO) "$(COLOR_GREEN)Detected Windows$(COLOR_RESET)"
	$(MAKE) link-windows FORCE=$(FORCE) VERBOSE=$(VERBOSE)
else
	$(ECHO) "$(COLOR_RED)Error: Unsupported OS ($(UNAME_S))$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "Supported:"
	$(ECHO) "  - macOS (Darwin)"
	$(ECHO) "  - Linux"
	$(ECHO) "  - Windows (via MINGW/MSYS/CYGWIN)"
	$(ECHO) ""
	$(ECHO) "If running from PowerShell/cmd.exe directly,"
	$(ECHO) "please use Git Bash, MSYS2, or WSL."
	exit 1
endif

# -----------------------------------------------------------------------------
# macOS link creation
# -----------------------------------------------------------------------------
link-macos: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)macOS: Creating symlinks$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[Directory-level]$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[File-level: fish]$(COLOR_RESET)"
	$(Q)$(MAKE) _link-fish-files FORCE=$(FORCE)
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[File-level: karabiner]$(COLOR_RESET)"
	$(Q)$(MAKE) _link-karabiner-files FORCE=$(FORCE)
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)macOS: Done$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Linux link creation
# -----------------------------------------------------------------------------
link-linux: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)Linux: Creating symlinks$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[Directory-level]$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(LINUX_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Linux: Done$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Windows link creation
# -----------------------------------------------------------------------------
# Windows (Git Bash/MSYS2/Cygwin) symlink creation
# Note: May require administrator privileges
link-windows: _ensure-xdg-config
	$(ECHO) "$(COLOR_CYAN)Windows: Creating symlinks$(COLOR_RESET)"
	$(ECHO) "$(COLOR_YELLOW)Note: Administrator privileges may be required$(COLOR_RESET)"
	$(ECHO) ""
	$(ECHO) "$(COLOR_CYAN)[Directory-level]$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(WINDOWS_CONFIGS); do \
		$(MAKE) _create-link \
			SRC="$(CONFIG_DIR)/$$config" \
			DEST="$(XDG_CONFIG_HOME)/$$config" \
			FORCE=$(FORCE); \
	done
	@# Neovim on Windows uses $LOCALAPPDATA/nvim
	$(Q)$(MAKE) _create-link \
		SRC="$(CONFIG_DIR)/nvim" \
		DEST="$(LOCALAPPDATA)/nvim" \
		FORCE=$(FORCE)
	$(ECHO) ""
	$(ECHO) "$(COLOR_GREEN)Windows: Done$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Unlink targets
# -----------------------------------------------------------------------------
unlink:
ifeq ($(DETECTED_OS),macos)
	$(MAKE) unlink-macos
else ifeq ($(DETECTED_OS),linux)
	$(MAKE) unlink-linux
else ifeq ($(DETECTED_OS),windows)
	$(MAKE) unlink-windows
else
	$(ECHO) "$(COLOR_RED)Error: Unsupported OS$(COLOR_RESET)"
	exit 1
endif

unlink-macos:
	$(ECHO) "$(COLOR_CYAN)macOS: Removing symlinks$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(MACOS_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(Q)$(MAKE) _unlink-fish-files
	$(Q)$(MAKE) _unlink-karabiner-files
	$(ECHO) "$(COLOR_GREEN)macOS: Unlink complete$(COLOR_RESET)"

unlink-linux:
	$(ECHO) "$(COLOR_CYAN)Linux: Removing symlinks$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(LINUX_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(ECHO) "$(COLOR_GREEN)Linux: Unlink complete$(COLOR_RESET)"

unlink-windows:
	$(ECHO) "$(COLOR_CYAN)Windows: Removing symlinks$(COLOR_RESET)"
	$(Q)for config in $(COMMON_CONFIGS) $(WINDOWS_CONFIGS); do \
		$(MAKE) _remove-link DEST="$(XDG_CONFIG_HOME)/$$config"; \
	done
	$(Q)$(MAKE) _remove-link DEST="$(LOCALAPPDATA)/nvim"
	$(ECHO) "$(COLOR_GREEN)Windows: Unlink complete$(COLOR_RESET)"

# -----------------------------------------------------------------------------
# Internal: Ensure XDG_CONFIG_HOME directory exists
# -----------------------------------------------------------------------------
_ensure-xdg-config:
	$(Q)if [ ! -d "$(XDG_CONFIG_HOME)" ]; then \
		echo -e "$(COLOR_YELLOW)Creating $(XDG_CONFIG_HOME)$(COLOR_RESET)"; \
		mkdir -p "$(XDG_CONFIG_HOME)"; \
	fi

# -----------------------------------------------------------------------------
# Internal: Create a symlink
# -----------------------------------------------------------------------------
# Args: SRC=source path  DEST=link path  FORCE=force flag
_create-link:
	@# Check source exists
	$(Q)if [ ! -e "$(SRC)" ]; then \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(SRC) (source not found)"; \
		exit 0; \
	fi
	@# Check destination state and handle accordingly
	$(Q)if [ -L "$(DEST)" ]; then \
		echo -e "  $(COLOR_YELLOW)[DEL]$(COLOR_RESET)  Removing existing link: $(DEST)"; \
		rm "$(DEST)"; \
	elif [ -e "$(DEST)" ]; then \
		if [ "$(FORCE)" = "1" ]; then \
			echo -e "  $(COLOR_RED)[FORCE]$(COLOR_RESET) Force removing: $(DEST)"; \
			rm -rf "$(DEST)"; \
		else \
			echo -e "  $(COLOR_RED)[ERROR]$(COLOR_RESET) $(DEST) is a regular file/directory"; \
			echo -e "         Use FORCE=1 to overwrite"; \
			exit 1; \
		fi; \
	fi
	@# Create symlink
	$(Q)ln -s "$(SRC)" "$(DEST)"
	$(Q)echo -e "  $(COLOR_GREEN)[LINK]$(COLOR_RESET) $(DEST) -> $(SRC)"

# -----------------------------------------------------------------------------
# Internal: Remove a symlink
# -----------------------------------------------------------------------------
# Args: DEST=link path
_remove-link:
	$(Q)if [ -L "$(DEST)" ]; then \
		rm "$(DEST)"; \
		echo -e "  $(COLOR_GREEN)[DEL]$(COLOR_RESET)  $(DEST)"; \
	elif [ -e "$(DEST)" ]; then \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(DEST) (not a symlink)"; \
	else \
		echo -e "  $(COLOR_YELLOW)[SKIP]$(COLOR_RESET) $(DEST) (not found)"; \
	fi

# -----------------------------------------------------------------------------
# Internal: Create fish file-level symlinks
# -----------------------------------------------------------------------------
# fish is linked per-file to exclude env-dependent files (fish_variables, etc.)
_link-fish-files:
	@# Create ~/.config/fish if missing
	$(Q)mkdir -p "$(XDG_CONFIG_HOME)/fish"
	@# Link root-level files
	$(Q)for file in $(FISH_FILES); do \
		src="$(CONFIG_DIR)/fish/$$file"; \
		dest="$(XDG_CONFIG_HOME)/fish/$$file"; \
		if [ -e "$$src" ]; then \
			$(MAKE) _create-link SRC="$$src" DEST="$$dest" FORCE=$(FORCE); \
		fi; \
	done
	@# Link files in subdirectories
	$(Q)for subdir in $(FISH_SUBDIRS); do \
		src_dir="$(CONFIG_DIR)/fish/$$subdir"; \
		dest_dir="$(XDG_CONFIG_HOME)/fish/$$subdir"; \
		if [ -d "$$src_dir" ]; then \
			mkdir -p "$$dest_dir"; \
			for file in "$$src_dir"/*; do \
				[ -e "$$file" ] || continue; \
				filename=$$(basename "$$file"); \
				$(MAKE) _create-link SRC="$$file" DEST="$$dest_dir/$$filename" FORCE=$(FORCE); \
			done; \
		fi; \
	done

# -----------------------------------------------------------------------------
# Internal: Remove fish file-level symlinks
# -----------------------------------------------------------------------------
_unlink-fish-files:
	@# Remove root-level files
	$(Q)for file in $(FISH_FILES); do \
		dest="$(XDG_CONFIG_HOME)/fish/$$file"; \
		$(MAKE) _remove-link DEST="$$dest"; \
	done
	@# Remove files in subdirectories
	$(Q)for subdir in $(FISH_SUBDIRS); do \
		src_dir="$(CONFIG_DIR)/fish/$$subdir"; \
		dest_dir="$(XDG_CONFIG_HOME)/fish/$$subdir"; \
		if [ -d "$$src_dir" ]; then \
			for file in "$$src_dir"/*; do \
				[ -e "$$file" ] || continue; \
				filename=$$(basename "$$file"); \
				$(MAKE) _remove-link DEST="$$dest_dir/$$filename"; \
			done; \
		fi; \
	done

# -----------------------------------------------------------------------------
# Internal: Create karabiner file-level symlinks
# -----------------------------------------------------------------------------
# karabiner.json is env-dependent, so only custom rules are linked
_link-karabiner-files:
	@# Create ~/.config/karabiner if missing
	$(Q)mkdir -p "$(XDG_CONFIG_HOME)/karabiner"
	$(Q)for file in $(KARABINER_FILES); do \
		src="$(CONFIG_DIR)/karabiner/$$file"; \
		dest="$(XDG_CONFIG_HOME)/karabiner/$$file"; \
		if [ -e "$$src" ]; then \
			$(MAKE) _create-link SRC="$$src" DEST="$$dest" FORCE=$(FORCE); \
		fi; \
	done

# -----------------------------------------------------------------------------
# Internal: Remove karabiner file-level symlinks
# -----------------------------------------------------------------------------
_unlink-karabiner-files:
	$(Q)for file in $(KARABINER_FILES); do \
		dest="$(XDG_CONFIG_HOME)/karabiner/$$file"; \
		$(MAKE) _remove-link DEST="$$dest"; \
	done

# -----------------------------------------------------------------------------
# Cleanup (alias for unlink)
# -----------------------------------------------------------------------------
clean: unlink
