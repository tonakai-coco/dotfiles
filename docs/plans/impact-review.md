# Plan: Impact Review 導入

## Goal

`data-workflow-tools/tools/impact-review` の PR 自動レビュー機能を、この dotfiles リポジトリへ組み込む。

## Scope

- `tools/impact-review/` をソースからコピー（本体ロジックは改変しない）
- `.github/workflows/impact-review.yml` を追加
- `.impact-review.yml` を追加（`docs/plans/**` と互換用 `generated/**` を ignore）
- 導入手順は `tools/impact-review/README.md` に記載

## Out of Scope

- LLM 本体ロジックの改変
- ルート `README.md` への手順追記
- GitHub Secrets / Variables の自動設定（手動）
- issue-auto-pr の `SAKURA_AI_*` との秘密情報統合

## Steps

1. `tools/impact-review/` をコピーし、導入手順付き README を作成
2. workflow と `.impact-review.yml` を追加
3. オフライン unittest を実行
4. 本計画を `docs/plans/impact-review.md` に保存

## Validation

- `python3 -m unittest discover -s tools/impact-review -p 'test_*.py' -v`
- Makefile / リンク定義は変更しないため `make check` / `make status` は対象外

## Notes

- 導入 PR 自体は base 側 CLI を使うため自動レビューされない
- マージ後に Secrets / Variables を設定してから通常 PR で受け入れ確認する
