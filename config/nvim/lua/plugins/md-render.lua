return {
  {
    "delphinus/md-render.nvim",
    ft = "markdown",
    dependencies = {
      "nvim-tree/nvim-web-devicons",
      { "delphinus/budoux.lua" },
    },
    keys = {
      { "<leader>mp", "<Plug>(md-render-preview)", desc = "Preview (toggle)" },
      { "<leader>mt", "<Plug>(md-render-preview-tab)", desc = "Preview in tab" },
      { "<leader>md", "<Plug>(md-render-demo)", desc = "Demo" },
    },
  },
}
