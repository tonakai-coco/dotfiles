# Impact Review MVP

PR の diff、変更単位、参照元の抜粋を OpenAI 互換 LLM に渡し、要約とインライン指摘を投稿します。
追加 SaaS、索引サーバー、埋め込み検索は使用しません。Python 3.10 以上が必要です。
何を残し、何を見送ったかは [ADR 0004](../../docs/ADR/0004-impact-review-finding-policy.md) に記録しています。

## 導入

1. `.github/workflows/impact-review.yml`、`.impact-review.yml`、`tools/impact-review/` を対象リポジトリの **base ブランチへ導入**します。
   workflow は base 側の CLI を実行するため、導入 PR 自体は自動レビューできません。手動実行は default ブランチに登録された workflow から、指定 PR の base SHA を取得してその CLI と設定を読み込みます。
2. GitHub の Settings → Secrets and variables → Actions に下記を設定します。
3. Actions に `contents: read` と `pull-requests: write` を許可します。組織ポリシーが書き込みを制限している場合は管理者側で設定します。
4. 同一リポジトリ内の通常 PR を作成します。以後、opened / synchronize / reopened / ready_for_review で実行します。

| 名前 | 設定先 | 値 |
|---|---|---|
| `IMPACT_REVIEW_LLM_API_KEY` | Secret | 接続先の Bearer トークン |
| `IMPACT_REVIEW_LLM_BASE_URL` | Variable または Secret | `/v1` までの HTTPS URL。例: `https://api.ai.sakura.ad.jp/v1` |
| `IMPACT_REVIEW_LLM_MODEL` | Variable または Secret | 接続先で利用可能なモデル ID |
| `IMPACT_REVIEW_LLM_TIMEOUT_SECONDS` | Variable（任意） | LLM HTTP タイムアウト秒。既定 `420`、許容 `30`〜`480`（job `timeout-minutes: 10` 内の余裕分） |

URL・モデルは Variable を優先します。URL の暗黙のデフォルトはなく、API キー・URL・モデルの 3 項目は必須です。
さくらの AI Engine は初期接続例です。別の OpenAI 互換サービスへは環境変数だけで切り替えられます。
接続先は `/chat/completions`、`messages`、`response_format: {type: json_object}` と
`choices[0].message.content` の JSON 文字列に対応している必要があります。実モデルの接続確認は導入先で行ってください。
GitHub 用には自動発行の `github.token` を使用します。GitHub API のタイムアウトは 90 秒のままです。

PR の内容は設定した LLM 接続先へ送られます。送信対象外のパスは `paths.ignore` に設定してください。
fork、draft、Bot 著者、対象ファイルがゼロの PR にはコメントを投稿せず、LLM も呼びません。

## 設定

`.impact-review.yml` は **base 側**から読みます。PR で変更した設定はマージ後に有効です。
URL・モデル・鍵を含む未知のキーは受け付けません。

```yaml
paths:
  include: ["**"]
  ignore: ["generated/**", "private/**"]
limits:
  files: 30
  callers: 10
  max_chars: 80000
  must_important: 10
  nit: 5
  note: 3
```

パターンは Python `fnmatchcase` 相当で大文字小文字を区別し、リポジトリ相対パスとそのディレクトリ以下に適用します。
`*.py` は配下の Python ファイルにも、`private/**` は配下の private ディレクトリにも一致します。
ignore が include より優先します。バイナリ、主要 lock ファイル、vendor / node_modules / dist / build、
`.min.js` / `.map` / `.generated.*` / `.g.*` は標準除外です。固有の生成物は ignore に追加します。

files / callers / max_chars は変更可能です（安全上限: 300 / 100 / 500,000、max_chars の下限: 2,000）。
重大度の上限は仕様の 10 / 5 / 3 まで下げられます。must を important より優先して残します。
80,000 文字はトークン数ではありません。モデルのコンテキスト容量に応じ、応答用の余裕を含めて下げてください。

## 境界と処理

| 境界 | 実装 | 責務 |
|---|---|---|
| Event | `cli.py` | PR イベントまたは `--pr` から現在の PR を取得 |
| Gate | `core.py` | draft / Bot / fork / closed / 対象ゼロを無言で除外 |
| Packer | `packer.py` | merge-base からの diff、変更単位、caller 抜粋、rubric、文字数制御 |
| LlmClient | `client.py` | レビュー要求のあと、未確定の指摘があるときだけ検証要求を行う。タイムアウトと HTTP エラーは再試行しない。応答完了前の接続断だけ、その要求をもう 1 回 |
| Converge | `converge.py` | 今回の変更で入った不具合以外、再掲、4回目以降の細かい指摘を捨てる |
| Mapper | `mapper.py` | ローカル差分と GitHub 提供差分の両方で path / line を検証 |
| Publisher | `publisher.py` | `COMMENT` Review の body と inline を投稿、旧指摘を置換 |
| Approval | `approval.py` | 人の承認が必要かを別の Issue コメントで示す。マージは止めない |

