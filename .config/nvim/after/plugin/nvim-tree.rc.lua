if not vim.g.vscode then
	local status, nvimtree = pcall(require, "nvim-tree")
	if not status then
		return
	end

	nvimtree.setup({
		sort_by = "case_sensitive",
		view = {
			width = 40,
		},
		renderer = {
			group_empty = true,
		},
		filters = {
			dotfiles = true,
		},
	})

	vim.keymap.set("n", "<leader>e", "<cmd>NvimTreeToggle<cr>", opts)
end
