# ADR-0002: Issue自動PRの事前変更量見積もりゲート

- ステータス: Accepted（採用）
- 決定日: 2026-08-29
- 対象: GitHub ActionsによるIssue起点の自動Pull Request
- 置き換えるADR: [ADR-0001](0001-issue-auto-pr-change-size-policy.md)

## 背景

ADR-0001では、AIが完全なファイル内容を生成してからGit差分を測定し、変更量が大きい場合に処理を停止していた。

この方式では、分割依頼になる変更でも完全な生成結果を作るため、生成トークンとSakura AI Engineのリクエストを消費する。

対象パスの最大3件制限はすでに撤廃している。対象パスの件数ではなく、変更の大きさを生成前に評価して、明らかに大きい依頼を早期に分割へ戻したい。

## 決定

### 処理段階

Issue入力の検証後、完全なファイル生成の前に、軽量な事前見積もりを1回実行する。

事前見積もりは、Issueのタイトルと本文、対象ファイルのサイズを制限したプレビューだけを入力として、次のJSON形式を返す。

```json
{
  "summary": "変更内容の短い要約",
  "planStatus": "change-needed",
  "confidence": "high",
  "plannedChanges": [
    {
      "path": "config/example.conf",
      "reason": "設定値を追加する",
      "estimatedChangedLinesMax": 80
    }
  ]
}
```

事前見積もりの応答には、ソースコード、完全なファイル内容、パッチ、差分を含めない。

`planStatus`は、`change-needed`、`no-change`、`insufficient-instructions`のいずれかとする。`change-needed`の場合は変更が必要なパスを`plannedChanges`に含める。`no-change`の場合は対象パスがすでに要件を満たしているため、`plannedChanges`を空にする。`insufficient-instructions`の場合はIssue本文から具体的な変更内容を判断できないため、`plannedChanges`を空にする。この状態は変更計画として採用せず、Issueへ具体的な変更内容と受入条件の追記を依頼する。

`estimatedChangedLinesMax`は各ファイルの変更行数の保守的な上限とし、正確な人手工数を表す値とは扱わない。

事前見積もりの判定は次のとおりとする。

| 判定 | 条件 | 処理 |
| --- | --- | --- |
| 生成可 | `planStatus`が`change-needed`、分割条件に該当せず、見積もり確度が低ではない | 完全なファイル生成へ進む |
| 変更不要 | `planStatus`が`no-change` | 完全なファイル生成を行わず、変更不要としてIssueへ通知する |
| 分割依頼 | `planStatus`が`change-needed`で、分割閾値以上の見積もりが1つでもある | 完全なファイル生成を行わず、Issueへ分割を依頼する |
| 人手確認 | `planStatus`が`change-needed`で、見積もり確度が低である | 完全なファイル生成を行わず、人手確認を依頼する |
| 指示不足 | `planStatus`が`insufficient-instructions` | 完全なファイル生成を行わず、Issueへ具体的な変更内容の追記を依頼する |

分割依頼、人手確認、変更不要、指示不足になった場合、完全なファイル生成、`make`検証、branch作成、commit、push、Pull Request作成を行わない。

分割閾値には達しないものの要確認の目安に達した場合は、`見積もり規模: 要確認`として記録する。これは情報提供であり、見積もり確度が低くない限り完全なファイル生成へ進む。

### 変更量の指標と閾値

事前見積もりでは、計画に含まれるファイルの最大変更行数を合計し、対象ファイル数、変更領域数、1ファイルの最大変更行数を加えて評価する。

変更領域は、ADR-0001と同じく対象パスの先頭2階層で数える。リポジトリ直下のファイルは`<root>`とする。

次の閾値は、40時間を直接測定するものではなく、1週間を超える可能性がある変更を早期に人へ戻すための初期予算である。

| 指標 | 要確認の目安 | 分割依頼の閾値 |
| --- | ---: | ---: |
| 変更行数 | 400行以上 | 800行以上 |
| 変更ファイル数 | 5件以上 | 10件以上 |
| 変更領域数 | 2領域以上 | 3領域以上 |
| 1ファイルの変更行数 | 判定に使用しない | 400行以上 |

事前見積もりは境界値を含めて判定する。これは、生成前の不確実性を吸収するためである。

見積もりスコアは次の最大値とする。

```text
max(
  変更行数 / 800,
  変更ファイル数 / 10,
  変更領域数 / 3,
  1ファイルの最大変更行数 / 400
)
```

スコアは比較用の補助値であり、分割判定は各閾値の超過を根拠として記録する。

### 生成後の実測

事前見積もりは早期停止のためのゲートであり、最終判定ではない。

事前見積もりを通過した後も、完全なファイル内容を一時適用してGit差分を測定する。実測値は事前見積もりより優先し、ADR-0001で定めた変更量判定を最終的な安全弁として維持する。

したがって、見積もりが小さくても実測差分が大きい場合は公開せず、見積もりが大きくても実測差分を理由に自動で小さくなったとは判断しない。

