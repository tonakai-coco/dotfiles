vim.cmd("autocmd!")

if not vim.g.vscode then
    vim.scriptencoding = "utf-8"
    vim.opt.encoding = "utf-8"
    vim.opt.fileencoding = "utf-8"

    vim.wo.number = true

    vim.opt.title = true
    vim.opt.autoindent = true
    vim.opt.smartindent = true
    vim.opt.hlsearch = true
    vim.opt.backup = false
    vim.opt.showcmd = true
    vim.opt.cmdheight = 1
    vim.opt.laststatus = 2
    vim.opt.expandtab = true
    vim.opt.scrolloff = 10
    vim.opt.backupskip = { "/tmp/*", "/private/tmp/*" }
    vim.opt.inccommand = "split"
    vim.opt.ignorecase = true -- Case insensitive searching UNLESS /C or capital in search
    vim.opt.smarttab = true
    vim.opt.breakindent = true
    vim.opt.shiftwidth = 4
    vim.opt.tabstop = 4
    vim.opt.wrap = false          -- No Wrap lines
    vim.opt.backspace = { "start", "eol", "indent" }
    vim.opt.path:append({ "**" }) -- Finding files - Search down into subfolders
    vim.opt.wildignore:append({ "*/node_modules/*" })
    vim.opt.shell = "powershell.exe"

    -- Undercurl
    vim.cmd([[let &t_Cs = "\e[4:3m"]])
    vim.cmd([[let &t_Ce = "\e[4:0m"]])

    -- Turn off paste mode when leaving insert
    vim.api.nvim_create_autocmd("InsertLeave", {
        pattern = "*",
        command = "set nopaste",
    })

    -- Add asterisks in block comments
    vim.opt.formatoptions:append({ "r" })

    vim.cmd([[
  augroup MarkdownAutoList
    autocmd!
    autocmd FileType markdown setlocal formatoptions-=c formatoptions+=jro
    autocmd FileType markdown setlocal comments=b:*,b:-,b:+,b:1.,nb:>
  augroup END
]])
end

-- Turn off IME when InsertLave and CmdLineLeave
if vim.fn.executable("zenhan") then
    vim.cmd("autocmd InsertLeave * :call system('zenhan 0')")
    vim.cmd("autocmd CmdlineLeave * :call system('zenhan 0')")
end

vim.g.im_select_default = "com.apple.keylayout.ABC"
if vim.fn.executable("im-select") then
    vim.cmd("autocmd InsertLeave * :call system('im-select com.apple.keylayout.ABC')")
    vim.cmd("autocmd CmdlineLeave * :call system('im-select com.apple.keylayout.ABC')")
end
