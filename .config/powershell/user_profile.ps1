if ($env:TERM_PROGRAM -ne 'vscode')
{
    # Windows Terminalから実行されたとき、かつvscodeのターミナル起動ではない場合にだけ変更する設定をここに記述する
    # Prompt
    # Set-PoshPrompt Paradox
    # Import-Module posh-git
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\powerlevel10k_rainbow.omp.json" | Invoke-Expression
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\slimfat.omp.json" | Invoke-Expression
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\gmay.omp.json" | Invoke-Expression
    oh-my-posh init pwsh --config "C:\Tools\oh-my-posh-themes\takuya.omp.json" | Invoke-Expression

    # 文字コードをUTF-8に変更
    chcp 65001
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    # Icons
    Import-Module -Name Terminal-Icons
    #
    # Fzf
    # Import-Module PSFzf
    # Set-PsFzfOption -PSReadlineChordProvider 'Ctrl+f' -PSReadlineChordReverseHistory 'Ctrl+r'

}

# zoxide
Invoke-Expression (& { (zoxide init powershell | Out-String) })

# mise
mise activate pwsh | Out-String | Invoke-Expression

# PSReadLine
Set-PSReadLineOption -EditMode Emacs
Set-PSReadLineOption -BellStyle None
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView

# carapace
$env:CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense' # optional
Set-PSReadLineOption -Colors @{ "Selection" = "`e[7m" }
Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
carapace _carapace | Out-String | Invoke-Expression

# Alias
Set-Alias vim nvim
Set-Alias ll ls
Set-Alias grep findstr
Set-Alias fb fzf-bat
Set-Alias tig 'C:\Program Files\Git\usr\bin\tig.exe'
Set-Alias less 'C:\Program Files\Git\usr\bin\less.exe'
Set-Alias gs git-status
Set-Alias rm File-ToRecycleBin
Set-Alias rmdir Folder-ToRecycleBin
Set-Alias watch Watch-Command
New-Alias -Name "dirsize" -Value Get-FolderSize
New-Alias -Name "convutf8" -Value Convert-ToUtf8FromShiftJis

# Function
function which ($command)
{
    Get-Command -Name $command -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue
}

function fzf-bat
{
    fzf --reverse --inline-info --ansi --preview "bat --color=always --style=header,grid --line-range :100 {}"
}

function pwdc
{
    pwd | Set-Clipboard
}

function opex
{
    param([string]$path = ".")
    Invoke-Item -Path $path
}

function pathc ($path)
{
    Get-Item $path | Select-Object -ExpandProperty FullName | Set-Clipboard
}

function merge ($path1, $path2)
{
    & "C:\Program Files\Araxis\Araxis Merge\Merge.exe" $path1 $path2
}

function treec
{
    tree /f | Set-Clipboard
}

function touch ($name)
{
    New-Item -ItemType File $name
}

function ..
{
    cd ..
}

function ...
{
    cd ..\..
}

function ....
{
    cd ..\..\..
}

function git-status
{
    git status
}

function File-ToRecycleBin($target_file_path)
{
    if ((Test-Path $target_file_path) -And ((Test-Path -PathType Leaf (Get-Item $target_file_path))))
    {
        $fullpath = (Get-Item $target_file_path).FullName
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($fullpath, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } else
    {
        Write-Output "'$target_file_path' is not file or not found."
    }
}

function Folder-ToRecycleBin($target_dir_path)
{
    if ((Test-Path $target_dir_path) -And ((Test-Path -PathType Container (Get-Item $target_dir_path))))
    {
        $fullpath = (Get-Item $target_dir_path).FullName
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($fullpath, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } else
    {
        Write-Output "'$target_dir_path' is not directory or not found."
    }
}

# Watch-Command 'echo "test"' 5のように実行すると、echo "test"を5秒ごとに実行する
function Watch-Command($command, $interval = 1)
{
    while ($true)
    {
        Invoke-Expression $command; Start-Sleep -Seconds $interval
    }
}

function zip
{
    param (
        [string]$destination,
        [string]$source
    )

    # 圧縮処理 (7-Zip)
    $sevenZip = 'C:\Program Files\7-Zip\7z.exe'
    if (!(Test-Path $sevenZip))
    {
        Write-Error "7z.exeが見つかりません: $sevenZip"
        return
    }
    # クォートでパスのスペース対応
    $quotedDest = '"' + $destination + '"'
    $quotedSrc = '"' + $source + '"'
    $cmd = "$sevenZip a $quotedDest $quotedSrc"
    $proc = Start-Process -FilePath $sevenZip -ArgumentList @('a', $destination, $source) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0)
    {
        Write-Error "7z.exeによる圧縮に失敗しました (ExitCode: $($proc.ExitCode))"
    }
}

function unzip
{
    param (
        [string]$zipFile,
        [string]$destination = (Get-Location)
    )

    # 展開処理 (7-Zip)
    $sevenZip = 'C:\Program Files\7-Zip\7z.exe'
    if (!(Test-Path $sevenZip))
    {
        Write-Error "7z.exeが見つかりません: $sevenZip"
        return
    }
    $oArg = "-o$destination"
    $proc = Start-Process -FilePath $sevenZip -ArgumentList @('x', $zipFile, $oArg, '-y') -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0)
    {
        Write-Error "7z.exeによる展開に失敗しました (ExitCode: $($proc.ExitCode))"
    }
}

function Get-FolderSize
{
    param([string]$Path)
    $folder = Get-ChildItem -Path $Path -Recurse | Measure-Object -Property Length -Sum
    $size = $folder.Sum / 1MB
    Write-Host ("{0:N2} MB" -f $size)

}

function Convert-ToUtf8FromShiftJis
{
    param (
        [string]$inputFile
    )

    $ext = [System.IO.Path]::GetExtension($inputFile)
    $outputFile = [System.IO.Path]::GetFileNameWithoutExtension($inputFile) + "_utf8" + $ext
    Get-Content -Encoding shift-jis $inputFile | Out-File -Encoding utf-8 $outputFile
}

function lsn
{
    $files = Get-ChildItem | ForEach-Object { $_.Name }
    $files -join "`t"
}

# yaziコマンドのラッパー関数
function y
{
    $tmp = (New-TemporaryFile).FullName
    yazi $args --cwd-file="$tmp"
    $cwd = Get-Content -Path $tmp -Encoding UTF8
    if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path)
    {
        Set-Location -LiteralPath (Resolve-Path -LiteralPath $cwd).Path
    }
    Remove-Item -Path $tmp
}

function wc
{
    $input | Measure-Object -Line -Word -Character
}
