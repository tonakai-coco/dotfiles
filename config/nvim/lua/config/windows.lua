vim.opt.clipboard:prepend({ "unnamed", "unnamedplus" })
local shell = vim.fn.executable("pwsh") == 1 and "pwsh" or "powershell.exe"
vim.opt.shell = shell
vim.opt.shellcmdflag =
  "-NoLogo -ExecutionPolicy RemoteSigned -Command [Console]::InputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$PSDefaultParameterValues['Out-File:Encoding']='utf8';Remove-Alias -Force -ErrorAction SilentlyContinue tee;"
vim.opt.shellredir = '2>&1 | %%{ "$_" } | Out-File %s; exit $LastExitCode'
vim.opt.shellpipe = '2>&1 | %%{ "$_" } | tee %s; exit $LastExitCode'
vim.opt.shellquote = ""
vim.opt.shellxquote = ""

-- Turn off IME when InsertLeave and CmdlineLeave (use vim.uv.spawn to bypass shell)
if vim.fn.executable("zenhan") == 1 then
  vim.api.nvim_create_autocmd({ "InsertLeave", "CmdlineLeave" }, {
    callback = function()
      vim.uv.spawn("zenhan", { args = { "0" }, hide = true }, function() end)
    end,
  })
end
