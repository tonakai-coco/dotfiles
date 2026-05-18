---
name: pre-publish-selfcheck
description: >
  GitHubパブリックリポジトリへの公開前セルフチェックを実施するスキル。
  シークレット漏洩、社内ネットワーク情報、ライセンス表記不備、個人情報（PII）、
  未発表製品情報の5フェーズで自動・手動チェックを行い、Markdownレポートを生成する。
  Windows環境（PowerShell + uv + winget）専用。
  ユーザーが「GitHubに公開する前にチェックして」「公開前セルフチェック」「OSSとして公開したい」
  「リポジトリを外部公開する準備」「セキュリティチェック」と言ったら必ずこのスキルを使うこと。
  ESP32/組み込みファームウェア、C/C++、Pythonプロジェクトいずれにも適用できる。
---

# 公開前セルフチェック（GitHub パブリックリポジトリ向け）

Windows PowerShell 環境で、公開前に自動ツール＋手動 grep の5フェーズでコードを検査し、
最終 Markdown レポートを生成する。

---

## 対象ディレクトリの確認

ユーザーに確認すること:

- **チェック対象ディレクトリ**: 現在の作業ディレクトリか、サブディレクトリかを確認する
- 以降、`$TARGET` に対象ディレクトリを設定して作業する

---

## フェーズ 0: ツールセットアップ

チェックを開始する前に `.venv` を作成してツールをインストールする。

```powershell
# 対象ディレクトリへ移動
cd <ターゲットディレクトリ>

# uv が入っていない場合はインストール
winget install astral-sh.uv

# Python 仮想環境を作成
uv venv .venv

# semgrep と reuse を仮想環境にインストール
uv pip install semgrep reuse --python .\.venv\Scripts\python.exe

# Gitleaks をシステムワイドにインストール（既にある場合はスキップ）
winget install gitleaks

# .gitignore に .venv を追加（まだない場合）
if (-not (Select-String -Path .gitignore -Pattern "^\.venv" -Quiet 2>$null)) {
    Add-Content .gitignore "`n.venv/"
    Write-Host ".venv/ を .gitignore に追加しました"
}
```

---

## フェーズ 1: 🔐 シークレット・パスワードチェック（Gitleaks）

```powershell
cd <ターゲットディレクトリ>
gitleaks detect --source . --report-format json --report-path .\gitleaks-report.json
```

**結果の解釈:**

- `leaks found: 0` → ✅ 問題なし
- 検出あり → `gitleaks-report.json` の `Description` と `File` を確認する

**注意点:**

- ログに `host=192.168.x.x` が表示される場合がある。これは Gitleaks が `.git/config` の
  remote URL から読んだものであり、**ファインディングではない**（JSON レポートが空なら問題なし）
- `gitleaks-report.json` は自動生成されるため `.gitignore` に追加する:

  ```powershell
  Add-Content .gitignore "`ngitleaks-report.json"
  ```

---

## フェーズ 2: 🌐 社内ネットワーク情報チェック（semgrep）

`scripts/semgrep.yml`（このスキルにバンドル）をターゲットディレクトリにコピーして実行する。

```powershell
# semgrep.yml をコピー（スキルの scripts/ から）
Copy-Item "<スキルパス>\scripts\semgrep.yml" ".\semgrep.yml"

# エンコーディング設定（Windowsで日本語コメントがある場合に必須）
$env:PYTHONUTF8 = "1"

# スキャン実行（semgrep.yml 自身を除外することで自己マッチを防ぐ）
.\.venv\Scripts\semgrep --config .\semgrep.yml . --exclude semgrep.yml

# チェック完了後、semgrep.yml を .gitignore に追加
Add-Content .gitignore "`nsemgrep.yml"
```

**`--exclude semgrep.yml` が重要な理由:**  
`semgrep.yml` のルール説明文（日本語コメント内）に `192.168.x.x` や `srv01` などの
サンプルパターンが含まれており、ルールが自分自身にマッチしてしまう（偽陽性）。

**結果の解釈:**

- `Findings: 0` → ✅ 問題なし
- 検出あり → ファイル・行番号を確認し、社内情報かダミー値かを判断する

---

## フェーズ 3: ©️ ライセンス・著作権チェック（REUSE）

```powershell
cd <ターゲットディレクトリ>
.\.venv\Scripts\reuse lint 2>&1 | Tee-Object -Variable reuseOutput
$reuseOutput | Select-String -Pattern "(<ターゲットディレクトリ名>|MISSING|ERROR|WARNING)"
```

**注意点:**  
`reuse lint` は Git リポジトリルートから全ファイルをスキャンする。
サブディレクトリが対象の場合は出力をフィルタリングすること。

**確認すべき項目:**

| 項目                     | 確認内容                                       |
| ------------------------ | ---------------------------------------------- |
| `LICENSE` ファイル       | リポジトリルートに存在するか                   |
| サードパーティライブラリ | 各コンポーネントのライセンスヘッダーを目視確認 |
| 自社ソース               | `Copyright` 表記が含まれているか               |
| `@author` / `@date`      | 空白でないか                                   |

**ソースファイルのライセンスヘッダー確認コマンド:**

```powershell
# Copyright/SPDX が含まれないファイルを列挙
# ※ PowerShell では配列に -notmatch を使うと「マッチしない行」が返るだけで
#   「ファイル全体にマッチしない」判定にはならない。-not (...-match ...) を使うこと。
git ls-files -- "*.c" "*.h" "*.cpp" "*.hpp" |
  Where-Object { $_ -notmatch "^build/" -and $_ -notmatch "^test/.*build" } |
  ForEach-Object {
    $content = Get-Content $_ -TotalCount 15 -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not ($content -match "Copyright|SPDX|copyright|@copyright")) { $_ }
  }
