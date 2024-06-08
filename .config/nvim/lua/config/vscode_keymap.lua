vim.g.mapleader = " " -- <Leader>をスペースに設定
local keymap = vim.keymap
keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", {
  noremap = true,
})
keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", {
  noremap = true,
})
keymap.set("n", "<Leader>e", "<cmd>call VSCodeNotify('workbench.action.toggleSidebarVisibility')<cr>", {
  noremap = true,
})
