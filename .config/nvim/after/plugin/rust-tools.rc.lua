if not vim.g.vscode then
    local status, rusttools = pcall(require, "rust-tools")
    if not status then
        print("rust-tools status failed.")
        return
    end

    local mason_registry = require("mason-registry")
    local codelldb = mason_registry.get_package("codelldb")
    local extension_path = codelldb:get_install_path() .. "/extension/"
    local codelldb_path = extension_path .. 'adapter/codelldb'
    local liblldb_path = extension_path .. 'lldb/lib/liblldb'
    local this_os = vim.loop.os_uname().sysname;

    -- The path in windows is different
    if this_os:find "Windows" then
        codelldb_path = extension_path .. "adapter\\codelldb.exe"
        liblldb_path = extension_path .. "lldb\\bin\\liblldb.dll"
    else
        -- The liblldb extension is .so for linux and .dylib for macOS
        liblldb_path = liblldb_path .. (this_os == "Linux" and ".so" or ".dylib")
    end

    -- print("rust-tools setup start.")
    rusttools.setup({
        dap = {
            adapter = require("rust-tools.dap").get_codelldb_adapter(codelldb_path, liblldb_path),
        },
        server = {
            capablilities = require("cmp_nvim_lsp").default_capabilities(),
            on_attach = function(_, bufnr)
                -- Hover actions
                vim.keymap.set("n", "<Leader>d", rusttools.hover_actions.hover_actions, { buffer = bufnr })
                -- Code action groups
                vim.keymap.set("n", "<Leader>a", rusttools.code_action_group.code_action_group, { buffer = bufnr })
            end,
        },
    })
end
