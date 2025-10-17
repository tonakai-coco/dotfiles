# Repository Guidelines

## プロジェクト構成とモジュール整理

このリポジトリは `~/.config` 以下の設定資産を macOS・Linux・Windows で共有するためのものです。

OS 固有の変更は既存の専用ディレクトリに 閉じ込めてください。

主な構成は、シェル略称や起動スクリプトをまとめた `fish/`、 LazyVim ベースの Lua モジュールを置く `nvim/` （コア設定は `lua/config`、プラグイン定義は `lua/plugins`、 整形ルールは `stylua.toml`）、 OS ごとのキーバインドを分けた `wezterm/`、 macOS のキーマップを扱う `karabiner/numpad.json`、 Windows 用プロファイルの `powershell/user_profile.ps1`、 tmux 設定の `tmux/tmux.conf`、 そして軽量な Vim 代替の `ubuntu_nvim/` です。

## ビルド・テスト・開発コマンド

プラグイン宣言を編集したら `nvim --headless "+Lazy sync" +qa` を実行しロックファイルを更新します。

Lua モジュールは `stylua --config nvim/stylua.toml nvim/lua/**/*.lua` で整形してください。

Fish スクリプトは `fish_indent --write fish/functions/*.fish` で整えます。

Karabiner 設定は同期前に `jq empty karabiner/numpad.json` で構文検証します。

wezterm の調整後は `wezterm --config-file wezterm/wezterm.lua start --always-new-process` でスモークテストを行います。

## コーディングスタイルと命名規則

Lua は 2 スペースインデントとし、 `stylua` が期待する順序規則に従います。
モジュール名は小文字＋アンダースコアで統一します （例: `lua/plugins/editor.lua`）。

Fish 関数は `snake_case` を維持し、 `conf.d` から宣言的に読み込ませます。

tmux オプションは機能ごとにまとまりを持たせ、 非デフォルトの理由を示すコメントは最小限に留めます。

JSON は終端改行を保ち、 可能ならキーをアルファベット順に整列させ、 ダブルクォートを使用します。

## テストと検証

Neovim 設定を変更したら `nvim --headless "+checkhealth" +qa` でプラグインやプロバイダの状態を確認します。

Fish の更新前には `fish -c "for f in fish/functions/*.fish; fish_indent --check $f; end"` を走らせて整形崩れを検知します。

wezterm の変更は `wezterm -n --config-file wezterm/wezterm.lua` から REPL を起動します。

`require "keybinds_mac"` などで 各モジュールが読み込めるか確認します。

tmux は稼働中のセッションで `tmux source-file ~/.config/tmux/tmux.conf` を実行し、リロードできるかテストしてください。

## コミットとプルリクエストの指針

Git ログが示す Conventional Commits （`feat: ...`、`fix: ...`、`chore: ...`）を踏襲し、 件名は簡潔にまとめます。
1 つの論理変更ごとにコミットを分けると 同期スクリプトが扱いやすくなります。
プルリクエストでは動機、 影響するディレクトリ、 必要な手動手順 （例: `nvim --headless "+Lazy sync"` の再実行） を記載してください。

テーマやキーバインドなど視覚変更がある場合は スクリーンショットを添えます。 関連 Issue とのリンクと、 クロスプラットフォームへの影響有無も明記しましょう。

## セキュリティと設定のヒント

ホスト固有のシークレットやトークン、 SSH 情報は絶対にコミットせず、 バージョン管理外にホストごとのオーバーライドを 保持します。
新しいツールを追加する際は `$XDG_CONFIG_HOME` に対応しているかを確認し、 絶対パスのハードコードより 環境変数を優先してください。
