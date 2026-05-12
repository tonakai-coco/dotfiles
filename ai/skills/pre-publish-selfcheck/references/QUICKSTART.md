# クイックスタートガイド

## 1. 初回セットアップ（初めて使う場合のみ）

### PowerShellで実行する場合

```powershell
# 必要なパッケージをインストール
.\run_pii_check.ps1 -Install
```

### 手動でインストールする場合

```powershell
pip install -r pii_requirements.txt
```

## 2. チェックの実行

### 最も簡単な方法（PowerShellスクリプト使用）

```powershell
.\run_pii_check.ps1
```

### Pythonスクリプトを直接実行

```powershell
python pii_checker.py
```

## 3. 結果の確認

チェック完了後、`pii_check_report.txt` が生成されます。

```powershell
# レポートを開く
notepad pii_check_report.txt

# または、PowerShellで表示
Get-Content pii_check_report.txt -Encoding UTF8
```

## 実行例

### 例1: 基本的な実行

```powershell
PS C:\Users\hldc0018\Desktop\git_upload_check\SampleDriver> python pii_checker.py

個人情報チェッカー (Microsoft Presidio)
================================================================================
スキャン開始: C:\Users\hldc0018\Desktop\git_upload_check\SampleDriver
--------------------------------------------------------------------------------
スキャン中 (1): 1_NonOS\1-1_async\dt_async_drv_11a\main.c
スキャン中 (2): 1_NonOS\1-1_async\dt_async_drv_11a\readme.txt
...
--------------------------------------------------------------------------------
スキャン完了: 150ファイル処理, 45ファイルスキップ

レポートを生成しました: pii_check_report.txt
検出された問題: 3件 (2ファイル)
```

### 例2: 結果の解釈

レポート内容の例：

```
================================================================================
個人情報チェックレポート
================================================================================

検出された問題の総数: 3
問題のあるファイル数: 2

【検出されたエンティティタイプ】
  - 電話番号 (JP_PHONE_NUMBER): 2件
  - メールアドレス (EMAIL_ADDRESS): 1件

================================================================================

ファイル: 2_Windows\2-1_ether\dt_ether_drv_21a\sample.c
--------------------------------------------------------------------------------

  [電話番号] (信頼度: 0.85)
  行番号: 45
  検出文字列: 03-1234-5678
  コンテキスト: ...// サポート連絡先: 03-1234-5678 までお問い合わせください...

  [メールアドレス] (信頼度: 0.95)
  行番号: 46
  検出文字列: support@example.co.jp
  コンテキスト: ...// Email: support@example.co.jp でお問い合わせ...

================================================================================
```

## よくある使用シナリオ

### シナリオ1: Git commitの前にチェック

```powershell
# チェックを実行
python pii_checker.py

# 問題がなければcommit
git add .
git commit -m "コミットメッセージ"
```

### シナリオ2: 特定のディレクトリのみチェック

スクリプトを修正するか、対象ディレクトリに移動して実行：

```powershell
cd 2_Windows\2-1_ether
python ..\..\pii_checker.py
```

### シナリオ3: CI/CDパイプラインに組み込む

```powershell
# 自動チェック（問題があればビルド失敗）
python pii_checker.py
if (Test-Path pii_check_report.txt) {
    $content = Get-Content pii_check_report.txt -Raw
    if ($content -notmatch "個人情報は検出されませんでした") {
        Write-Error "個人情報が検出されました！"
        exit 1
    }
}
```

## トラブルシューティング

### 問題: "presidio-analyzer がインストールされていません"

解決策:
```powershell
pip install presidio-analyzer presidio-anonymizer
```

### 問題: "エンコーディング検出失敗"

原因: 特殊なエンコーディングのファイルが存在  
解決策: そのファイルをスキップするか、エンコーディングを変更

### 問題: 誤検出が多い

解決策: `pii_checker_config.ini` の `min_score` を調整（例: 0.7に上げる）

### 問題: 処理が遅い

原因: ファイル数が多すぎる  
解決策: 
- 不要なディレクトリを除外設定に追加
- 特定のディレクトリのみスキャン

## 次のステップ

1. **設定のカスタマイズ**: `pii_checker_config.ini` を編集
2. **カスタムパターンの追加**: 独自のパターンを追加
3. **自動化**: Git hooksやCI/CDに組み込む

## ヘルプが必要な場合

詳細なドキュメント: `PII_CHECK_README.md` を参照
