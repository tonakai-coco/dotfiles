# Impact Review: 影響探索（Phase A / B）仕様草案

- ステータス: Phase A / B 実装済み（方針は [ADR 0005](../../docs/ADR/0005-impact-review-bounded-explore.md)）。既定 CI への `--explore` 有効化は未着手
- 日付: 2026-10-29
- 対象: [packer.py](packer.py) / [explore.py](explore.py) / [client.py](client.py) / [cli.py](cli.py) の拡張。Publisher 以降のゲートは変更しない

この文書は実装契約である。
コードを変えるときは本 SPEC と ADR 0004 / 0005 を同時に満たすこと。

## 目的

静的に切り出した pack だけでは、モデルが「追加で見るべき参照」に気づけても辿れない。
目的は指摘を増やすことではない。
**導入欠陥の影響を、根拠のある追加文脈で突けるようにすること**である。

## 共通制約（全 Phase）

- Git object の読み取りのみ。PR コード・ビルド・依存インストール・テストを実行しない
- 追加 SaaS・永続索引・埋め込み検索を導入しない（必要ならその場の `git grep` / AST）
- 最終 findings は現行 JSON schema（severity / origin / evidence / path / line / …）
- verify → converge → mapper → publish → approval の順序と ADR 0004 の残存条件は維持する
- pack の保持優先度は現行どおり **変更単位 → callers → related → diff**（低優先の末尾から削る）

---

## Phase A: Packer の静的強化

エージェントも tool-use も使わない。
[Packer.build](packer.py) が返す seed pack の種を厚くする。

### A1. `related` を空配列のままにしない

`related` は「変更単位でも caller 抜粋でもないが、影響判断の種になる抜粋」である。
各要素の形は callers に揃え、次を最低限含める。

```json
{"path": "relative/path.py", "start": 1, "text": "...", "reason": "import_target|sibling_test|same_dir_config"}
```

**収集ルール（優先順、重複 path は先勝ち）**

1. **import_target（Python 変更単位があるとき）**  
   RIGHT 側変更単位のソースを AST で読み、同一リポジトリ内に解決できる `import` / `from … import` 先モジュールのファイルを最大 5 件。
   解決できない相対・外部パッケージは捨てる。
   各ファイルは先頭またはシンボル定義付近から最大 40 行。
2. **sibling_test**  
   変更 path `foo/bar.py` に対し、既存の慣例で存在するテスト候補を head 上で確認する。  
   例: `foo/test_bar.py`, `foo/tests/test_bar.py`, `tests/foo/test_bar.py`, `foo/bar_test.py`。  
   存在するものだけを最大 3 件。全文は入れず、変更シンボル名が含まれる箇所の前後 40 行を優先。無ければファイル先頭 40 行。
3. **same_dir_config**  
   変更ファイルと同じディレクトリにある設定・契約っぽい名前（`*.yml` / `*.yaml` / `*.toml` / `*.json` / `*.ini`、ただし lock と DEFAULT_IGNORE 除外）を最大 2 件、先頭 40 行。

上限: `related` は最大 **8 抜粋**（設定キー `limits.related`、既定 8、安全上限 30）。
文字数は既存の `max_chars` 切り詰めに委譲する。
取れなければ空配列のままでよく、その旨を `limitations` に出さない（欠落は正常）。

### A2. callers の偽陽性を減らす

現行の `git grep -F -w` 単語一致は残してよいが、次のフィルタを追加する。

1. **変更単位 path のモジュール修飾を優先**  
   例: `packer.py` の `Packer` に対し、`Packer(` / `packer.Packer` / `from packer import Packer` に近い行を先に残す。
   単純な単語 `Packer` のみの一致は後段にする。
2. **Python ファイルでは定義行を除外**  
   AST 上 `FunctionDef` / `AsyncFunctionDef` / `ClassDef` / 代入の定義行と一致するヒットは caller にしない（現行の「変更単位内除外」の拡張）。
3. **同一 path の近傍重複**  
   現行の 20 行近傍スキップは維持する。

`limits.callers` の意味（最大件数）は変えない。
フィルタ強化で件数が減るのは許容する。

### A3. 設定

`.impact-review.yml` の `limits` に次を追加する（未知キー拒否の現行パーサを更新）。

| キー | 既定 | 安全上限 | 意味 |
|---|---|---|---|
| `related` | 8 | 30 | related 抜粋の最大件数 |

`paths` は変更しない。ignore は related / callers の両方に効く。

### A4. Phase A の受け入れ

1. Python の import 先が同一 repo にあれば `related` に `reason=import_target` が入る
2. 対になるテストファイルがあれば `sibling_test` が入る
3. `--pack-only` で related が観察でき、`max_chars` 超過時は related が callers より先に削られる（優先度維持）
4. callers からクラス／関数の定義行が除外されるオフラインテストがある
5. 既存 unittest がすべて通る

### A5. Phase A の非目標

- 言語横断の完全な参照解析
- LSP / 索引サーバー
- LLM 呼び出し回数の変更

---

## Phase B: bounded tool-use レビューア（最小プロトタイプ）

### B1. 位置づけ

Phase A の seed pack を渡したあと、モデルが読み取り専用ツールを予算内で呼び、追加文脈を得てから現行 schema のレビュー JSON を返す。
**既定の GitHub Actions 経路ではまだ有効にしない。**
ローカルと明示フラグでのみ動かす最小プロトタイプとする。

### B2. CLI

[cli.py](cli.py) に次を追加する。

