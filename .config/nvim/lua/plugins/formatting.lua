return {
  {
    "stevearc/conform.nvim",
    opts = {
      formatters_by_ft = {
        c = { "clang-format" },
        cpp = { "clang-format" },
      },
      formatters = {
        clang_format = {
          prepend_args = { "--style=file", "--fallback-style=LLVM" },
        },
      },
    },
  },
}
