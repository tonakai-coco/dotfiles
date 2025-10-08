-- keybinds_mac.lua
-- macOS固有のキーバインドをここに記述します
local wezterm = require("wezterm")
local act = wezterm.action

return {
	keys = {
		-- コマンドパレット表示
		{ key = "p", mods = "SUPER", action = act.ActivateCommandPalette },
		-- Tab新規作成
		{ key = "t", mods = "SUPER", action = act({ SpawnTab = "CurrentPaneDomain" }) },
		-- Tabを閉じる
		{ key = "w", mods = "SUPER", action = act({ CloseCurrentTab = { confirm = true } }) },
		-- コピー
		{ key = "c", mods = "SUPER", action = act.CopyTo("Clipboard") },
		-- 貼り付け
		{ key = "v", mods = "SUPER", action = act.PasteFrom("Clipboard") },

		-- タブ切替 Cmd + 数字
		{ key = "1", mods = "SUPER", action = act.ActivateTab(0) },
		{ key = "2", mods = "SUPER", action = act.ActivateTab(1) },
		{ key = "3", mods = "SUPER", action = act.ActivateTab(2) },
		{ key = "4", mods = "SUPER", action = act.ActivateTab(3) },
		{ key = "5", mods = "SUPER", action = act.ActivateTab(4) },
		{ key = "6", mods = "SUPER", action = act.ActivateTab(5) },
		{ key = "7", mods = "SUPER", action = act.ActivateTab(6) },
		{ key = "8", mods = "SUPER", action = act.ActivateTab(7) },
		{ key = "9", mods = "SUPER", action = act.ActivateTab(-1) },
	},
}
