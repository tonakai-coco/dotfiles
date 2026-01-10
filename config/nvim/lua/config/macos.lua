vim.opt.clipboard:append { 'unnamedplus' }
vim.opt.shell = "fish"

-- Turn off IME when InsertLave and CmdLineLeave
vim.g.im_select_default = "com.apple.keylayout.ABC"
if vim.fn.executable("im-select") then
    vim.cmd("autocmd InsertLeave * :call system('im-select com.apple.keylayout.ABC')")
    vim.cmd("autocmd CmdlineLeave * :call system('im-select com.apple.keylayout.ABC')")
end
