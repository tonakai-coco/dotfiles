return {
  {
    "stevearc/oil.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {},
    init = function()
      vim.api.nvim_create_autocmd("VimEnter", {
        nested = true,
        callback = function()
          local bufname = vim.api.nvim_buf_get_name(0)
          if vim.fn.isdirectory(bufname) == 1 then
            require("oil").open(bufname)
          end
        end,
      })
    end,
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
