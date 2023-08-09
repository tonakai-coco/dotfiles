if not vim.g.vscode then
	vim.opt.cursorline = true
	vim.opt.termguicolors = true
	vim.opt.winblend = 0
	vim.opt.wildoptions = "pum"
	vim.opt.pumblend = 5
	vim.opt.background = "dark"

	-- [[ Highlight on yank ]]
	-- See `:help vim.highlight.on_yank()`
	local highlight_group = vim.api.nvim_create_augroup("YankHighlight", { clear = true })
	vim.api.nvim_create_autocmd("TextYankPost", {
		callback = function()
			vim.highlight.on_yank()
		end,
		group = highlight_group,
		pattern = "*",
	})
end
