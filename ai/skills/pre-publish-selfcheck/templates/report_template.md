# 公開前セルフチェックレポート

**実施日**: YYYY-MM-DD  
**対象ディレクトリ**: <path>  
**チェック実施者**: <担当者名または "GitHub Copilot による自動チェック">

---

## チェック結果サマリー

| フェーズ           | ツール            | 結果  | 要対応    |
| ------------------ | ----------------- | ----- | --------- |
| 1 シークレット     | Gitleaks vX.X.X   | ✅/⚠️ | あり/なし |
| 2 社内ネットワーク | semgrep vX.X.X    | ✅/⚠️ | あり/なし |
| 3 ライセンス       | REUSE lint vX.X.X | ✅/⚠️ | あり/なし |
| 4 個人情報 (PII)   | Presidio vX.X.X   | ✅/⚠️ | あり/なし |
| 5 未発表製品情報   | grep + 目視       | ✅/⚠️ | あり/なし |

---

## 実施手順（再現手順）

> 各フェーズで実際に実行したコマンドと、その出力の要点（バージョン・件数・終了コード）を記載する。
> `...` のまま残すことは禁止。第三者がこのセクションだけで再現・監査できる粒度で書くこと。

### フェーズ 0: セットアップ

```powershell
# 実際に実行したコマンドをここに記載
# 例: cd <ターゲットディレクトリ>
# 例: uv pip install semgrep reuse --python .\.venv\Scripts\python.exe
# 例: Add-Content .gitignore "`n.venv/"
```

### フェーズ 1: シークレットチェック

```powershell
# 実際に実行したコマンドをここに記載
# 例: gitleaks detect --source . --report-format json --report-path .\gitleaks-report.json
# 出力要点: 例) 201 commits scanned, 14.41 MB, no leaks found (exit code 0)
```

### フェーズ 2: 社内ネットワーク情報チェック

```powershell
# 実際に実行したコマンドをここに記載
# 例: .\.venv\Scripts\semgrep --config .\semgrep.yml . --exclude semgrep.yml
# 出力要点: 例) Ran 14 rules on 68 files: 0 findings.
```

### フェーズ 3: ライセンスチェック

```powershell
# 実際に実行したコマンドをここに記載
# 例: .\.venv\Scripts\reuse lint 2>&1 | Where-Object { $_ -match "XM125_IR_MINTIA" }
# 出力要点: 例) LICENSEあり。全ソースファイルにCopyrightヘッダー確認済み
```

### フェーズ 4: 個人情報チェック

```powershell
# 実際に実行したコマンドをここに記載
# 例: .\.venv\Scripts\python.exe "<skillScripts>\pii_checker.py"
# 出力要点: 例) 94ファイル処理, 検出49件(2ファイル) → 全件偽陽性（詳細は詳細結果セクション参照）
```

### フェーズ 5: 未発表製品情報チェック

```powershell
# 実際に実行したコマンドをここに記載
# 例: Get-ChildItem -Recurse -Include "*.c","*.cpp","*.h","*.hpp","*.md","*.py" | ...
# 出力要点: 例) TODO 3件検出（data_parser_service.cpp, task_sensor.cpp）
```

---

## チェック時に生成されたファイル

| ファイル               | 内容                      | .gitignore 済み |
| ---------------------- | ------------------------- | --------------- |
| `gitleaks-report.json` | Gitleaks スキャン結果     | ✅              |
| `semgrep.yml`          | semgrep カスタムルール    | ✅              |
| `pii_check_report.txt` | Presidio PII スキャン結果 | ✅              |
| `.venv/`               | Python 仮想環境           | ✅              |

---

## 詳細結果

（フェーズごとの詳細、推測を含む場合は「※推測」と明記）

---

## 推奨対策

（問題あり → 対処内容。問題なし → 「なし」）
