vim.g.mapleader = " " -- <Leader>をスペースに設定

local keymap = vim.keymap
keymap.set({ "n", "v" }, "<Space>", "<Nop>", { silent = true })
keymap.set("n", "x", '"_x')
keymap.set("n", "k", "v:count == 0 ? 'gk' : 'k'", { expr = true, silent = true })
keymap.set("n", "j", "v:count == 0 ? 'gj' : 'j'", { expr = true, silent = true })

-- Increment/decrement
keymap.set("n", "+", "<C-a>")
keymap.set("n", "-", "<C-x>")

-- Delete a word backwards
keymap.set("n", "dw", 'vb"_d')

-- Select all
keymap.set("n", "<C-a>", "gg<S-v>G")

-- Save with root permission (not working for now)
-- vim.api.nvim_create_user_command('W', 'w !sudo tee > /dev/null %', {})

keymap.set("i", "jj", "<Esc>", {
    noremap = true,
    silent = true,
})

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

if not vim.g.vscode then
    -- New tab
    keymap.set("n", "te", ":tabedit")
    -- Close tab
    keymap.set("n", "td", ":tabclose")

    -- Split window
    keymap.set("n", "ss", ":split<Return><C-w>w")
    keymap.set("n", "sv", ":vsplit<Return><C-w>w")
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

    -- keymap.set("n", "<Space>s", ":source $MYVIMRC<Return>", {
    -- 	noremap = true,
    -- }) -- init.vim読み込み
    keymap.set("n", "<Leader>w", ":<C-u>w<Return>", {
        noremap = true,
    }) -- init.vim読み込み
    keymap.set("n", "<Leader>q", ":<C-u>q<Return>", {
        noremap = true,
    }) -- init.vim読み込み

    -- Terminal
    keymap.set("t", "<Esc>", "<C-\\><C-n>", {
        noremap = true,
    })
else
    -- keymap.set("n", "<Leader>s", ":source $MYVIMRC<Return>", {
    -- 	noremap = true,
    -- }) -- init.vim読み込み
    keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", {
        noremap = true,
    })
    keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", {
        noremap = true,
    })
    keymap.set("n", "<Leader>e", "<cmd>call VSCodeNotify('workbench.action.toggleSidebarVisibility')<cr>", {
        noremap = true,
    })
end
