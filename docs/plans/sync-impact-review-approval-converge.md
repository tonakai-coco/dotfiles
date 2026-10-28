# Plan: Impact Review の approval / converge 同期

## Goal

`data-workflow-tools/tools/impact-review` の最新実装（approval / converge / 検証要求）を
`dotfiles/tools/impact-review` へ同期する。

## Scope

- `tools/impact-review/` をソースから同期（`__pycache__` 除外）
- 指摘方針 ADR を `docs/ADR/0004-impact-review-finding-policy.md` として追加
  （dotfiles 既存の 0001–0003 と番号衝突を避ける）
- README の ADR リンクを 0004 に合わせて修正
- `.github/workflows/impact-review.yml` のコメントを検証要求の説明に合わせて更新

## Out of Scope

- `.impact-review.yml` の上書き（dotfiles 固有の `docs/plans/**` ignore を維持）
- LLM 本体ロジックの独自改変
- Secrets / Variables の変更
- Makefile / リンク定義の変更

## Steps

1. `tools/impact-review/` を rsync で同期
2. ADR 0004 を追加し README リンクを更新
3. workflow コメントを同期
4. オフライン unittest を実行
5. 本計画を保存

## Validation

- `python3 -m unittest discover -s tools/impact-review -p 'test_*.py' -v`
- Makefile / リンク定義は変更しないため `make check` / `make status` は対象外

## Notes

- 対象 OS: 全 OS 共通のツール／CI（`tools/`・`.github/`）
- ソース側 ADR 番号 0001 は、dotfiles では 0004 に振り直す
