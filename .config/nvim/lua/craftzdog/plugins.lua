if not vim.g.vscode then
	local status, packer = pcall(require, "packer")
	if not status then
		print("Packer is not installed")
		return
	end

	vim.cmd([[packadd packer.nvim]])

	packer.startup(function(use)
		use("wbthomason/packer.nvim")
		use("vim-jp/vimdoc-ja")
		use({
			"svrana/neosolarized.nvim",
			requires = { "tjdevries/colorbuddy.nvim" },
		})
		use("nvim-lualine/lualine.nvim") -- Statusline
		use("nvim-lua/plenary.nvim") -- Common utilities
		use("onsails/lspkind-nvim") -- vscode-like pictograms
		use("hrsh7th/cmp-buffer") -- nvim-cmp source for buffer words
		use("hrsh7th/cmp-nvim-lsp") -- nvim-cmp source for neovim's built-in LSP
		use("hrsh7th/nvim-cmp") -- Completion
		use("neovim/nvim-lspconfig") -- LSP
		use("jose-elias-alvarez/null-ls.nvim") -- Use Neovim as a language server to inject LSP diagnostics, code actions, and more via Lua
		-- use 'MunifTanjim/prettier.nvim'
		use("williamboman/mason.nvim")
		use("williamboman/mason-lspconfig.nvim")
		use("simrat39/rust-tools.nvim")
		use("mfussenegger/nvim-dap")
		use("rcarriga/nvim-dap-ui")

		use("glepnir/lspsaga.nvim") -- LSP UIs
		use("L3MON4D3/LuaSnip")
		use({
			"nvim-treesitter/nvim-treesitter",
			run = function()
				require("nvim-treesitter.install").update({
					with_sync = true,
				})
			end,
		})
		use("kyazdani42/nvim-web-devicons") -- File icons
		use("nvim-telescope/telescope.nvim")
		use("nvim-telescope/telescope-file-browser.nvim")
		use("windwp/nvim-autopairs")
		use("windwp/nvim-ts-autotag")
		use({
			"numToStr/Comment.nvim",
			requires = { "JoosepAlviste/nvim-ts-context-commentstring" },
		})
		use("norcalli/nvim-colorizer.lua")
		use("folke/zen-mode.nvim")
		use({
			"iamcco/markdown-preview.nvim",
			run = function()
				vim.fn["mkdp#util#install"]()
			end,
		})
		use("akinsho/nvim-bufferline.lua")
		-- use 'github/copilot.vim'

		use("lewis6991/gitsigns.nvim")
		use("dinhhuy258/git.nvim") -- For git blame & browse

		use({
			"kylechui/nvim-surround",
			tag = "*", -- Use for stability; omit to use `main` branch for the latest features
			config = function()
				require("nvim-surround").setup({
					-- Configuration here, or leave empty to use defaults
				})
			end,
		})
		use({
			"nvim-tree/nvim-tree.lua",
			requires = {
				"nvim-tree/nvim-web-devicons", -- optional
			},
			config = function()
				require("nvim-tree").setup({})
			end,
		})
		-- Vim configuration for Rust
		--	use({
		--		"rust-lang/rust.vim",
		--		ft = { "rust" },
		--		config = function()
		--			require("plugins.rust")
		--		end,
		--	})
		use({
			"jackMort/ChatGPT.nvim",
			config = function()
				require("chatgpt").setup()
			end,
			requires = {
				"MunifTanjim/nui.nvim",
				"nvim-lua/plenary.nvim",
				"nvim-telescope/telescope.nvim",
			},
		})
		use({
			"folke/which-key.nvim",
			config = function()
				vim.o.timeout = true
				vim.o.timeoutlen = 300
				require("which-key").setup({
					-- your configuration comes here
					-- or leave it empty to use the default settings
					-- refer to the configuration section below
				})
			end,
		})
	end)
end
