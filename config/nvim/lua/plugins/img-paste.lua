return {
  "HakonHarnes/img-clip.nvim",
  event = "VeryLazy",
  keys = {
    { "<leader>pi", "<cmd>PasteImage<cr>", desc = "Paste image from clipboard" },
  },
  opts = {
    default = {
      dir_path = "assets",
      file_name = "%Y%m%d%H%M%S",
      url_encode_path = true,
      use_absolute_path = false,
    },
    filetypes = {
      markdown = {
        dir_path = "assets",
        template = "![$CURSOR]($FILE_PATH)",
      },
    },
  },
}
