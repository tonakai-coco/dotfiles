vim.opt.clipboard:prepend { 'unnamed', 'unnamedplus' }
-- TODO:以下を有効にするとIME切り替えautocmdが正常に動作しない
-- vim.opt.shell = "powershell.exe"

-- Turn off IME when InsertLave and CmdLineLeave
if vim.fn.executable("zenhan") then
    vim.cmd("autocmd InsertLeave * :call system('zenhan 0')")
    vim.cmd("autocmd CmdlineLeave * :call system('zenhan 0')")
end
