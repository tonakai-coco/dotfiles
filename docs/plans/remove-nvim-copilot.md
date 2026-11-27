# Neovim から GitHub Copilot 系プラグインを削除する

## 背景

GitHub Copilot の契約を解約したため、Neovim の Copilot 系プラグインは不要になった。

## 対象 OS・ディレクトリ

- 全 OS 共通
- `config/nvim/`

## 変更内容

- `config/nvim/lua/config/lazy.lua` から LazyVim extras `ai.copilot` と `ai.copilot-chat` の import を削除する
- `config/nvim/lua/plugins/ai.lua`（CopilotChat.nvim のキーマップ設定）を削除する
- `config/nvim/lazy-lock.json` から `CopilotChat.nvim` `blink-copilot` `copilot.lua` を削除する
- `config/nvim/lua/config/vscode_keymap.lua` から VSCode の Copilot Chat を呼ぶキーマップ（`<Leader>aa` `<Leader>ae` `<Leader>ai` `<Leader>aq`）を削除する

## 対象外

- `ai/copilot/` と `.github/copilot-instructions.md`（Copilot CLI と Copilot 向けエージェント入口のため）

## 検証

- `jq empty config/nvim/lazy-lock.json`
- `nvim --headless "+Lazy! clean" ... +qa` で起動し、Copilot 系プラグインが 0 件であることと、3 つのプラグインが clean されることを確認した
- 起動時の `refactoring.nvim requires Neovim 0.12 or higher` はローカルの Neovim のバージョンによるもので、今回の変更とは関係ない
- `nvim --headless -u NONE "+luafile config/nvim/lua/config/vscode_keymap.lua" +qa` でエラーなく読み込めることを確認した
- `stylua` はローカルにないため未実施。Lua は行を削除しただけ