| フラグ | 既定 | 意味 |
|---|---|---|
| `--explore` | off | tool-use 探索ループを有効化 |
| `--explore-max-calls` | 8 | ツール呼び出しの最大回数 |
| `--explore-max-chars` | 40000 | ツール結果として追加してよい文字数合計 |
| `--explore-timeout-seconds` | 120 | 探索ループ全体の壁時計上限 |

既存フラグとの関係:

- `--pack-only`: 探索しない（従来どおり pack のみ）。`--explore` と同時指定ならエラー
- `--dry-run`: 探索＋レビュー＋検証まで行い、GitHub へは投稿しない（従来どおり）
- フラグなし: 現行の一発レビュー（探索なし）。CI workflow は当面フラグなしのまま

環境変数（Actions 将来用、プロトタイプでは任意）:

- `IMPACT_REVIEW_EXPLORE=1`
- `IMPACT_REVIEW_EXPLORE_MAX_CALLS`
- `IMPACT_REVIEW_EXPLORE_MAX_CHARS`
- `IMPACT_REVIEW_EXPLORE_TIMEOUT_SECONDS`

CLI フラグが環境変数より優先する。

### B3. 許可ツール

すべて repository-relative path。`Config.accepts` と DEFAULT_IGNORE を通さない path は拒否し、モデルには短いエラー文字列だけ返す（存在の有無を過剰に漏らさない）。

| 名前 | 引数 | 振る舞い |
|---|---|---|
| `read_path` | `path`, `start_line?`, `max_lines?`（既定 40、上限 80） | head の blob から行抜粋 |
| `search_symbol` | `symbol`, `max_hits?`（既定 10、上限 20） | head 上の単語境界検索。hit ごとに path / line / 前後最大 20 行 |
| `grep` | `pattern`, `max_hits?`（既定 10、上限 20） | 固定文字列検索（`git grep -F`）。正規表現は初版では載せない |
| `git_show` | `path`, `ref?`（`base` / `head` のみ、既定 `head`） | 指定側 blob の先頭または指定範囲。1 MB 超・非 UTF-8 は拒否 |

禁止（実装しても呼んでよいとモデルに示さない）:

- 任意シェル、`pip` / `npm`、テストランナー
- ワークツリーへの書き込み
- ネットワーク
- `ref` に任意 SHA やブランチ名（base/head 以外）

ツール実行器は Packer と同様 `git` サブプロセスのみを使い、PR ツリーを `import` しない。

### B4. ループ契約

```text
seed pack
  → (assistant tool_calls | final JSON review)
      → ツール実行（予算消費）
      → 結果を messages に追加
  → 予算切れ or 最終 JSON
  → 既存 LlmClient.verify（未確定 findings があるときだけ）
  → converge → mapper → publish / dry-run
```

- API は OpenAI 互換の `tools` / `tool_calls` を使う。接続先が tools 非対応なら `--explore` は明示エラーで終了し、黙って一発レビューへフォールバックしない
- 最終メッセージは現行 `REVIEW_SYSTEM` 相当の JSON object のみ（tool_calls なし）
- 探索中の中間自然言語は findings に載せない
- 予算切れ時はその時点で「これ以上の tool_calls 禁止、JSON のみ」と指示してもう 1 回だけ完了要求する。それでも JSON でなければ現行どおり診断エラー
- `limitations` に `explore_calls: N`, `explore_chars: M`, `explore_budget_exhausted`（該当時）を残す

### B5. 予算の初期値と CI 余裕

| 予算 | 初期値 | ハード上限 |
|---|---|---|
| max calls | 8 | 20 |
| max chars | 40_000 | 100_000 |
| wall clock | 120s | 300s |

レビュー本体の HTTP timeout（既定 420s）とは別計量である。
探索 timeout は「ツール実行＋追加 completion の合計壁時計」とする。
将来 CI で有効化するときは、job `timeout-minutes: 10` 内に explore + review + verify が収まる組み合わせだけを許す。

### B6. Finding policy

探索で得た caller / 設定 / テストを根拠にしてもよいが、残す条件は ADR 0004 のままである。

- `origin` は `introduced` のみ投稿対象
- `evidence` は **変更行** からの 8 文字以上の引用（探索で読んだだけの行では不可）
- 検証要求は「今回の変更で入った具体的不具合か」を判定する。探索文脈は参考であり、検証を緩くしない

### B7. Phase B プロトタイプの受け入れ

1. `--explore --dry-run` で tool_calls が予算内に収まり、最終 JSON が現行 schema でパースできる
2. 許可外 path / 禁止ツール相当の要求が拒否される unittest がある
3. max_calls=0 相当または即座の予算切れで、追加読みなしでもレビュー JSON に到達するか明示エラーになる（無限待ちしない）
4. `--pack-only --explore` がエラーになる
5. フラグなし実行の経路・テストが Phase A 以前と互換である
6. workflow YAML はまだ `--explore` を付けない

### B8. Phase B の非目標

- Actions 既定経路での有効化
- 複数エージェントの役割分担
- 外部 CLI（Claude Code / Codex / OpenCode）の呼び出し
- tools 非対応エンドポイントへのサイレントフォールバック

---

## Phase C（この SPEC の範囲外のメモ）

ADR 0005 のとおり、外部コーディングエージェントは非既定の深いレビューに限る。
出力は必ず現行 schema へ正規化してから Publisher へ渡す。
本 SPEC の実装対象外とし、着手時に後継文書を書く。

## 実装順序

1. Phase A（`related` + callers フィルタ + 設定 + テスト）
2. Phase B（ツール実行器 → explore ループ → CLI フラグ → dry-run 受け入れ）
3. 実 PR で `--explore --dry-run` の質を見てから、CI opt-in（ラベルまたは repository variable）を別 PR で検討する
