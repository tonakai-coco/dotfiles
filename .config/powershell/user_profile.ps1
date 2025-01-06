if ($env:WT_PROFILE_ID -and $env:TERM_PROGRAM -ne 'vscode')
{
    # Windows Terminalから実行されたとき、かつvscodeのターミナル起動ではない場合にだけ変更する設定をここに記述する
    # Prompt
    # Set-PoshPrompt Paradox
    Import-Module posh-git
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\powerlevel10k_rainbow.omp.json" | Invoke-Expression
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\slimfat.omp.json" | Invoke-Expression
    # oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\gmay.omp.json" | Invoke-Expression
    oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\takuya.omp.json" | Invoke-Expression

    # 文字コードをUTF-8に変更
    chcp 65001

    # Icons
    Import-Module -Name Terminal-Icons
    #
    # Fzf
    Import-Module PSFzf
    Set-PsFzfOption -PSReadlineChordProvider 'Ctrl+f' -PSReadlineChordReverseHistory 'Ctrl+r'

}

# PSReadLine
Set-PSReadLineOption -EditMode Emacs
Set-PSReadLineOption -BellStyle None
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView

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
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($fullpath,'OnlyErrorDialogs','SendToRecycleBin')
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
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($fullpath,'OnlyErrorDialogs','SendToRecycleBin')
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

    # 圧縮処理
    Compress-Archive -Path $source -DestinationPath $destination
}

function unzip
{
    param (
        [string]$zipFile,
        [string]$destination = (Get-Location)
    )

    # 展開処理
    Expand-Archive -Path $zipFile -DestinationPath $destination
}

