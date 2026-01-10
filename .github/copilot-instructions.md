# Dotfiles Repository Guidelines

## Structure and Module Organization

This dotfiles repository shares `~/.config` configurations across macOS, Linux, and Windows. Keep OS-specific logic confined to dedicated files/directories.

- **fish/** - Shell abbreviations ([abbr.fish](../config/fish/abbr.fish)) and functions ([functions/](../config/fish/functions/))
  - `clip.fish`, `yazi.fish` contain macOS-specific features
- **nvim/** - LazyVim-based. Core config in [lua/config/](../config/nvim/lua/config/), plugins in [lua/plugins/](../config/nvim/lua/plugins/)
  - [lazy.lua](../config/nvim/lua/config/lazy.lua) imports LazyVim extras
- **wezterm/** - OS detection with branching ([wezterm.lua](../config/wezterm/wezterm.lua))
  - Common binds in [keybinds_common.lua](../config/wezterm/keybinds_common.lua), OS-specific in `keybinds_mac.lua`/`keybinds_win.lua`
- **karabiner/** - macOS keymaps ([numpad.json](../config/karabiner/numpad.json))
- **powershell/** - Windows-only ([user_profile.ps1](../config/powershell/user_profile.ps1))
- **tmux/** - [tmux.conf](../config/tmux/tmux.conf)
- **ubuntu_nvim/** - Lightweight Vim alternative ([init.vim](../config/ubuntu_nvim/init.vim))

## Development Commands

### Neovim
```bash
# Sync plugins
nvim --headless "+Lazy sync" +qa

# Format Lua files
stylua --config nvim/stylua.toml nvim/lua/**/*.lua

# Health check
nvim --headless "+checkhealth" +qa
```

### Fish
```bash
# Format functions
fish_indent --write fish/functions/*.fish

# Check formatting
fish -c "for f in fish/functions/*.fish; fish_indent --check $f; end"
```

### WezTerm
```bash
# Smoke test
wezterm --config-file wezterm/wezterm.lua start --always-new-process

# Test module loading in REPL
wezterm -n --config-file wezterm/wezterm.lua
# > local m = require "keybinds_mac"
```

### Other
```bash
# Validate Karabiner JSON
jq empty karabiner/numpad.json

# Reload tmux config
tmux source-file ~/.config/tmux/tmux.conf
```

## Coding Patterns

### Lua (Neovim)
- **Indentation**: 2 spaces, auto-formatted with stylua
- **Module naming**: lowercase + underscore (`editor.lua`, `keybinds_mac.lua`)
- **Plugin definitions**: Split into [lua/plugins/](../config/nvim/lua/config/lazy.lua), LazyVim extras imported in `lazy.lua`
  ```lua
  { import = "lazyvim.plugins.extras.ai.copilot" },
  { import = "plugins" }, -- Custom plugins
  ```

### Fish
- **Function naming**: `snake_case`
- **Abbreviations**: Consolidated in [abbr.fish](../config/fish/abbr.fish) (`gs`, `ga`, `ll`, etc.)
- **Loading**: Declarative from `conf.d`, or `source` in [config.fish](../config/fish/config.fish)

### WezTerm (Lua)
- **OS branching**: Detect via `wezterm.target_triple` (`apple`, `windows`, `linux`)
- **Keybind merging**: Load common keys first, append OS-specific with `ipairs`
  ```lua
  for _, key in ipairs(os_binds.keys or {}) do
    table.insert(keybinds.keys, key)
  end
  ```

### JSON
- **Trailing newline**: Required
- **Key order**: Alphabetical preferred
- **Quotes**: Double only

## Cross-Platform Support

- **No absolute paths**: Use environment variables (`$XDG_CONFIG_HOME`, `~`)
- **OS-specific logic**: Localize to existing files/directories
  - Neovim: [lua/config/macos.lua](../config/nvim/lua/config/macos.lua), [windows.lua](../config/nvim/lua/config/windows.lua), [wsl.lua](../config/nvim/lua/config/wsl.lua)
  - WezTerm: `keybinds_mac.lua`, `keybinds_win.lua`

## Commit Conventions

- **Format**: Conventional Commits (`feat:`, `fix:`, `chore:`)
- **Granularity**: 1 logical change = 1 commit
- **Visual changes**: Include screenshots
- **Manual steps**: Document in PR if needed (e.g., re-run `nvim --headless "+Lazy sync"`)

## Security

- **Secrets**: Never commit host-specific tokens or SSH information
- **Overrides**: Keep host-specific configs outside version control
