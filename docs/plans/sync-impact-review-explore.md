# Plan: Impact Review の bounded explore 同期

## Goal

`data-workflow-tools/tools/impact-review` の Phase A/B（`related` 強化と `--explore`）を
`dotfiles/tools/impact-review` へ同期する。

## Scope

- `tools/impact-review/` をソースから同期（`__pycache__` 除外）
- 影響探索 ADR を `docs/ADR/0005-impact-review-bounded-explore.md` として追加
  （dotfiles 既存の 0001–0004 と番号衝突を避ける）
- README / SPEC-explore の ADR リンクを 0004 / 0005 に合わせて修正

## Out of Scope

- 既定 CI（`.github/workflows/impact-review.yml`）への `--explore` 有効化
- `.impact-review.yml` の上書き
- LLM 本体ロジックの独自改変
- Secrets / Variables の変更
- Makefile / リンク定義の変更

## Steps

1. 差分ファイルをソースから `tools/impact-review/` へコピー
2. ADR 0005 を追加し README / SPEC-explore リンクを更新
3. オフライン unittest を実行
4. 本計画を保存

## Validation

- `uv run --with PyYAML==6.0.2 python -m unittest discover -s tools/impact-review -v`
  → 73 tests OK
- Makefile / リンク定義は変更しないため `make check` / `make status` は対象外

## Notes

- 対象 OS: 全 OS 共通のツール／CI（`tools/`・`docs/`）
- ソース側 ADR 番号 0001 / 0002 は、dotfiles では 0004 / 0005 に振り直す