生成、検証、公開の各Jobでdefault branchを再解決しないよう、入力検証時のHEADを`baseCommitSha`として入力文書とartifactへ記録する。検証と公開はartifactの`baseCommitSha`をcheckoutし、別のHEADで作られた成果物を適用しない。

artifact適用前に、固定したbase commitからPublisherと変更対象別検証処理をrunnerの一時領域へコピーする。artifact適用後はworkspace上の`.github/scripts/auto-pr-publish.mjs`や共通処理を実行せず、固定コピーだけを実行する。

変更されたパスに応じて、`docs/agent-guides/validation.md`に定義されたformatter、health check、構文確認、設定再読み込みを選択して実行する。GUIを起動できないWezTerm検証は未実施理由をJob Summaryへ記録する。

### 入力の制限

対象パスの件数には上限を設けない。ただし、入力を無制限にしないため、次の既存上限と事前見積もり専用の上限を維持する。

| 対象 | 上限 |
| --- | ---: |
| 対象パス指定全体 | 64 KiB |
| 1ファイルの完全入力 | 128 KiB |
| 完全入力ファイルの合計 | 512 KiB |
| 1ファイルの事前見積もりプレビュー | 12,000文字 |
| 事前見積もりコンテキストの合計 | 96 KiB |
| 事前見積もりJSON | 64 KiB |

事前見積もりのプロンプトへ渡すファイル情報は、上記の範囲で切り詰める。完全なファイル内容を見積もりのためにSakura AI Engineへ送らない。

## 検討した代替案

### 完全生成後に差分を測定する

採用しない。最終的な実測ガードとしては残すが、早期判定にならず、分割依頼になる変更でも完全生成のトークンを消費する。

### 静的なファイル数だけで判定する

採用しない。対象パスが多くても変更が小さい依頼を不必要に分割し、対象パスが少なくても1ファイルの大きな変更を見逃すためである。

### AIに40時間を直接見積もらせる

採用しない。40時間という人手工数を差分やIssueだけから安定して算出できず、モデルや依頼文に依存するためである。AIには変更計画と保守的な変更行数の上限だけを求める。

## 影響

分割依頼になる可能性が高い変更では、完全なファイル生成を省略できる。その分、事前見積もり用の小さなAI呼び出しは追加される。

生成可と判定された依頼では、従来どおり完全なファイル生成と実測検証を行う。事前見積もりの誤りによる通過を防ぐため、生成後のGit差分測定は削除しない。

見積もりの確度が低い場合は、無理に生成へ進めず人手確認へ戻す。これにより、コンテキスト不足による過小見積もりを自動公開につなげない。

閾値は40時間超を証明するものではない。成功した自動PRと人手実装の実績を蓄積し、実測工数と見積もり指標の関係を確認してから調整する。

## 再評価条件

次の条件で閾値と見積もり方式を見直す。

- 自動PRまたは比較対象となる人手PRを10件から20件程度蓄積した場合。
- 小さな変更が繰り返し分割依頼となった場合。
- 大きな実測差分が事前見積もりを通過した場合。
- 事前見積もりの低確度が多く、実用的なゲートとして機能しない場合。
- Sakura AI Engineのモデル、コンテキスト上限、料金、レート制限が変わった場合。

## 実装状況

事前見積もりの指標計算と判定は、`.github/scripts/auto-pr-common.mjs`に集約している。

Sakura AI Engineへの共通リクエストは、`.github/scripts/auto-pr-sakura.mjs`に集約している。

事前見積もりの実行は、`.github/scripts/auto-pr-estimate.mjs`と`.github/workflows/auto-pr.yml`に実装している。

完全なファイル生成は事前見積もりの生成可判定を通過した場合だけ実行し、生成後の実差分判定も維持している。

旧仕様の手順書である`GITHUB_ACTIONS_HANDOFF.md`は変更しない。

## 関連ファイル

- [`.github/workflows/auto-pr.yml`](../../.github/workflows/auto-pr.yml)
- [`.github/scripts/auto-pr-common.mjs`](../../.github/scripts/auto-pr-common.mjs)
- [`.github/scripts/auto-pr-estimate.mjs`](../../.github/scripts/auto-pr-estimate.mjs)
- [`.github/scripts/auto-pr-sakura.mjs`](../../.github/scripts/auto-pr-sakura.mjs)
- [`.github/scripts/auto-pr-prepare-trusted.mjs`](../../.github/scripts/auto-pr-prepare-trusted.mjs)
- [`.github/scripts/auto-pr-validate.mjs`](../../.github/scripts/auto-pr-validate.mjs)
- [`.github/scripts/auto-pr-ai.mjs`](../../.github/scripts/auto-pr-ai.mjs)
- [`.github/scripts/auto-pr-publish.mjs`](../../.github/scripts/auto-pr-publish.mjs)
- [`.github/scripts/auto-pr.test.mjs`](../../.github/scripts/auto-pr.test.mjs)
