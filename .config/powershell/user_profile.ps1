# Prompt
Import-Module posh-git
# Set-PoshPrompt Paradox
if ($env:WT_PROFILE_ID) {
    # Windows Terminalから実行されたときだけ変更する設定をここに記述する
    oh-my-posh init pwsh --config "$env:POSH_THEMES_PATH\powerlevel10k_rainbow.omp.json" | Invoke-Expression
}

# 文字コードをUTF-8に変更
chcp 65001

# Icons
Import-Module -Name Terminal-Icons

# PSReadLine
Set-PSReadLineOption -EditMode Emacs
Set-PSReadLineOption -BellStyle None
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView

# Fzf
Import-Module PSFzf
Set-PsFzfOption -PSReadlineChordProvider 'Ctrl+f' -PSReadlineChordReverseHistory 'Ctrl+r'

# Alias
Set-Alias vim nvim
Set-Alias ll ls
Set-Alias grep findstr
Set-Alias fb fzf-bat
Set-Alias tig 'C:\Program Files\Git\usr\bin\tig.exe'
Set-Alias less 'C:\Program Files\Git\usr\bin\less.exe'

# Function
function which ($command) {
  Get-Command -Name $command -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue
}

function fzf-bat {
  fzf --reverse --inline-info --ansi --preview "bat --color=always --style=header,grid --line-range :100 {}"
}

function pwdc {
  pwd | Set-Clipboard
}

function opex {
  param([string]$path = ".")
  Invoke-Item -Path $path
}

function pathc ($path) {
  Get-Item $path | Select-Object -ExpandProperty FullName | Set-Clipboard
}

function merge ($path1, $path2) {
    & "C:\Program Files\Araxis\Araxis Merge\Merge.exe" $path1 $path2
}

function treec {
   tree /f | Set-Clipboard
}

function touch ($name) {
    New-Item -ItemType File $name
}
