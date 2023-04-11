if not vim.g.vscode then
	local status, autopairs = pcall(require, "nvim-autopairs")
	if not status then
		return
	end

	autopairs.setup({
		disable_filetype = { "TelescopePrompt", "vim" },
	})
end
