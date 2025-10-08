-- keybinds_win.lua
-- Windows固有のキーバインドをここに記述します
local wezterm = require("wezterm")
local act = wezterm.action

return {
	keys = {
		-- コマンドパレット表示
		{ key = "p", mods = "CTRL|SHIFT", action = act.ActivateCommandPalette },
		-- Tab新規作成
		{ key = "t", mods = "CTRL|SHIFT", action = act({ SpawnTab = "CurrentPaneDomain" }) },
		-- Tabを閉じる
		{ key = "w", mods = "CTRL|SHIFT", action = act({ CloseCurrentTab = { confirm = true } }) },
		-- コピー
		{ key = "c", mods = "CTRL|SHIFT", action = act.CopyTo("Clipboard") },
		-- 貼り付け
		{ key = "v", mods = "CTRL|SHIFT", action = act.PasteFrom("Clipboard") },
		-- 検索
		{ key = "f", mods = "CTRL|SHIFT", action = act.Search("CurrentSelectionOrEmptyString") },

		-- タブ切替 Ctrl+Shift + 数字
		{ key = "1", mods = "CTRL|SHIFT", action = act.ActivateTab(0) },
		{ key = "2", mods = "CTRL|SHIFT", action = act.ActivateTab(1) },
		{ key = "3", mods = "CTRL|SHIFT", action = act.ActivateTab(2) },
		{ key = "4", mods = "CTRL|SHIFT", action = act.ActivateTab(3) },
		{ key = "5", mods = "CTRL|SHIFT", action = act.ActivateTab(4) },
		{ key = "6", mods = "CTRL|SHIFT", action = act.ActivateTab(5) },
		{ key = "7", mods = "CTRL|SHIFT", action = act.ActivateTab(6) },
		{ key = "8", mods = "CTRL|SHIFT", action = act.ActivateTab(7) },
		{ key = "9", mods = "CTRL|SHIFT", action = act.ActivateTab(-1) },
	},
}

