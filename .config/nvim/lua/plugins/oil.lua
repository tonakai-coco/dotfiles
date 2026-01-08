return {
  {
    "stevearc/oil.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {},
    keys = {
      {
        "sf",
        function()
          require("oil").open_float()
        end,
        desc = "Open parent directory in floating window",
      },
    },
  },
}
