if not vim.g.vscode then
	local status, saga = pcall(require, "lspsaga")
	if not status then
		return
	end

	saga.setup({
		ui = {
			winblend = 10,
			border = "rounded",
			colors = {
				normal_bg = "#002b36",
			},
		},
	})

	local diagnostic = require("lspsaga.diagnostic")
	vim.keymap.set("n", "<leader>df", vim.diagnostic.open_float, { desc = "Open floating diagnostic message" })
	vim.keymap.set("n", "<leader>dq", vim.diagnostic.setloclist, { desc = "Open diagnostic list" })

	local opts = { noremap = true, silent = true }
	vim.keymap.set("n", "<C-j>", "<Cmd>Lspsaga diagnostic_jump_next<CR>", opts)
	-- vim.keymap.set("n", "gl", "<Cmd>Lspsaga show_diagnostic<CR>", opts)
	vim.keymap.set("n", "K", "<Cmd>Lspsaga hover_doc<CR>", opts)
	vim.keymap.set("n", "gd", "<Cmd>Lspsaga finder<CR>", opts)
	vim.keymap.set("n", "gt", "<Cmd>Lspsaga goto_definition<CR>", opts)
	-- vim.keymap.set('i', '<C-k>', '<Cmd>Lspsaga signature_help<CR>', opts)
	vim.keymap.set("i", "<C-k>", "<cmd>lua vim.lsp.buf.signature_help()<CR>", opts)
	vim.keymap.set("n", "gp", "<Cmd>Lspsaga peek_definition<CR>", opts)
	vim.keymap.set("n", "gr", "<Cmd>Lspsaga rename<CR>", opts)
	vim.keymap.set("n", "go", "<Cmd>Lspsaga outline<CR>", opts)

	local has = vim.fn.has
	local is_mac = has("mac")
	local is_win = has("win32") or has("win64")

	if is_mac == 1 then
		vim.keymap.set("n", "<M-t>", "<Cmd>Lspsaga term_toggle<CR>", opts)
		vim.keymap.set("t", "<M-t>", "<Cmd>Lspsaga term_toggle<CR>", opts)
	end
	if is_win == 1 then
		vim.keymap.set("n", "<A-t>", "<Cmd>Lspsaga term_toggle<CR>", opts)
		vim.keymap.set("t", "<A-t>", "<Cmd>Lspsaga term_toggle<CR>", opts)
	end

	-- code action
	local codeaction = require("lspsaga.codeaction")
	vim.keymap.set("n", "<leader>ca", function()
		codeaction:code_action()
	end, { silent = true })
	vim.keymap.set("v", "<leader>ca", function()
		vim.fn.feedkeys(vim.api.nvim_replace_termcodes("<C-U>", true, false, true))
		codeaction:range_code_action()
	end, { silent = true })
end
