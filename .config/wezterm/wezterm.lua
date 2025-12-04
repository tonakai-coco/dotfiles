-- Pull in the wezterm API
local wezterm = require("wezterm")

local config = wezterm.config_builder()

----------------------------------------------------
-- OS別設定
----------------------------------------------------
local triple = wezterm.target_triple
if string.find(triple, "windows") then
	-- Windows
	config.default_prog = { "pwsh.exe", "-NoLogo" }
	config.font_size = 9.5
	config.font = require("wezterm").font_with_fallback({
		{
			family = "Hack Nerd Font",
			weight = "Bold",
			stretch = "Normal",
			style = "Normal",
		},
	})
	config.window_background_opacity = 0.70
	config.win32_system_backdrop = "Acrylic"
elseif string.find(triple, "apple") then
	-- macOS (Apple Silicon / Intel)
	-- config.default_prog = { "zsh" }
	config.font_size = 12.5
	wezterm.font("Hack", { weight = "Regular", stretch = "Normal", style = "Normal" })
	config.window_background_opacity = 0.75
	config.macos_window_background_blur = 30
elseif string.find(triple, "linux") then
	-- Linux
	config.enable_wayland = false
	config.default_prog = { "bash" }
end

----------------------------------------------------
-- config
----------------------------------------------------
config.automatically_reload_config = true
config.window_close_confirmation = "NeverPrompt"
config.enable_scroll_bar = true
config.use_ime = true
config.window_decorations = "RESIZE"
config.hide_tab_bar_if_only_one_tab = false
-- config.color_scheme = "iceberg-dark"
-- config.color_scheme = "iceberg-light"
-- config.color_scheme = "Builtin Solarized Dark"

-- kanagawaカラースキームを適用
local kanagawa = require("kanagawa")
for key, value in pairs(kanagawa) do
	config[key] = value
end

config.window_frame = {
	inactive_titlebar_bg = "none",
	active_titlebar_bg = "none",
}

config.window_background_gradient = {
	colors = { "#000000" },
}

config.show_new_tab_button_in_tab_bar = false
-- config.show_close_tab_button_in_tab_bar = false  -- ナイトリービルドのみのオプション
config.colors = {
	tab_bar = {
		inactive_tab_edge = "none",
	},
	compose_cursor = "orange",
}

----------------------------------------------------
-- keybinds
----------------------------------------------------
config.disable_default_key_bindings = true

-- キーバインド設定
-- 1. 共通のキーバインドを読み込む
local common_binds = require("keybinds_common")
local keybinds = {
	keys = common_binds.keys or {},
	key_tables = common_binds.key_tables or {},
}

-- 2. OS固有のキーバインドを読み込んでマージする
local os_binds_file = nil
if string.find(triple, "apple") then
	os_binds_file = "keybinds_mac"
elseif string.find(triple, "windows") then
	os_binds_file = "keybinds_win"
end

-- pcall を使って安全に require する
if os_binds_file then
	local ok, os_binds = pcall(require, os_binds_file)
	if ok and os_binds then
		-- `keys` テーブル (配列) を連結する
		for _, key in ipairs(os_binds.keys or {}) do
			table.insert(keybinds.keys, key)
		end
		-- `key_tables` テーブル (マップ) をマージする
		if os_binds.key_tables then
			for name, keys in pairs(os_binds.key_tables) do
				keybinds.key_tables[name] = keys
			end
		end
	end
end

config.keys = keybinds.keys
config.key_tables = keybinds.key_tables
config.leader = { key = "t", mods = "CTRL", timeout_milliseconds = 2000 }

----------------------------------------------------
-- event handlers
----------------------------------------------------
local SOLID_LEFT_ARROW = wezterm.nerdfonts.ple_lower_right_triangle
local SOLID_RIGHT_ARROW = wezterm.nerdfonts.ple_upper_left_triangle

wezterm.on("format-tab-title", function(tab, tabs, panes, config, hover, max_width)
	local background = "#5c6d74"
	local foreground = "#FFFFFF"
	local edge_background = "none"
	if tab.is_active then
		background = "#ae8b2d"
		foreground = "#FFFFFF"
	end
	local edge_foreground = background
	local title = "   " .. wezterm.truncate_right(tab.active_pane.title, max_width - 1) .. "   "
	return {
		{ Background = { Color = edge_background } },
		{ Foreground = { Color = edge_foreground } },
		{ Text = SOLID_LEFT_ARROW },
		{ Background = { Color = background } },
		{ Foreground = { Color = foreground } },
		{ Text = title },
		{ Background = { Color = edge_background } },
		{ Foreground = { Color = edge_foreground } },
		{ Text = SOLID_RIGHT_ARROW },
	}
end)
-- and finally, return the configuration to wezterm
return config
