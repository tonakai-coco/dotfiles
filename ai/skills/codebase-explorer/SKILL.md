---
name: codebase-explorer
description: 未知のコードベース・SDK・ファームウェアを素早く理解したいとき、オンボーディング資料を作りたいとき、ベンダー提供コードを内製改変する前の解読フェーズに必ず使うこと。静的解析・動的観測プラン・Git 履歴の3観点で段階的に文書化し、新規メンバーが30分で概要を把握できる成果物セットを生成する。ユーザーが「コードを読み解きたい」「リポジトリの構造を整理したい」「このコードベースを理解したい」「オンボーディング資料を作りたい」「設計を把握したい」「このコードを調べてほしい」「SDK を調べてほしい」のように言ったら迷わずこのスキルを使うこと。
---

# codebase-explorer

未知のリポジトリを「人間がメンタルモデルを構築しやすい形」で段階的に解読・文書化する。
単純な「AIに要約させる」だけでは抜け落ちる **Why / 実行時挙動 / History** を補い、
静的解析 × 動的観測 × Git 履歴 の3観点で整理する。

---

## パラメータ

| 名前 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `repo_path` | ✅ | — | 対象コードベースのルートパス |
| `entry_hint` | | — | 入口のヒント（例: `app_main`, `main.c`, `/api/...`, ISR 名）|
| `use_case` | | — | トレース対象のユースケース 1 つ（例: "USB Start コマンド受信 → 1 フレーム描画"）|
| `output_dir` | | `./docs/codebase-explorer/` | 成果物の出力先 |
| `language` | | `ja` | 出力言語 |
| `git_enabled` | | `true` | Git 履歴解析を行うか |

---

## 成果物

| # | ファイル | 内容 |
|---|---|---|
| 1 | `00_overview.md` | Executive Summary / リポジトリの目的・構成・技術スタック |
| 2 | `01_c4_context.md` | C4 Lv1 Context 図 (Mermaid) — 外部アクター・外部システム |
| 3 | `02_c4_container.md` | C4 Lv2 Container 図 — プロセス・基板・プロトコル |
| 4 | `03_c4_component.md` | C4 Lv3 Component 図 — 主要モジュール・責務・依存 |
| 5 | `04_sequence_<usecase>.md` | 指定ユースケースのエンドツーエンドシーケンス図 (Mermaid) |
| 6 | `05_runtime_observation.md` | 動的観測プラン: ログポイント / ブレーク位置 / バスキャプチャ推奨箇所 |
| 7 | `06_glossary.md` | ドメイン用語・略語・レジスタ名・ピン名・状態名の索引 |
| 8 | `07_hotspots.md` | Git churn × 複雑度 で算出した「先に読むべき」ファイル Top 20 |
| 9 | `08_adr_candidates.md` | コードから読み取れる設計判断を ADR 形式で列挙 (Status: Inferred) |
| 10 | `09_unknowns_qa.md` | コードから読み取れない疑問点の質問リスト（提供元送付用） |
| 11 | `.tours/10_code_tour.tour` | VSCode Code Tour 拡張用 — 読む順番をステップ化（標準 CodeTour 形式、拡張子 `.tour`）|
| 12 | `README.md` | 上記 1〜11 への目次と推奨読書順 |

---

## ワークフロー（必ずこの順で実行）

### Phase 1: 静的スキャン

**目的**: コードベース全体の構造と依存関係を把握し、C4 図と概要を生成する。

1. ディレクトリツリーを取得（`tree -L 3` 相当、無視: `build/`, `node_modules/`, `.git/`, `*.zip`, 画像, PDF）
2. 言語とビルドシステムを検出（CMake / ESP-IDF / Gradle / Cargo / package.json 等）
3. エントリポイントを特定（`main`, `app_main`, `setup()`, `index.*`, エクスポート関数, HTTP ルート, ISR テーブル）
4. include/import グラフを解析 → Mermaid `graph TD` で依存関係を可視化
5. **生成**: `00_overview.md`, `01_c4_context.md`, `02_c4_container.md`, `03_c4_component.md`
   - `03_c4_component.md` は **Mermaid 図の分割ルール**（後述）に従って生成すること

### Phase 2: 動的トレース（1 ユースケース集中）

**目的**: 1本のコールパスを徹底的に追い、実行時の観測ポイントを特定する。
複数のユースケースを同時に追うと迷子になるため、必ず1本に絞ること。

6. `use_case` が未指定なら候補を 3 つ提案してユーザーに確認
7. 入口 → 出口まで **1 本だけ** コールパスを追う
8. 各ステップの「呼び出し元ファイル:行」を引用付きでリスト化（例: `main.c:1349`）
9. Mermaid `sequenceDiagram` に変換 → `04_sequence_<usecase>.md`
10. 同じパス上で観測可能なポイントを抽出し `05_runtime_observation.md` に：
    - `printf` / `ESP_LOGI` 等を挿入すべき位置と期待値
    - デバッガで止めるべきブレークポイント
    - SPI / USB / UART のバスキャプチャ推奨ポイント
    - 期待される値・周期・タイミング

### Phase 3: 履歴・用語・疑問点

**目的**: 「Why」を補完し、提供元への質問リストを作る。

11. `git_enabled=true` なら `git log --numstat` + 複雑度（cyclomatic または行数）でホットスポット Top 20 → `07_hotspots.md`
    - 履歴が浅い / 提供ソースのみの場合は `"N/A (shallow history)"` と明記
