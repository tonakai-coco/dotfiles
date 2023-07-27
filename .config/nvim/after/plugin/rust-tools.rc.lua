if not vim.g.vscode then
	local status, rusttools = pcall(require, "rust-tools")
	if not status then
		print("rust-tools status failed.")
		return
	end

	local mason_registry = require("mason-registry")
	local codelldb = mason_registry.get_package("codelldb")
	local extension_path = codelldb:get_install_path() .. "/extension/"
	local codelldb_path = extension_path .. "adapter/codelldb"
	local liblldb_path = extension_path .. "lldb/lib/liblldb.dylib"

	-- print("rust-tools setup start.")
	rusttools.setup({
		dap = {
			adapter = require("rust-tools.dap").get_codelldb_adapter(codelldb_path, liblldb_path),
		},
		server = {
			capablilities = require("cmp_nvim_lsp").default_capabilities(),
			on_attach = function(_, bufnr)
				-- Hover actions
				vim.keymap.set("n", "<Leader>d", rusttools.hover_actions.hover_actions, { buffer = bufnr })
				-- Code action groups
				vim.keymap.set("n", "<Leader>a", rusttools.code_action_group.code_action_group, { buffer = bufnr })
			end,
		},
	})
end
