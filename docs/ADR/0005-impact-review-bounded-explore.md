# ADR 0005: 影響探索は bounded tool-use で行い、汎用コーディングエージェントは既定 CI に載せない

- ステータス: 採用（data-workflow-tools から同期。Phase A / B 実装済み。既定 CI への explore 有効化は未着手。[SPEC-explore](../../tools/impact-review/SPEC-explore.md)）
- 日付: 2026-10-29

## 文脈

Impact Review は Packer が diff・変更単位・caller 抜粋を静的に組み立て、OpenAI 互換 LLM へ 1 回のレビュー要求（必要時だけ検証要求）を送る。
caller はシンボルの単語一致検索であり、`related` は v0 で空である。
モデルは渡された pack の外を読めない。

「Claude Code / Codex / OpenCode などのコーディングエージェントを挟み、その場の判断で影響範囲を追加チェックする」案がある。
探索できる中間層を置く発想は、静的 pack の浅さを直接突いている。

一方で現行の制約は次のとおりである。

- PR のプログラム・ビルド・依存スクリプトを実行しない（[README](../../tools/impact-review/README.md)）
- 1 job は約 10 分、レビュー待ちの既定は 420 秒（[ADR 0004](0004-impact-review-finding-policy.md)）
- 残す指摘は今回導入の具体的不具合だけとし、検証・収束・座標検証で投稿を絞る（ADR 0004）
- 追加 SaaS・索引サーバー・埋め込み検索は使わない

汎用エージェントを既定の opened / synchronize 経路に載せると、実行境界・時間・出力ゲート・再現性・CLI 運用のすべてが現行方針と衝突しやすい。

## 決定

1. **欲しい能力は agent autonomy ではなく、影響グラフを追加で辿れることと定める。**
   既定 CI に Claude Code / Codex / OpenCode などの汎用コーディングエージェントを直載せしない。
2. **探索は読み取り専用の bounded tool-use ループで行う。**
   許可ツールは `read_path` / `search_symbol` / `grep` / `git_show`（および同等の Git object 読み）に限定する。
   write・exec・network・依存インストール・テスト実行は許可しない。
3. **予算を必須とする。**
   ツール呼び出し回数・追加文字数・壁時計の上限を設け、超過したら探索を打ち切り、その時点の文脈で構造化レビューへ進む。
4. **最終出力と投稿ゲートは現行を維持する。**
   レビュー結果は現行と同じ JSON finding schema とする。
   その後は既存の verify → converge → mapper → publish → approval をそのまま使う。
   探索を増やしても ADR 0004 の指摘方針は緩めない。
5. **導入は段階的にする。**
   - Phase A: Packer の `related` 充填と callers の静的強化（エージェントなし）
   - Phase B: bounded tool-use レビューア（opt-in。既定 CI は Phase B 安定後に検討）
   - Phase C: 外部コーディングエージェントは `workflow_dispatch` またはラベルによる非既定の深いレビューに限り、出力は現行 schema へ正規化してから Publisher へ渡す

詳細なツール契約・予算初期値・CLI・Phase A/B の受け入れ条件は [SPEC-explore](../../tools/impact-review/SPEC-explore.md) に書く。

## 採用しなかったこと

- **既定 CI への汎用コーディングエージェント直載せ。**
  シェル実行やテスト実行まで行きやすく、fork / 未信頼 PR と 10 分 job に合わない。
  エージェント CLI・認証・バージョン差分の運用コストも、OpenAI 互換 HTTP 1 本で切替できる現状の利点を失わせる。
- **自由形式のマルチエージェントオーケストレーションを先に作ること。**
  固定パイプライン（seed pack → explore → review → verify）で足りる。
  自由なフローは再現性と収束（再掲抑制）を壊しやすい。
- **探索拡大に合わせて nit / note や推測指摘を増やすこと。**
  Impact Review の差別化は広く指摘することではなく、導入欠陥の影響を根拠付きで突くことである。
- **PR コードのテスト実行をレビュー経路に含めること。**
  ADR 0004 と同様、未信頼コードを実行しない制約を維持する。別議論とする。

## 結果

静的 pack の浅さは Phase A で種を増やし、Phase B でモデル主導の追加読みを許す。
投稿品質の制御は既存ゲートに残る。
Phase B の実装前に SPEC-explore のツール契約と予算を実装・テストの受け入れ条件とする。
Phase C を始めるときは、この ADR を更新するか後継 ADR を追加する。