Python の関数・クラスは AST で全文を取得します。削除された単位は LEFT として収録します。
それ以外の言語や構文解析できない部分は変更行前後の最大約 40 行を取得し、`complete: false` と明記します。
一部の宣言名も簡易抽出します。caller は抽出シンボルの単語一致検索で、実際の呼び出しである保証はありません。
変更単位内の一致は除外し、最大 10 抜粋・各最大 40 行に制限します。1 MB 超の blob と非 UTF-8 は全文取得しません。
`related` は v0 では空です。保持優先度は **変更単位 → callers → related → diff** とし、低優先度の末尾から削ります。
省略は pack と Review の制限欄へ残します。

LLM の行番号は RIGHT 側として扱います。削除側、diff 外の caller、パス不一致、行番号不正、GitHub 側 patch 欠落は
`summary_only` として本文へ残します。座標が合っていても、指摘内容が正しいことにはなりません。
🔴 [MUST] / 🟠 [IMPORTANT] / 🟢 [NIT] / ⚪ [NOTE] は本文一覧とインラインの両方に付きます。

残す指摘は、次をすべて満たすものだけです。

- モデルが `origin: introduced` とし、追加行または削除行から 8 文字以上の引用を付けている。変更されていない文脈行やファイル全体の一致では残しません。
- 検証要求が「今回の変更で入った具体的な不具合」と判定している。残す判定は、理由が短くても投稿します。スタイル、命名、整形、コメント、片付け、診断、既存の挙動、推測は捨てます。
- 前回の別 head で出した指摘と、同じパス・重大度・題名、または同じパス・行・重大度ではない。2 回目以降の nit / note は、前回の指摘から 3 行以内のものと、前回 head から今の head への直接の差分に含まれない行のものを捨てます。差分が取れないときも nit / note は残しません。
- 4 回目以降は、その直接の差分にある must と important だけを残します。行番号がない指摘は残しません。差分が取れないときは、新しい行だと示せない must / important も残しません。同じ種類の指摘が続く場合は、実装方針の見直しを制限欄に書きます。同じ head の再実行はラウンドを増やさず、これらの抑制を行いません。

検証要求が失敗したときは、nit と note を捨て、引用の付いた must と important だけを残して `verification_failed` を制限欄に書きます。このとき残した指摘は、検証を通過していないので確定しません。指摘が残らなければ、要約は「今回の変更で入った不具合は残っていません。」に置き、質問は空にします。

人の承認判定はレビューとは別のコメントです。コード、must、important、残った nit と note、ワークフロー、認証、秘密情報、差分の切り詰め、検証失敗、前回差分の取得失敗がある変更は「必要」です。秘密情報のパスは大文字小文字を区別しません。ルートの `auth.py` や `auth/` 配下も認証パスとして扱います。文書・画像だけで、残った指摘も被覆の欠けもない変更は「不要」です。このコメントはマージを止めません。

## 再実行と失敗時

- 同じ PR の workflow を concurrency group で直列化します。LLM 実行中の head / base 更新・draft 化・close は投稿直前に再確認します。
- 同じ head・本文・inline の結果は再利用し、新しい Review を作りません。同じ head・同じ指摘位置なら、
  LLM の文言が変わっても本文とインラインをその場で更新します。head または指摘位置が変われば置換します。
- 新しい Review の投稿成功後、マーカーと投稿者の一致する旧レビューの bot コメントを削除し、旧本文を最新版へのリンクに置換します。
  GitHub の制約で投稿済み Review の履歴枠は残ります。通常は詳細本文と bot インラインは最新版 1 組です。
- cleanup が途中で失敗した場合、次の同一結果の実行は新規投稿せず cleanup を再開できます。人間や他ツールの Review は変更しません。
- レビュー要求と検証要求は、それぞれ、不正 JSON の内容抽出に失敗したときと、応答完了前に接続が切れたとき（`RemoteDisconnected` など）だけ、同じプロセスでもう 1 回です。タイムアウトと HTTP エラーは再試行しません。レビューの待ち時間の既定は 420 秒、検証は最大 90 秒です。workflow は CLI を 1 回だけ実行します。接続断の再試行が job の 10 分を超えると、その実行は打ち切られます。検証要求の失敗では指摘を絞って投稿を続けます。
  LLM・新規投稿失敗時は既存レビューを維持します。既存コメント更新の途中で失敗すると部分更新が残る場合があります。
  GitHub 投稿成功後の cleanup 失敗では一時的に旧指摘が残ることがあります。
