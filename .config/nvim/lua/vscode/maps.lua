vim.g.mapleader = " " -- <Leader>をスペースに設定

local keymap = vim.keymap
keymap.set("n", "x", '"_x')

-- Increment/decrement
keymap.set("n", "+", "<C-a>")
keymap.set("n", "-", "<C-x>")

-- Delete a word backwards
keymap.set("n", "dw", 'vb"_d')

-- Select all
keymap.set("n", "<C-a>", "gg<S-v>G")

-- Original settings
keymap.set("n", "<Leader>s", ":source $MYVIMRC<Return>", { noremap = true }) -- init.vim読み込み
keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", { noremap = true })
keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", { noremap = true })

keymap.set("i", "jj", "<Esc>", { noremap = true, silent = true })
keymap.set("i", "っj", "<Esc>", { noremap = true, silent = true })
