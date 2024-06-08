-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here

-- Turn off paste mode when leaving insert
vim.api.nvim_create_autocmd("InsertLeave", {
  pattern = "*",
  command = "set nopaste",
})

vim.cmd([[
  augroup MarkdownAutoList
    autocmd!
    autocmd FileType markdown setlocal formatoptions-=c formatoptions+=jro
    autocmd FileType markdown setlocal comments=b:*,b:-,b:+,b:1.,nb:>
  augroup END
]])
