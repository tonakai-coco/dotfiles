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

-- Save with root permission (not working for now)
-- vim.api.nvim_create_user_command('W', 'w !sudo tee > /dev/null %', {})

keymap.set("i", "jj", "<Esc>", {
    noremap = true,
    silent = true,
})
keymap.set("i", "っj", "<Esc>", {
    noremap = true,
    silent = true,
})

-- vim.api.nvim_set_keymap("n", "S*", [[:%s/\<]] .. vim.fn.expand("<cword>") .. [[\>//gc<left><left>]], { noremap = true })
keymap.set("n", "S*", ":%s/", { noremap = true })

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

    -- Original settings
    keymap.set("n", "<Space>s", ":source $MYVIMRC<Return>", {
        noremap = true,
    }) -- init.vim読み込み
    keymap.set("n", "<Space>w", ":<C-u>w<Return>", {
        noremap = true,
    }) -- init.vim読み込み
    keymap.set("n", "<Space>q", ":<C-u>q<Return>", {
        noremap = true,
    }) -- init.vim読み込み

    -- Terminal
    keymap.set('t', '<Esc>', '<C-\\><C-n>', {
        noremap = true
    })
else
    -- Original settings
    keymap.set("n", "<Leader>s", ":source $MYVIMRC<Return>", {
        noremap = true,
    }) -- init.vim読み込み
    keymap.set("n", "<Leader>w", "<cmd>call VSCodeNotify('workbench.action.files.save')<cr>", {
        noremap = true,
    })
    keymap.set("n", "<Leader>q", "<cmd>call VSCodeNotify('workbench.action.closeActiveEditor')<cr>", {
        noremap = true,
    })
end
