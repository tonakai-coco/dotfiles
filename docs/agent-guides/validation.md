# Agent Guide: Validation

変更したパスに応じて次を実行する。未実施なら理由を記録する。

## Always

- 作業前: `git status --short`
- 差分確認: `git diff -- <path>`

## Link Management

- リンク定義や `Makefile` を変更したら `make check`
- 同上で `make status`

## Neovim

- 対象: `config/nvim/`
- 整形: `stylua --config config/nvim/stylua.toml config/nvim/lua/**/*.lua`
- ヘルスチェック: `nvim --headless "+checkhealth" +qa`
- 必要時の同期: `nvim --headless "+Lazy sync" +qa`

## Fish

- 対象: `config/fish/functions/*.fish`
- 整形: `fish_indent --write config/fish/functions/*.fish`

## Karabiner

- 対象: `config/karabiner/*.json`
- 構文確認: `jq empty config/karabiner/numpad.json`

## WezTerm

- 対象: `config/wezterm/`
- 起動確認: `wezterm --config-file config/wezterm/wezterm.lua start --always-new-process`
- GUI を起動できない環境では未実施理由を記録する。

## Tmux

- 対象: `config/tmux/`
- リロード: `tmux source-file ~/.config/tmux/tmux.conf`
- セッションがなければ未実施理由を記録する。
