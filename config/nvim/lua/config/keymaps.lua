-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here
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

-- New tab
keymap.set("n", "te", ":tabedit")

-- NOTE: <Tab> と <C-i> は同じキーコードのため Ctrl-i のジャンプ履歴に影響しないようにする
keymap.set("n", "<leader>tn", ":tabnext<Return>", opts)
keymap.set("n", "<leader>tp", ":tabprev<Return>", opts)

-- Split window
keymap.set("n", "ss", ":split<Return><C-w>w")
keymap.set("n", "sv", ":vsplit<Return><C-w>w")
--
-- Move window
-- keymap.set('n', '<Space>', '<C-w>w')
keymap.set("", "sh", "<C-w>h")
keymap.set("", "sk", "<C-w>k")
keymap.set("", "sj", "<C-w>j")
keymap.set("", "sl", "<C-w>l")

-- Resize window
keymap.set("n", "<C-w><left>", "<C-w><")
keymap.set("n", "<C-w><right>", "<C-w>>")
keymap.set("n", "<C-w><up>", "<C-w>+")
keymap.set("n", "<C-w><down>", "<C-w>-")

-- Terminal
keymap.set("t", "<Esc>", "<C-\\><C-n>", {
  noremap = true,
})

--Diagnostics
keymap.set("n", "<C-j>", function()
  vim.diagnostic.goto_next()
end, opts)

-- Copy File Path
local function copy_current_file_path()
  local path = vim.fn.expand("%:.")
  vim.fn.setreg("*", path)
  vim.api.nvim_echo({ { "Copied: " .. path, "None" } }, true, {})
end

keymap.set("n", "<Leader>yp", copy_current_file_path, {
  noremap = true,
  silent = true,
  desc = "Copy current file path",
})

-- Copy File Name
local function copy_current_file_name()
  local fileName = vim.fn.expand("%:t")
  vim.fn.setreg("*", fileName)
  vim.api.nvim_echo({ { "Copied: " .. fileName, "None" } }, true, {})
end

keymap.set("n", "<Leader>yn", copy_current_file_name, {
  noremap = true,
  silent = true,
  desc = "Copy current file name",
})
