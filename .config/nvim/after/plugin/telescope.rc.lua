if not vim.g.vscode then
	local status, telescope = pcall(require, "telescope")
	if not status then
		return
	end
	local actions = require("telescope.actions")
	local builtin = require("telescope.builtin")

	local function telescope_buffer_dir()
		return vim.fn.expand("%:p:h")
	end

	local fb_actions = require("telescope").extensions.file_browser.actions

	telescope.setup({
		defaults = {
			mappings = {
				n = {
					["q"] = actions.close,
				},
			},
		},
		extensions = {
			file_browser = {
				theme = "dropdown",
				-- disables netrw and use telescope-file-browser in its place
				hijack_netrw = true,
				mappings = {
					-- your custom insert mode mappings
					["i"] = {
						["<C-w>"] = function()
							vim.cmd("normal vbd")
						end,
					},
					["n"] = {
						-- your custom normal mode mappings
						["N"] = fb_actions.create,
						["h"] = fb_actions.goto_parent_dir,
						["/"] = function()
							vim.cmd("startinsert")
						end,
					},
				},
			},
		},
	})

	telescope.load_extension("file_browser")

	vim.keymap.set("n", "<leader><space>", function()
		builtin.resume()
	end, { desc = "Resume" })

	vim.keymap.set("n", "<leader>/", function()
		builtin.current_buffer_fuzzy_find()
	end, { desc = "[/] Fuzzily find in current buffer" })

	vim.keymap.set("n", "<leader>sf", function()
		builtin.find_files({
			no_ignore = false,
			hidden = true,
		})
	end, { desc = "[S]earch [F]iles" })

	vim.keymap.set("n", "<leader>sg", function()
		builtin.live_grep()
	end, { desc = "[S]earch by [G]rep" })

	vim.keymap.set("n", "<leader>sb", function()
		builtin.buffers()
	end, { desc = "[S]earch [B]uffers" })

	vim.keymap.set("n", "<leader>sh", function()
		builtin.help_tags()
	end, { desc = "[S]earch [H]elp" })

	vim.keymap.set("n", "<leader>sd", function()
		builtin.diagnostics()
	end, { desc = "[S]earch [D]iagnostics" })

	vim.keymap.set("n", "<leader>sk", function()
		builtin.keymaps()
	end, { desc = "[S]earch [K]eymaps" })

	vim.keymap.set("n", "<leader>sw", function()
		builtin.grep_string()
	end, { desc = "[S]earch [W]ord" })

	vim.keymap.set("n", "<leader>?", function()
		builtin.oldfiles()
	end, { desc = "[S]earch [?] Oldfiles" })

	vim.keymap.set("n", "sf", function()
		telescope.extensions.file_browser.file_browser({
			path = "%:p:h",
			cwd = telescope_buffer_dir(),
			respect_gitignore = false,
			hidden = true,
			grouped = true,
			previewer = false,
			initial_mode = "normal",
			layout_config = { height = 40 },
		})
	end)
end
