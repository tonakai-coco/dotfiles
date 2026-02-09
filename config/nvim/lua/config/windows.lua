vim.opt.clipboard:prepend { 'unnamed', 'unnamedplus' }
local shell = vim.fn.executable("pwsh") == 1 and "pwsh" or "powershell.exe"
vim.opt.shell = shell
vim.opt.shellcmdflag =
  "-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues['Out-File:Encoding']='utf8';Remove-Alias -Force -ErrorAction SilentlyContinue tee;"
vim.opt.shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
vim.opt.shellpipe = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
vim.opt.shellquote = ""
vim.opt.shellxquote = ""

-- Turn off IME when InsertLave and CmdLineLeave
if vim.fn.executable("zenhan") then
    vim.cmd("autocmd InsertLeave * :call system('zenhan 0')")
    vim.cmd("autocmd CmdlineLeave * :call system('zenhan 0')")
end
