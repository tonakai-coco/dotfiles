-- vim-translator: English <-> Japanese translation
-- Keymap:
--   <leader>tw - Translate and show in window (Visual/Normal)
--   <leader>tr - Translate and replace to Japanese (Visual/Normal)
--   <leader>tR - Translate and replace to English (Visual)
return {
  "voldikss/vim-translator",
  keys = {
    -- Window display (non-destructive)
    { "<leader>tw", "<Plug>TranslateW", mode = "n", desc = "Translate (window)" },
    { "<leader>tw", "<Plug>TranslateWV", mode = "v", desc = "Translate (window)" },
    -- Replace with translation (to Japanese)
    { "<leader>tr", "<Plug>TranslateR", mode = "n", desc = "Translate to Japanese (replace)" },
    { "<leader>tr", "<Plug>TranslateRV", mode = "v", desc = "Translate to Japanese (replace)" },
    -- Replace with translation (to English)
    { "<leader>tR", "<Cmd>TranslateR --target_lang=en<CR>", mode = "v", desc = "Translate to English (replace)" },
  },
  config = function()
    -- Use Google Translate (no API key required)
    vim.g.translator_default_engines = { "google" }

    -- Target language: Japanese
    -- vim-translator auto-detects source language
    -- If source is Japanese, it translates to English (via translator_source_lang)
    vim.g.translator_target_lang = "ja"

    -- Window settings
    vim.g.translator_window_type = "popup"
    vim.g.translator_window_max_width = 0.6
    vim.g.translator_window_max_height = 0.6
  end,
}
