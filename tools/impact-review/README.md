# Impact Review

PR の diff・変更単位・参照元抜粋を OpenAI 互換 LLM に渡し、要約とインライン指摘を投稿します。
追加 SaaS、索引サーバー、埋め込み検索は使いません。Python 3.10 以上が必要です。

このディレクトリは `data-workflow-tools` の Impact Review MVP を、本リポジトリ向けに導入したものです。

## 導入（このリポジトリ）

導入物は次の 3 点です。

| パス | 役割 |
|------|------|
| `tools/impact-review/` | Python CLI |
| `.github/workflows/impact-review.yml` | PR / 手動実行の workflow |
| `.impact-review.yml` | 対象パスと文字数などの設定 |

1. 上記を **base ブランチへマージ**する。workflow は base 側の CLI を実行するため、導入 PR 自体は自動レビューされない。
2. GitHub の Settings → Secrets and variables → Actions に下記を設定する。
3. Actions に `contents: read` と `pull-requests: write` を許可する。
4. 以降、通常 PR の opened / synchronize / reopened / ready_for_review で実行される。

| 名前 | 設定先 | 値 |
|------|--------|-----|
| `IMPACT_REVIEW_LLM_API_KEY` | Secret | 接続先の Bearer トークン |
| `IMPACT_REVIEW_LLM_BASE_URL` | Variable または Secret | `/v1` までの HTTPS URL。例: `https://api.ai.sakura.ad.jp/v1` |
| `IMPACT_REVIEW_LLM_MODEL` | Variable または Secret | 接続先で利用可能なモデル ID |
| `IMPACT_REVIEW_LLM_TIMEOUT_SECONDS` | Variable（任意） | LLM HTTP タイムアウト秒。既定 `420`、許容 `30`〜`480` |

URL・モデルは Variable を優先する。API キー・URL・モデルの 3 項目は必須。
既存の issue-auto-pr 用 `SAKURA_AI_*` とは別名なので、Impact Review 用に別途設定する。
接続先は `/chat/completions`、`messages`、`response_format: {type: json_object}` と
`choices[0].message.content` の JSON 文字列に対応している必要がある。

fork、draft、Bot 著者、対象ファイルがゼロの PR にはコメントを投稿せず、LLM も呼ばない。

## 設定

`.impact-review.yml` は **base 側**から読む。PR で変更した設定はマージ後に有効。

```yaml
paths:
  include: ["**"]
  ignore:
    - "docs/plans/**"
    - "generated/**"
limits:
  files: 30
  callers: 10
  max_chars: 80000
  must_important: 10
  nit: 5
  note: 3
```

本リポジトリでは実装計画 `docs/plans/**` と、サンプル互換の `generated/**` を ignore している。
ignore が include より優先する。バイナリ、主要 lock、vendor / node_modules / dist / build、
`.min.js` / `.map` / `.generated.*` / `.g.*` は標準除外。

## ローカル実行

信頼済み base ブランチの checkout で実行する。未信頼 PR の CLI を鍵付きで実行しない。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/impact-review/requirements.txt

# pack のみ（LLM・投稿なし）
.venv/bin/python tools/impact-review/cli.py \
  --repo OWNER/REPO --pr 123 --fetch --pack-only > /tmp/impact-pack.json

# LLM 結果のみ確認（投稿なし）
.venv/bin/python tools/impact-review/cli.py \
  --repo OWNER/REPO --pr 123 --fetch --dry-run

# オフラインテスト
.venv/bin/python -m unittest discover -s tools/impact-review -p 'test_*.py' -v
```

`--pack-only` は GitHub 読み取り API を使う。`--dry-run` は LLM 利用料が発生し得る。
実投稿は `--dry-run` を外す。PAT で投稿する場合は `IMPACT_REVIEW_BOT_LOGIN` に投稿者 login を指定する。
ローカルと Actions を同一 PR に並列投稿しない。

手動実行は Actions → Impact Review → Run workflow で PR 番号を指定する。

## 境界と注意

| 境界 | 実装 | 責務 |
|------|------|------|
| Event | `cli.py` | PR イベントまたは `--pr` から現在の PR を取得 |
| Gate | `core.py` | draft / Bot / fork / closed / 対象ゼロを無言で除外 |
| Packer | `packer.py` | merge-base からの diff、変更単位、caller 抜粋 |
| LlmClient | `client.py` | Bearer 認証で要求、JSON 応答を検証 |
| Mapper | `mapper.py` | path / line を検証 |
| Publisher | `publisher.py` | `COMMENT` Review の投稿と旧指摘の置換 |

- Review は常に `COMMENT`。`REQUEST_CHANGES` や必須チェック登録はしない。
- job は `continue-on-error: true`。ブランチ保護の required check に登録しないこと。
- ログに API レスポンス本文・キーは出さない。
