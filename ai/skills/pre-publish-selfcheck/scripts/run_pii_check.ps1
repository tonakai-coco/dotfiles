# 個人情報チェックツール実行スクリプト
# 使用方法: .\run_pii_check.ps1

param(
    [switch]$Install,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "個人情報チェックツール" -ForegroundColor Cyan
    Write-Host "=" * 70
    Write-Host ""
    Write-Host "使用方法:" -ForegroundColor Yellow
    Write-Host "  .\run_pii_check.ps1           - チェックを実行"
    Write-Host "  .\run_pii_check.ps1 -Install  - 必要なパッケージをインストール"
    Write-Host "  .\run_pii_check.ps1 -Help     - このヘルプを表示"
    Write-Host ""
    Write-Host "出力:" -ForegroundColor Yellow
    Write-Host "  pii_check_report.txt - 検出結果レポート"
    Write-Host ""
}

function Get-PythonExe {
    # .venv が存在すればそちらを優先
    if (Test-Path ".\.venv\Scripts\python.exe") {
        return ".\.venv\Scripts\python.exe"
    }
    return "python"
}

function Test-Python {
    $pyExe = Get-PythonExe
    try {
        $pythonVersion = & $pyExe --version 2>&1
        Write-Host "✓ Python検出: $pythonVersion ($pyExe)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Pythonが見つかりません" -ForegroundColor Red
        Write-Host "  Python 3.7以上をインストールするか、.venv を作成してください" -ForegroundColor Yellow
        return $false
    }
}

function Install-Requirements {
    Write-Host "`n必要なパッケージをインストールしています..." -ForegroundColor Cyan
    
    if (-not (Test-Python)) {
        exit 1
    }
    
    if (Test-Path "$script:scriptDir\pii_requirements.txt") {
        Write-Host "pip install -r pii_requirements.txt を実行中..." -ForegroundColor Yellow
        $pyExe = Get-PythonExe
        & $pyExe -m pip install -r "$script:scriptDir\pii_requirements.txt"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ パッケージインストール完了" -ForegroundColor Green
            
            # spaCy日本語モデルのインストール
            Write-Host "`nspaCy日本語モデルをダウンロード中..." -ForegroundColor Yellow
            & $pyExe -m spacy download ja_core_news_sm
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ 日本語モデルのインストール完了" -ForegroundColor Green
            }
            else {
                Write-Host "⚠ 日本語モデルのインストールに失敗しましたが、基本機能は動作します" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "✗ インストール失敗" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "✗ pii_requirements.txt が見つかりません: $script:scriptDir\pii_requirements.txt" -ForegroundColor Red
        exit 1
    }
}

function Run-PIICheck {
    Write-Host "`n個人情報チェックを実行しています..." -ForegroundColor Cyan
    Write-Host "=" * 70
    
    if (-not (Test-Python)) {
        exit 1
    }
    
    if (-not (Test-Path "$script:scriptDir\pii_checker.py")) {
        Write-Host "✗ pii_checker.py が見つかりません: $script:scriptDir\pii_checker.py" -ForegroundColor Red
        exit 1
    }
    
    # チェック実行
    $pyExe = Get-PythonExe
    $env:PYTHONUTF8 = "1"
    & $pyExe "$script:scriptDir\pii_checker.py"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n" + "=" * 70
        Write-Host "✓ チェック完了" -ForegroundColor Green
        
        if (Test-Path "pii_check_report.txt") {
            Write-Host "`nレポートが生成されました: pii_check_report.txt" -ForegroundColor Cyan
            
            # レポートの先頭を表示
            Write-Host "`n--- レポート概要 ---" -ForegroundColor Yellow
            Get-Content "pii_check_report.txt" -Head 20 -Encoding UTF8
            Write-Host "..." -ForegroundColor Gray
            Write-Host "`n詳細は pii_check_report.txt を参照してください" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "`n✗ エラーが発生しました" -ForegroundColor Red
        Write-Host "詳細は上記のエラーメッセージを確認してください" -ForegroundColor Yellow
        exit 1
    }
}

# メイン処理
Clear-Host

# このスクリプト自身のディレクトリを保存（pii_checker.py などの参照に使用）
$script:scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Help) {
    Show-Help
    exit 0
}

if ($Install) {
    Install-Requirements
    exit 0
}

# デフォルト動作: チェック実行
Write-Host "個人情報チェックツール" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host "作業ディレクトリ: $(Get-Location)" -ForegroundColor Gray

Run-PIICheck

Write-Host "`n完了しました。" -ForegroundColor Green