```

---

## フェーズ 4: 👤 個人情報チェック（Microsoft Presidio）

`scripts/run_pii_check.ps1` をスキルフォルダから直接実行する（コピー不要）。  
詳細な使い方は `references/QUICKSTART.md` と `references/PII_CHECK_README.md` を参照。

```powershell
$skillScripts = "<スキルパス>\scripts"

# Presidio と spaCy 日本語モデルをインストール（初回のみ）
& "$skillScripts\run_pii_check.ps1" -Install

# PII チェック実行（カレントディレクトリ = ターゲットディレクトリであること）
$env:PYTHONUTF8 = "1"
& "$skillScripts\run_pii_check.ps1"
```

**生成ファイル:** `pii_check_report.txt`（`.gitignore` に追加する）

```powershell
Add-Content .gitignore "`npii_check_report.txt"
```

既知の偽陽性パターンは `references/troubleshooting.md` を参照。

**ファームウェアソース（`main/`, `components/`）に 0 件なら合格。**

---

## フェーズ 5: 📢 未発表製品情報チェック（grep + 目視）

### 5-1. TODO/FIXME コメントスキャン

```powershell
Get-ChildItem -Recurse -Include "*.c","*.cpp","*.h","*.hpp","*.md","*.py" |
  Select-String -Pattern "(TODO|FIXME|HACK|XXX|NOTE):" |
  Where-Object { $_.Path -notmatch "\\build\\" -and $_.Path -notmatch "\\.venv\\" }
```

### 5-2. カスタムキーワードスキャン

プロジェクト固有の未発表製品名・コードネームを `.pr-keywords-blacklist.txt` に記載して実行:

```powershell
# キーワードファイルを作成（1行1キーワード、# でコメント）
# 例: project-phoenix, ACME-v3, internal-only

if (Test-Path ".pr-keywords-blacklist.txt") {
    Get-Content ".pr-keywords-blacklist.txt" | ForEach-Object {
        $kw = $_.Trim()
        if ($kw -and -not $kw.StartsWith("#")) {
            $hits = Get-ChildItem -Recurse -Include "*.c","*.cpp","*.h","*.hpp","*.md","*.txt","*.py" |
                Select-String -Pattern $kw -SimpleMatch |
                Where-Object { $_.Path -notmatch "\\.venv\\" }
            if ($hits) {
                Write-Host "⚠️  '$kw' が検出されました:" -ForegroundColor Yellow
                $hits | ForEach-Object { Write-Host "  $($_.Filename):$($_.LineNumber): $($_.Line.Trim())" }
            }
        }
    }
    Write-Host "キーワードスキャン完了"
} else {
    Write-Host "⚠️  .pr-keywords-blacklist.txt が見つかりません。プロジェクト固有のキーワードをリストアップして作成してください。"
}
```

### 5-3. 目視確認項目

以下は自動検出できないため、**必ず人間が判断**すること:

| #   | 確認対象                         | 確認内容                                   |
| --- | -------------------------------- | ------------------------------------------ |
| A   | 製品名・基板名                   | コードネームとして外部公開可能か           |
| B   | 社内ライブラリ・コンポーネント名 | 外部秘の製品・プロジェクト名でないか       |
| C   | ブランチ名・コミットメッセージ   | 内部チケット番号や未発表情報が含まれないか |
| D   | テスト用マクロ・スクリプト       | 社内案件固有の接続先情報が含まれないか     |
| E   | 画像・スクリーンショット         | 未発表 UI が写り込んでいないか             |

---

## 最終レポートの生成

全フェーズ完了後、`templates/report_template.md` のテンプレートに結果を埋めてレポートを生成する。
ファイル名は `PUBLISH_SELFCHECK_REPORT.md` を推奨（リポジトリに含めるか否かはユーザーが判断）。

> ⚠️ **`実施手順（再現手順）` セクションは必ず埋めること。**  
> テンプレートの `...` プレースホルダーをそのまま残してはならない。  
> 各フェーズで**実際に実行したコマンド**と、その**出力の要点**（バージョン番号・スキャン件数・
> 終了コード・検出件数など）をコードブロックで記載する。  
> このセクションがあることで、チェック内容を第三者が再現・監査できる。

---

## バンドルリソース

| パス                             | 説明                                                    |
| -------------------------------- | ------------------------------------------------------- |
| `scripts/semgrep.yml`            | 社内 IP / サーバー名 / ドメイン / VPN 設定のルール（フェーズ 2） |
| `scripts/pii_checker.py`         | Microsoft Presidio ベースの PII チェッカー（日本語対応）|
| `scripts/pii_checker_config.ini` | PII チェッカー設定ファイル                              |
| `scripts/pii_requirements.txt`   | PII チェッカーの Python 依存パッケージ                  |
| `scripts/run_pii_check.ps1`      | PII チェッカーの PowerShell ラッパー（-Install / 実行） |
| `templates/report_template.md`   | 最終レポートのテンプレート                              |
| `references/troubleshooting.md`  | よくある問題・既知の偽陽性パターン                      |
| `references/QUICKSTART.md`       | PII チェッカーのクイックスタートガイド                  |
| `references/PII_CHECK_README.md` | PII チェッカーの詳細ドキュメント                        |
