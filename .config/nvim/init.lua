-- bootstrap lazy.nvim, LazyVim and your plugins
if vim.loader then
  vim.loader.enable()
end

if not vim.g.vscode then
  require("config.lazy")
else
  require("config.vscode_keymap")
end

local has = vim.fn.has
local is_mac = has("mac")
local is_win = has("win32") or has("win64")
local is_wsl = has("wsl")

if is_mac == 1 then
  require("config.macos")
end
if is_win == 1 then
  require("config.windows")
end
if is_wsl == 1 then
  require("config.wsl")
end
