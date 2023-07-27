if not vim.g.vscode then
	local status_dap, dap = pcall(require, "dap")
	local status_dapui, dapui = pcall(require, "dapui")
	if not status_dap or not status_dapui then
		print("dap or dapui status error.")
		return
	end

	-- print("dapui setup start.")
	dapui.setup()

	dap.listeners.after.event_initialized["dapui_config"] = function()
		dapui.open()
	end
	dap.listeners.before.event_terminated["dapui_config"] = function()
		dapui.close()
	end
	dap.listeners.before.event_exited["dapui_config"] = function()
		dapui.close()
	end

	vim.keymap.set("n", "<Leader>dt", ":DapToggleBreakpoint<CR>")
	vim.keymap.set("n", "<Leader>dx", ":DapTerminate<CR>")
	vim.keymap.set("n", "<Leader>dc", ":DapContinue<CR>")
	vim.keymap.set("n", "<Leader>do", ":DapStepOver<CR>")
	vim.keymap.set("n", "<Leader>di", ":DapStepInto<CR>")
end