12. コメント・マクロ名・レジスタ名・状態名から用語を抽出 → `06_glossary.md`
13. `#define` マジックナンバー・定数テーブル・`if` 分岐の判断基準から「設計判断」を推定 → `08_adr_candidates.md`
    - Status は必ず `Inferred` と明記（事実との混同を防ぐため）
14. コメントが薄い / マジックナンバーの根拠不明 / タイミング値の出典不明な箇所 → `09_unknowns_qa.md`
    - カテゴリ別・優先度付きで整理し、提供元への質問に使える粒度で書く

### Phase 4: 読書ガイド化

**目的**: 成果物を「読める順番」に整理し、新規メンバーが迷わないナビゲーションを作る。

15. Phase 1〜3 の成果物を参照する順番をステップ化 → `.tours/10_code_tour.tour`（VSCode Code Tour 拡張の標準形式）
    - ファイルはワークスペースルート直下の **`.tours/`** ディレクトリに置く（CodeTour 拡張の自動検出対象）
    - 拡張子は必ず **`.tour`**（`.json` や `.tours.json` 不可）
    - **必須スキーマ**（`tours` 配列は使わない。`steps` をトップレベルに置く）:
      ```json
      {
        "title": "ツアー名",
        "description": "説明",
        "steps": [
          {
            "title": "Step N: セクション名",
            "file": "ワークスペースルート相対パス/ファイル名",
            "line": 行番号,
            "description": "説明文"
          }
        ]
      }
      ```
    - `file` は **ワークスペースルート相対パス**（`main/main.c` ではなく `FW_RPU_POSTURE_TILT/main/main.c` のように上位ディレクトリを含める）
    - 各 Step のタイトルは `"Step N: セクション名"` 形式で統一する
    - Step 1: overview → Step 2: C4 Context → ... → Step N: sequence の入口ファイル
16. `README.md` に目次と以下の2コースを提示：
    - **30分コース**: overview + C4 Lv1-2 + sequence で「何をするシステムか」を把握
    - **2時間コース**: Code Tour を辿り、1ユースケースの入口→出口を再現

---

## Mermaid 図の分割ルール（C4 Lv3 Component 図）

1 つの `graph TD` に **subgraph が 4 つ以上** または **ノード数が 15 以上** になる場合は、必ず以下の構成に分割する。

### 構成

```
## 概要図（サブシステム間の依存）
各 subgraph を 1 ノードに抽象化した全体俯瞰図（ノード数は subgraph 数と同数）

## 詳細図 1 — <subgraph 名>
当該 subgraph の内部フローのみ

## 詳細図 2 — <subgraph 名>
...
```

### ルール

- **概要図**: `graph TD` で subgraph を 1 ノードとして表現。subgraph 間のデータ・制御フローのエッジのみ描く。ノード ID は UPPER_CASE の短縮名（例: `MAIN`, `CMD`, `AK`）。
- **詳細図**: subgraph ごとに独立した `graph TD` を 1 つ。他の subgraph のノードは「入力ノード」として最小限だけ表現する（例: `H_IN["呼び出し元"]`）。
- **エッジラベル**はダブルクォートで囲む（`-->|"ラベル"|`）。日本語・スペース・記号が含まれる場合も同様。
- subgraph が 3 つ以下かつノード数 14 以下なら 1 枚の図にまとめてよい。

---

## 出力ルール

- すべての図は **Mermaid** で書く（PlantUML 不可。Markdown ネイティブで見えるため）
- コード引用は必ず `file:line` 形式（例: `main.c:1349-1367`）
- 推測部分は **Confidence ★1〜5** を明記（★5 = 確実、★1 = 根拠薄弱）
- ADR・Glossary・QA は表形式
- 「AI の自己紹介」「推測の言い訳」「冗長な導入文」は書かない
- 技術用語は原語優先（"RPU", "CFAR", "SPI", "ISR" はそのまま）

---

## 制約

- バイナリ・画像・PDF は読み込まない（存在のみリスト化）
- 1 ファイルあたり 5000 行超の場合は関数単位で分割して読む
- プロプライエタリコードのレジスタマップ等、仕様書がないと不明な箇所は**推測せず** `09_unknowns_qa.md` に回す

---

## 成功基準

- 新規メンバーが **30 分** で overview + C4 Lv1-2 + sequence を読み、何をするシステムかを口頭で説明できる
- **2 時間** で Code Tour を辿り、1 ユースケースの入口→出口を再現できる
- **QA リスト** が提供元への質問送付にそのまま使える粒度で揃っている

---

## Anti-patterns（やってはいけない）

- ❌ 全ファイルを機械的に要約する（メンタルモデルにならない）
- ❌ ユースケースを複数同時に追う（最初の 1 本で迷子になる）
- ❌ 推測を事実として書く（Confidence と Inferred ラベルを必ず使う）
- ❌ AI 生成であることを隠す / 誇示する（淡々と事実のみ）

---

## 呼び出し例

```
/skill codebase-explorer
repo_path=C:\PROJ\radar\aimez-v\FW_RPU_POSTURE_TILT
entry_hint=app_main
use_case="USB Startコマンド受信→1フレーム描画データ送信"
output_dir=./docs/explorer/
language=ja
```
