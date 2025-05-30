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

-- VSCodeコマンドのキーバインドを設定
-- ファイルを保存
keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", {
  noremap = true,
})

-- VSCodeのエディタを閉じる
keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", {
  noremap = true,
})

-- VSCodeのサイドバーをトグル
keymap.set("n", "<Leader>e", "<cmd>call VSCodeNotify('workbench.action.toggleSidebarVisibility')<cr>", {
  noremap = true,
})

-- ファイルを開く
keymap.set("n", "<Leader>ff", "<cmd>call VSCodeNotify('workbench.action.quickOpen')<cr>", {
  noremap = true,
})

-- 検索を開く
keymap.set("n", "<Leader>/", "<cmd>call VSCodeNotify('workbench.view.search')<cr>", {
  noremap = true,
})

-- ターミナルを開く
keymap.set("n", "<Leader>t", "<cmd>call VSCodeNotify('workbench.action.terminal.toggleTerminal')<cr>", {
  noremap = true,
})

-- ソース管理を開く
keymap.set("n", "<Leader>gg", "<cmd>call VSCodeNotify('workbench.view.scm')<cr>", {
  noremap = true,
})

-- エディタを縦に分割
keymap.set("n", "sv", "<cmd>call VSCodeNotify('workbench.action.splitEditor')<cr>", {
  noremap = true,
})

-- エディタを横に分割
keymap.set("n", "ss", "<cmd>call VSCodeNotify('workbench.action.splitEditorDown')<cr>", {
  noremap = true,
})

-- エディタ間の移動（左へ）
keymap.set("n", "sh", "<cmd>call VSCodeNotify('workbench.action.focusLeftGroup')<cr>", {
  noremap = true,
})

-- エディタ間の移動（右へ）
keymap.set("n", "sl", "<cmd>call VSCodeNotify('workbench.action.focusRightGroup')<cr>", {
  noremap = true,
})

-- エディタ間の移動（下へ）
keymap.set("n", "sj", "<cmd>call VSCodeNotify('workbench.action.focusBelowGroup')<cr>", {
  noremap = true,
})

-- エディタ間の移動（上へ）
keymap.set("n", "sk", "<cmd>call VSCodeNotify('workbench.action.focusAboveGroup')<cr>", {
  noremap = true,
})

-- Format
keymap.set("n", "<Leader>cf", "<cmd>call VSCodeNotify('editor.action.formatDocument')<cr>", {
  noremap = true,
})

-- ホバー情報の表示
keymap.set("n", "K", "<cmd>call VSCodeNotify('editor.action.showHover')<cr>", {
  noremap = true,
})

-- すべての参照を表示
keymap.set("n", "<Leader>gr", "<cmd>call VSCodeNotify('references-view.findReferences')<cr>", {
  noremap = true,
})

-- Github Copilot Chatの表示
keymap.set({ "n", "v" }, "<Leader>aa", "<cmd>call VSCodeNotify('workbench.panel.chat.view.copilot.focus')<cr>", {
  noremap = true,
})

-- これを説明する
keymap.set({ "n", "v" }, "<Leader>ae", "<cmd>call VSCodeNotify('github.copilot.chat.explain.palette')<cr>", {
  noremap = true,
})
