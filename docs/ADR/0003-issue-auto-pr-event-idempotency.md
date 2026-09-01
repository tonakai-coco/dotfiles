# ADR-0003: Issue自動PRのイベント単一化と冪等性

- ステータス: Accepted（採用）
- 決定日: 2026-08-29
- 対象: GitHub ActionsによるIssue起点の自動Pull Request
- 関連: [ADR-0002](0002-issue-auto-pr-preflight-estimate.md)

## 背景

Issueに`auto-pr`ラベルを付けて作成したとき、GitHub Actionsの`opened`と`labeled`の両方が発火し、同じIssueに対する自動PR処理が2回実行されることがある。

Issue #31では、2つのrunがそれぞれ事前見積もり、完全ファイル生成、検証、dry-runコメント投稿まで実行した。`concurrency`で同じIssueのrunを同時実行しない設定にしていても、後続runをキャンセルしない設定では重複処理を防げない。

dry-runではbranchやPull Requestが作成されないため、既存branch／Pull Requestの確認だけでは、後続runが「処理済み」と判断できない。

## 決定

### イベントを`labeled`に限定する

Issue自動PRのworkflowは、次のイベントだけを購読する。

```yaml
on:
  issues:
    types: [labeled]
```

ジョブ条件でも、イベントのラベル名が`auto-pr`であることを確認する。

`auto-pr`ラベルの追加を自動PR開始の明示的な操作と扱う。Issue作成時にラベルを同時指定した場合も、GitHubが記録する`labeled`イベントを開始条件とする。Issue作成だけでは自動PRを開始しない。

### 同一要求をリクエストキーで識別する

入力検証Jobは、次の値を固定順序のJSONにしてSHA-256ハッシュを作成する。

- リポジトリ名
- Issue番号
- default branch
- Issueタイトル
- Issue本文
- 対象パス一覧
- 生成基準コミットSHA

この値をリクエストキーとする。Issue本文、対象パス、または基準コミットが変われば別の要求として扱う。

### 生成前に完了済み要求を確認する

完全ファイル生成や事前見積もりの前に、対象Issueのコメントを読み取り、次の条件を満たすコメントがあるか確認する。

- GitHub Actions Bot（`github-actions[bot]`）が投稿している
- 現在のリクエストキーを含む隠しマーカーがある

一致するコメントがある場合は、入力検証Jobを`skipped`として成功終了する。後続のAI呼び出し、Artifact生成、検証、branch作成、commit、push、Pull Request作成、重複通知は行わない。

### 完了マーカーを付けるコメントを限定する

次の完了系コメントにだけリクエストキーを含む隠しマーカーを付ける。

- `preflight-too-large`
- `preflight-review-required`
- `change-too-large`
- `dry-run`
- `published`
- `no-change`

AI失敗、見積もり失敗、検証失敗、公開失敗、入力不備などの失敗コメントには完了マーカーを付けない。外部サービスや一時的な環境の失敗は、ラベルを付け直して再試行できるようにする。

利用者が投稿したコメントに同じ文字列が含まれていても処理済みとは扱わない。Botの投稿者を確認し、利用者によるマーカー偽装で自動処理を停止できないようにする。

### 同時実行制御を維持する

同じIssueのworkflow runは引き続きIssue番号単位で直列化し、`cancel-in-progress: false`を維持する。

先行runが処理中の場合は後続runを待機させ、先行runが完了系コメントを投稿した後に後続runの生成前ガードが処理済みと判断する。先行runが失敗した場合は完了マーカーがないため、後続runによる再試行を許可する。

## 検討した代替案

### `opened`だけを購読する

採用しない。

Issue作成後に利用者が`auto-pr`ラベルを追加する通常の運用を取りこぼすためである。

### `opened`と`labeled`を維持し、concurrencyだけで抑止する

採用しない。

`cancel-in-progress: true`にしても先行runをキャンセルして後続runが実行される可能性があり、生成後に先行runが完了してから次のrunが開始される場合の重複も防げない。

### Issue番号だけで処理済みと判定する

採用しない。

Issue本文を修正して再依頼した場合や、基準コミットが変わった場合まで同一要求として扱うためである。

### 利用者コメントを含む任意のマーカーを信頼する

採用しない。

Issue参加者がマーカーを含むコメントを投稿するだけで自動PRを停止できるため、GitHub Actions Botの投稿に限定する。

## 影響

同じIssue作成操作による`opened`／`labeled`の二重実行を防ぎ、Sakura AIの事前見積もりと完全ファイル生成、検証、dry-runコメントが重複しなくなる。

生成前にIssueコメントを1回読み取るため、GitHub API呼び出しは増える。ただし、重複時には完全生成を省略できるため、AIトークンとRunner時間を節約できる。

同じIssue本文、対象パス、基準コミットで完了処理した要求を再実行したい場合は、同じIssueへのラベル再追加ではなく、目的と受入条件を整理した新しいIssueを作成する。実際のPull Requestやbranchが存在する場合は、従来の既存作業検出も引き続き適用する。

旧仕様の手順書である`GITHUB_ACTIONS_HANDOFF.md`は変更しない。

## 再評価条件

次の条件でイベント条件または冪等性方式を見直す。

- GitHub ActionsのIssueイベント仕様が変わった場合。
- 完了マーカーによる再試行制御が運用上の障害になった場合。
- コメント数が増え、現在のページング上限では処理済み要求を確認できなくなった場合。
- 同じ要求を安全に再実行するためのworkflow dispatchや専用状態管理を導入する場合。

## 関連ファイル

- [`.github/workflows/auto-pr.yml`](../../.github/workflows/auto-pr.yml)
- [`.github/scripts/auto-pr-common.mjs`](../../.github/scripts/auto-pr-common.mjs)
- [`.github/scripts/auto-pr-input.mjs`](../../.github/scripts/auto-pr-input.mjs)
- [`.github/scripts/auto-pr-publish.mjs`](../../.github/scripts/auto-pr-publish.mjs)
- [`.github/scripts/auto-pr.test.mjs`](../../.github/scripts/auto-pr.test.mjs)
