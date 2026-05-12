# 個人情報チェックツール

Microsoft Presidioを使用して、ソースコード内の個人情報や機密情報を検出するツールです。

## 検出対象

1. **氏名** (JP_PERSON_NAME)
   - 日本人名パターン
   - テスト用のよくある氏名（山田太郎、田中太郎など）

2. **メールアドレス** (EMAIL_ADDRESS)
   - 標準的なメールアドレス形式

3. **電話番号** (JP_PHONE_NUMBER)
   - 固定電話: 0X-XXXX-XXXX
   - 携帯電話: 090/080/070-XXXX-XXXX
   - フリーダイヤル: 0120-XXX-XXX

4. **住所** (JP_ADDRESS)
   - 郵便番号: XXX-XXXX
   - 住所パターン（都道府県、市区町村を含む）

5. **マイナンバー** (JP_MY_NUMBER)
   - 12桁のマイナンバーパターン
   - XXXX-XXXX-XXXX形式

6. **社会保障番号** (US_SSN)
   - アメリカの社会保障番号パターン

7. **クレジットカード番号** (CREDIT_CARD)
   - 16桁のカード番号
   - 15桁のカード番号（AMEX）

## セットアップ

### 1. Python環境の準備

Python 3.7以上が必要です。

### 2. 必要なパッケージのインストール

```powershell
pip install presidio-analyzer presidio-anonymizer
```

または、requirements.txtを使用：

```powershell
pip install -r pii_requirements.txt
```

### 3. 日本語対応のための追加設定（オプション）

より高度な日本語処理を行う場合は、spaCyと日本語モデルをインストール：

```powershell
pip install spacy
python -m spacy download ja_core_news_sm
```

## 使用方法

### 基本的な使用方法

チェックしたいディレクトリに移動して実行：

```powershell
cd C:\Users\hldc0018\Desktop\git_upload_check\SampleDriver
python pii_checker.py
```

### 実行結果

実行すると、以下の処理が行われます：

1. 現在のディレクトリ以下のすべてのテキストファイルをスキャン
2. 個人情報パターンを検出
3. `pii_check_report.txt` にレポートを出力

### レポートの見方

生成されるレポート（`pii_check_report.txt`）には以下が含まれます：

- **サマリー**: 検出された問題の総数とファイル数
- **エンティティタイプ別集計**: どの種類の情報が何件検出されたか
- **詳細結果**: 
  - ファイル名
  - 検出された行番号
  - 検出された文字列
  - 前後のコンテキスト
  - 信頼度スコア（0.0〜1.0）

## スキャン対象ファイル

以下の拡張子を持つファイルがスキャンされます：

- ソースコード: `.c`, `.h`, `.cpp`, `.hpp`, `.py`, `.java`, `.js`, `.cs`など
- 設定ファイル: `.xml`, `.json`, `.yaml`, `.ini`, `.cfg`, `.conf`など
- ドキュメント: `.txt`, `.md`, `.rst`, `.html`など
- ログファイル: `.log`
- データファイル: `.csv`, `.tsv`

## スキップされるファイル

以下はスキャンされません：

- バイナリファイル (`.exe`, `.dll`, `.so`, `.o`など)
- 画像ファイル (`.jpg`, `.png`など)
- 圧縮ファイル (`.zip`, `.tar`, `.gz`など)
- 隠しファイル・ディレクトリ（`.`で始まる）
- 特定のディレクトリ (`__pycache__`, `node_modules`, `.git`など)

## カスタマイズ

### スキャン対象のカスタマイズ

`pii_checker.py`の`PIIChecker`クラス内で以下を変更できます：

- `text_extensions`: スキャンする拡張子の追加
- `skip_extensions`: スキップする拡張子の追加
- `entities`: 検出するエンティティタイプの変更

### カスタムパターンの追加

独自のパターンを追加する場合は、新しいレコグナイザークラスを作成します：

```python
class CustomRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [
            Pattern(
                name="custom_pattern",
                regex=r"your_regex_pattern",
                score=0.8
            )
        ]
        super().__init__(
            supported_entity="CUSTOM_ENTITY",
            patterns=patterns,
            supported_language="ja"
        )
```

## 注意事項

1. **誤検出について**: 
   - パターンマッチングベースのため、誤検出（False Positive）が発生する可能性があります
   - 信頼度スコアを参考に判断してください

2. **大規模プロジェクトでの実行**:
   - ファイル数が多い場合、処理に時間がかかることがあります
   - 必要に応じてスキャン対象を絞ることを検討してください

3. **エンコーディング**:
   - 複数のエンコーディング（UTF-8, Shift-JIS, EUC-JPなど）に対応していますが、特殊な文字コードでは読み込めない場合があります

4. **本番データの混入チェック**:
   - 既知の本番データパターンがある場合は、カスタムレコグナイザーを追加することを推奨します

## トラブルシューティング

### インストールエラー

```
ERROR: Could not find a version that satisfies the requirement presidio-analyzer
```

Python 3.7以上であることを確認してください：

```powershell
python --version
```

### メモリエラー

大規模なファイルでメモリエラーが発生する場合は、ファイルをチャンク単位で処理するよう修正が必要です。

## ライセンス

このスクリプトは、Microsoft Presidioのライセンス（MITライセンス）に従います。

## 関連リンク

- [Microsoft Presidio公式ドキュメント](https://microsoft.github.io/presidio/)
- [Presidio GitHub](https://github.com/microsoft/presidio)
