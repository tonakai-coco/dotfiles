if not vim.g.vscode then
	local status, colorizer = pcall(require, "colorizer")
	if not status then
		return
	end

	colorizer.setup({
		"*",
	})
end
