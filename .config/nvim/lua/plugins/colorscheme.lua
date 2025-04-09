return {
  {
    "craftzdog/solarized-osaka.nvim",
    enable = false,
    lazy = true,
    priority = 1000,
    opts = function()
      return {
        transparent = true,
      }
    end,
  },
  { "cocopon/iceberg.vim" },
  -- {
  -- "0xstepit/flow.nvim",
  -- lazy = false,
  -- priority = 1000,
  -- opts = {},
  -- config = function()
  --   require("flow").setup({
  --     transparent = true,
  --     fluo_color = "pink",
  --     mode = "normal",
  --     aggressive_spell = false,
  --   })
  --   vim.cmd("colorscheme flow")
  -- end,
  -- },
  -- add gruvbox
  -- { "ellisonleao/gruvbox.nvim" },

  -- Configure LazyVim to load gruvbox
  -- {
  --   "LazyVim/LazyVim",
  --   opts = {
  --     colorscheme = "gruvbox",
  --   },
  -- },
}
