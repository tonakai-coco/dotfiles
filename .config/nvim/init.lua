require("craftzdog.base")
require("craftzdog.highlights")
require("craftzdog.maps")
require("craftzdog.plugins")

local has = vim.fn.has
local is_mac = has("mac")
local is_win = has("win32") or has("win64")
local is_wsl = has("wsl")

if is_mac == 1 then
  require("craftzdog.macos")
end
if is_win == 1 then
  require("craftzdog.windows")
end
if is_wsl == 1 then
  require("craftzdog.wsl")
end
