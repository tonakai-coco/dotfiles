return {
  {
    "ludovicchabant/vim-gutentags",
    config = function()
      vim.g.gutentags_cache_dir = vim.fn.expand("~/.cache/tags")
    end,
  },

  {
    "skywind3000/gutentags_plus",
    enable = true,
    config = function()
      vim.g.gutentags_plus_switch = 1
    end,
    keys = function()
      return {}
    end,
  },
}
