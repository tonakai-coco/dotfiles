# gitleaks の導入

## Context

個人用 public リポジトリ `tonakai-coco/dotfiles` に、API キーやトークンの混入を commit 前と CI で止める。履歴の書き換えはしない。

## 対象

- 共通（OS の設定ファイルは変更しない）
- 追加するもの: `.githooks/pre-commit` `.github/workflows/gitleaks.yml` `README.md`

## 方針

- 既存の pre-commit フレームワーク、lefthook、mise 設定、Brewfile、セットアップスクリプトは無い。Makefile はシンボリックリンク専用なのでフック管理は混ぜない。
- フックはリポジトリ内の `.githooks/pre-commit` を `git config core.hooksPath .githooks` で有効化する。追加のフックマネージャを入れない。
- CI は gitleaks-action v3。所有者は GitHub の User アカウントで、公式 README / EULA / v3 の実装は Personal Account にライセンスキーを要求しない。スキャナのバージョンは 8.30.1 に固定する。
- 履歴全体を 8.30.1 で一度スキャンする。検出が無ければ allowlist も `.gitleaksignore` も追加しない。

## 検証

- 履歴スキャンの結果を記録する。
- 秘密らしいダミーをステージしてフックが commit を止めること、ダミーを外した通常の commit が通ることを確認する。ダミーはコミットしない。
- ワークフロー YAML を actionlint で確認する。
