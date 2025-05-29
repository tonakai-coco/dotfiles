vim.g.mapleader = " " -- <Leader>をスペースに設定
local keymap = vim.keymap
local opts = { noremap = true, silent = true }

-- Increment/decrement
keymap.set("n", "+", "<C-a>")
keymap.set("n", "-", "<C-x>")

-- Delete a word backwards
keymap.set("n", "dw", 'vb"_d')

-- Select all
keymap.set("n", "<C-a>", "gg<S-v>G")

-- Turn off IME when leaving insert
keymap.set("i", "<Esc>", "<Esc>:set iminsert=0<cr>", {
  noremap = true,
})

-- vim.api.nvim_set_keymap("n", "S*", [[:%s/\<]] .. vim.fn.expand("<cword>") .. [[\>//gc<left><left>]], { noremap = true })
keymap.set("n", "S*", ":%s/", { noremap = true })

-- visualモードの場合にvを押すと矩形選択モードにする
keymap.set("v", "v", "<C-v>", {
  noremap = true,
})

-- VSCodeのキーバインドを設定
keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", {
  noremap = true,
})

keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", {
  noremap = true,
})

keymap.set("n", "<Leader>e", "<cmd>call VSCodeNotify('workbench.action.toggleSidebarVisibility')<cr>", {
  noremap = true,
})

keymap.set("n", "<Leader>ff", "<cmd>call VSCodeNotify('workbench.action.quickOpen')<cr>", {
  noremap = true,
})