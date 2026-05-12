"""
個人情報チェックスクリプト (Microsoft Presidio使用)
日本語環境対応版

使用方法:
    python pii_checker.py

必要なパッケージ:
    pip install presidio-analyzer presidio-anonymizer
"""

import os
import re
from typing import List, Dict
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider


class JapaneseMyNumberRecognizer(PatternRecognizer):
    """マイナンバー（12桁）を検出するカスタムレコグナイザー"""
    
    def __init__(self):
        patterns = [
            Pattern(
                name="my_number_pattern",
                regex=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                score=0.85
            ),
            Pattern(
                name="my_number_continuous",
                regex=r"\b\d{12}\b",
                score=0.75
            )
        ]
        super().__init__(
            supported_entity="JP_MY_NUMBER",
            patterns=patterns,
            supported_language="ja"
        )


class JapanesePhoneRecognizer(PatternRecognizer):
    """日本の電話番号を検出するカスタムレコグナイザー"""
    
    def __init__(self):
        patterns = [
            # 固定電話: 0X-XXXX-XXXX, 0XX-XXX-XXXX, 0XXX-XX-XXXX
            Pattern(
                name="jp_phone_hyphen",
                regex=r"\b0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}\b",
                score=0.7
            ),
            # 携帯電話: 090-XXXX-XXXX, 080-XXXX-XXXX, 070-XXXX-XXXX
            Pattern(
                name="jp_mobile",
                regex=r"\b0[789]0[-\s]?\d{4}[-\s]?\d{4}\b",
                score=0.85
            ),
            # フリーダイヤル: 0120-XXX-XXX
            Pattern(
                name="jp_toll_free",
                regex=r"\b0120[-\s]?\d{3}[-\s]?\d{3}\b",
                score=0.8
            )
        ]
        super().__init__(
            supported_entity="JP_PHONE_NUMBER",
            patterns=patterns,
            supported_language="ja"
        )


class JapaneseAddressRecognizer(PatternRecognizer):
    """日本の住所パターンを検出するカスタムレコグナイザー"""
    
    def __init__(self):
        patterns = [
            # 郵便番号: 123-4567
            Pattern(
                name="jp_postal_code",
                regex=r"\b\d{3}[-\s]?\d{4}\b",
                score=0.6
            ),
            # 住所キーワード付きパターン
            Pattern(
                name="jp_address_keywords",
                regex=r"[都道府県][^\s]{1,10}[市区町村][^\s]{0,20}[丁目番地号\-\d]",
                score=0.85
            )
        ]
        super().__init__(
            supported_entity="JP_ADDRESS",
            patterns=patterns,
            supported_language="ja"
        )


class JapaneseNameRecognizer(PatternRecognizer):
    """日本人名パターンを検出するカスタムレコグナイザー"""
    
    def __init__(self):
        # よくあるテスト用の氏名パターンを検出
        common_test_names = [
            "山田太郎", "山田花子", "田中太郎", "佐藤太郎", "鈴木一郎",
            "テスト太郎", "試験太郎", "サンプル太郎", "テストユーザー"
        ]
        
        patterns = [
            # 一般的な姓名パターン（漢字2-4文字 + 漢字2-4文字）
            Pattern(
                name="jp_name_kanji",
                regex=r"[一-龯]{2,4}[\s　][一-龯]{2,4}",
                score=0.5
            ),
            # テスト用の名前パターン
            Pattern(
                name="test_names",
                regex=r"(" + "|".join(common_test_names) + r")",
                score=0.9
            )
        ]
        super().__init__(
            supported_entity="JP_PERSON_NAME",
            patterns=patterns,
            supported_language="ja"
        )