- Review は常に `COMMENT` です。`REQUEST_CHANGES`、Check 作成、必須チェック登録はしません。
  job は `continue-on-error: true`。**Impact Review をブランチ保護の required check に登録しないでください。**
  既存のブランチ保護ルールをこのツールが変更することはありません。
- ログに API レスポンス本文・キーは出しません。切り分け用に次だけ区別します。
  - `ResponseJsonError`: HTTP 成功応答の body が JSON でない（status / bytes / `{` 開始の有無）
  - `LlmContentJsonError`: `message.content` が JSON でない（型 / 文字数 / finish_reason / `{` 開始の有無）
  - `TimeoutError`: LLM（または指定 timeout）の待ち時間超過
  - `ApiError`: HTTP 4xx/5xx
  - `ApiConnectionError`: 応答完了前の接続断。詳細（URL や原因文字列）は出さない
  CLI は失敗を終了コード 1 で通知し、workflow が非ブロック扱いにします。

PR のプログラム・ビルド・依存スクリプトは実行しません。base 側の CLI から Git オブジェクトとして読みます。
手動実行は Actions → Impact Review → Run workflow で PR 番号を指定します。

## ローカル実行

信頼済み base ブランチの checkout で実行してください。未信頼 PR の CLI を鍵付きで実行しないでください。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/impact-review/requirements.txt

# GitHub 読み取り用トークンを環境変数 GITHUB_TOKEN に設定済みとする。
# --fetch は origin から base/head を取得するため、Git の認証も必要です。
# LLM 呼び出し・GitHub 書き込みなしで pack を確認
.venv/bin/python tools/impact-review/cli.py \
  --repo OWNER/REPO --pr 123 --fetch --pack-only > /tmp/impact-pack.json

# 3 つの IMPACT_REVIEW_LLM_* 環境変数を設定して、投稿せず LLM 結果を確認
.venv/bin/python tools/impact-review/cli.py \
  --repo OWNER/REPO --pr 123 --fetch --dry-run

# オフラインの受け入れテスト（API・LLM 通信なし）
.venv/bin/python -m unittest discover -s tools/impact-review -p 'test_*.py' -v
```

`--pack-only` は GitHub 読み取り API を使用します。`--dry-run` は LLM 利用料が発生し得ます。
Git の取得が不要なら `--fetch` を省略できます。`--root` で Git リポジトリ、`--config` で信頼済み設定ファイルを指定できます。
実投稿は `--dry-run` を外します。PAT で投稿する場合は `IMPACT_REVIEW_BOT_LOGIN` にその投稿者の login を指定し、
PR 書き込み権限を付けてください。ローカルと Actions を同一 PR に並列投稿しないでください。

## 受け入れ確認（導入先で実行）

1. base 導入・環境変数設定後、通常 PR の作成と追加 push で Review が付くことを確認。
2. 変更行の問題を含め、検証済み指摘がインラインになることを確認。決定的な座標検証はオフラインテストで確認。
3. diff 外・不正座標が `summary_only` に残ることを Mapper テストで確認。
4. 4 種類の目印が本文・インラインにあることをテストと実 PR で確認。
5. 同一結果再実行で Review が増えず、追加 push 後は旧指摘が最新版へ置換されることを確認。履歴枠は残る。
6. draft / Bot / ignore のみ / fork でコメントが付かないことを確認。
7. URL・model を別の互換接続先へ切り替え、コード変更なしで動くことを確認。
8. テストまたは接続先の利用履歴で、成功時のレビュー要求が 1 回であることを確認。未確定の指摘が残るときだけ検証要求がもう 1 回ある。不正 JSON と応答完了前の接続断だけ、その要求をもう 1 回行う。
9. 無効なモデルなどで失敗させ、required check 未登録の状態で merge を妨げないことを確認。
10. 上記モジュール表と `cli.main()` の呼び出し順を確認。

GitHub API の仕様: [Review 作成・更新・削除制限](https://docs.github.com/en/rest/pulls/reviews)、
[インラインの行と side](https://docs.github.com/en/rest/pulls/comments)。
