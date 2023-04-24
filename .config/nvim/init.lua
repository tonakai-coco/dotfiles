if vim.g.vscode then
  print("vscode")
else
  print("not vscode")
end

require("craftzdog.base")
require("craftzdog.highlights")
require("craftzdog.maps")
require("craftzdog.plugins")

local has = vim.fn.has
local is_mac = has("mac")
local is_win = has("win32") or has("win64")
local is_wsl = has("wsl")

if is_mac == 1 then
  print("is_mac", is_mac)
  require("craftzdog.macos")
end
if is_win == 1 then
  print("is_win", is_win)
  require("craftzdog.windows")
end
if is_wsl == 1 then
  print("is_wsl", is_wsl)
  require("craftzdog.wsl")
end