class PIIChecker:
    """個人情報チェッカー"""
    
    def __init__(self):
        # Presidio Analyzerの初期化（日本語NLPサポート付き）
        try:
            # spaCyの日本語モデルを使用
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "ja", "model_name": "ja_core_news_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["ja", "en"])
        except Exception as e:
            # 日本語モデルがない場合はデフォルトで初期化
            print(f"  注意: 日本語NLPモデルが利用できません ({e})")
            print("  パターンマッチングのみで動作します")
            self.analyzer = AnalyzerEngine()
        
        # カスタムレコグナイザーを登録
        self.analyzer.registry.add_recognizer(JapaneseMyNumberRecognizer())
        self.analyzer.registry.add_recognizer(JapanesePhoneRecognizer())
        self.analyzer.registry.add_recognizer(JapaneseAddressRecognizer())
        self.analyzer.registry.add_recognizer(JapaneseNameRecognizer())
        # クレジットカードはPresidio標準のものを使用
        
        # チェック対象のエンティティタイプ
        self.entities = [
            "JP_MY_NUMBER",          # マイナンバー
            "JP_PHONE_NUMBER",       # 電話番号
            "JP_ADDRESS",            # 住所
            "JP_PERSON_NAME",        # 氏名
            "CREDIT_CARD",           # クレジットカード
            "EMAIL_ADDRESS",         # メールアドレス（Presidio標準）
            "US_SSN",                # 社会保障番号（Presidio標準）
        ]
        
        # スキャン対象外の拡張子
        self.skip_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
            '.zip', '.tar', '.gz', '.7z', '.rar',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.o', '.obj', '.a', '.lib',
            '.pyc', '.pyo', '.pyd'
        }
        
        # スキャン対象のテキストファイル拡張子
        self.text_extensions = {
            '.txt', '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx',
            '.py', '.java', '.js', '.ts', '.cs', '.go', '.rb',
            '.php', '.pl', '.sh', '.bat', '.cmd', '.ps1',
            '.xml', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.md', '.rst', '.html', '.htm', '.css', '.scss',
            '.sql', '.log', '.csv', '.tsv',
            '.properties', '.conf', '.config'
        }
    
    def should_scan_file(self, file_path: Path) -> bool:
        """ファイルをスキャンすべきかを判定"""
        # 隠しファイル・ディレクトリをスキップ
        if any(part.startswith('.') for part in file_path.parts):
            return False
        
        # 特定のディレクトリをスキップ
        skip_dirs = {'__pycache__', 'node_modules', '.git', '.svn', 'build', 'dist'}
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            return False
        
        ext = file_path.suffix.lower()
        
        # スキップ対象の拡張子
        if ext in self.skip_extensions:
            return False
        
        # テキストファイル拡張子、または拡張子なし（Makefileなど）
        if ext in self.text_extensions or ext == '':
            return True
        
        return False
    
    def read_file_safely(self, file_path: Path) -> str:
        """ファイルを安全に読み込む（エンコーディング自動検出）"""
        encodings = ['utf-8', 'shift-jis', 'euc-jp', 'iso-2022-jp', 'cp932', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                print(f"  警告: ファイル読み込みエラー ({file_path}): {e}")
                return ""
        
        # すべてのエンコーディングで失敗した場合
        print(f"  警告: エンコーディング検出失敗 ({file_path})")
        return ""
    
    def analyze_text(self, text: str, language: str = "ja") -> List[Dict]:
        """テキストを分析してPIIを検出"""
        try:
            results = self.analyzer.analyze(
                text=text,
                entities=self.entities,
                language=language
            )
            return results
        except Exception as e:
            print(f"  分析エラー: {e}")
            return []
    
    def scan_file(self, file_path: Path) -> Dict:
        """ファイルをスキャン"""
        content = self.read_file_safely(file_path)
        if not content:
            return None
        
        results = self.analyze_text(content)
        
        if results:
            findings = []
            for result in results:
                start = result.start
                end = result.end
                
                # 検出された文字列の前後を取得（コンテキスト）
                context_start = max(0, start - 30)
                context_end = min(len(content), end + 30)
                context = content[context_start:context_end]
                
                # 行番号を計算
                line_number = content[:start].count('\n') + 1
                
                findings.append({
                    'entity_type': result.entity_type,
                    'score': result.score,
                    'start': start,
                    'end': end,
                    'text': content[start:end],
                    'context': context.replace('\n', ' '),
                    'line_number': line_number
                })
            
            return {
                'file': str(file_path),
                'findings': findings
            }
        
        return None
    
    def scan_directory(self, root_dir: str) -> List[Dict]:
        """ディレクトリを再帰的にスキャン"""
        root_path = Path(root_dir)
        all_results = []
        
        print(f"スキャン開始: {root_dir}")
        print("-" * 80)
        
        scanned_count = 0
        skipped_count = 0
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file():
                if self.should_scan_file(file_path):
                    scanned_count += 1
                    print(f"スキャン中 ({scanned_count}): {file_path.relative_to(root_path)}")
                    
                    result = self.scan_file(file_path)
                    if result:
                        all_results.append(result)
                else:
                    skipped_count += 1
        
        print("-" * 80)
        print(f"スキャン完了: {scanned_count}ファイル処理, {skipped_count}ファイルスキップ")
        
        return all_results
    
    def generate_report(self, results: List[Dict], output_file: str = "pii_check_report.txt"):
        """レポートを生成"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("個人情報チェックレポート\n")
            f.write("=" * 80 + "\n\n")
            
            if not results:
                f.write("✓ 個人情報は検出されませんでした。\n")
                print("\n✓ 個人情報は検出されませんでした。")
                return
            
            # エンティティタイプごとに集計
            entity_stats = {}
            total_findings = 0
            
            for result in results:
                for finding in result['findings']:
                    entity_type = finding['entity_type']
                    entity_stats[entity_type] = entity_stats.get(entity_type, 0) + 1
                    total_findings += 1
            
            # サマリー
            f.write(f"検出された問題の総数: {total_findings}\n")
            f.write(f"問題のあるファイル数: {len(results)}\n\n")
            
            f.write("【検出されたエンティティタイプ】\n")
            entity_names = {
                'JP_MY_NUMBER': 'マイナンバー',
                'JP_PHONE_NUMBER': '電話番号',
                'JP_ADDRESS': '住所',
                'JP_PERSON_NAME': '氏名',
                'CREDIT_CARD': 'クレジットカード番号',
                'EMAIL_ADDRESS': 'メールアドレス',
                'US_SSN': '社会保障番号'
            }
            
            for entity_type, count in sorted(entity_stats.items(), key=lambda x: x[1], reverse=True):
                entity_name = entity_names.get(entity_type, entity_type)
                f.write(f"  - {entity_name} ({entity_type}): {count}件\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
            
            # 詳細結果
            for result in results:
                f.write(f"ファイル: {result['file']}\n")
                f.write("-" * 80 + "\n")
                
                for finding in result['findings']:
                    entity_name = entity_names.get(finding['entity_type'], finding['entity_type'])
                    f.write(f"\n  [{entity_name}] (信頼度: {finding['score']:.2f})\n")
                    f.write(f"  行番号: {finding['line_number']}\n")
                    f.write(f"  検出文字列: {finding['text']}\n")
                    f.write(f"  コンテキスト: ...{finding['context']}...\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"\nレポートを生成しました: {output_file}")
        print(f"検出された問題: {total_findings}件 ({len(results)}ファイル)")


def main():
    """メイン処理"""
    # 現在のディレクトリをスキャン
    current_dir = os.getcwd()
    
    print("個人情報チェッカー (Microsoft Presidio)")
    print("=" * 80)
    
    checker = PIIChecker()
    results = checker.scan_directory(current_dir)
    checker.generate_report(results)


if __name__ == "__main__":
    main()
