$jsonText = [Console]::In.ReadToEnd()
if (-not $jsonText.Trim()) { exit 0 }

$json = $jsonText | ConvertFrom-Json

$cwd         = if ($json.workspace.current_dir) { $json.workspace.current_dir } else { $json.cwd }
$model       = $json.model.display_name
$usedPct     = $json.context_window.used_percentage
$fiveHrPct   = $json.rate_limits.five_hour.used_percentage
$sevenDayPct = $json.rate_limits.seven_day.used_percentage

# Git branch
$gitBranch = ""
if ($cwd) {
    $null = git --no-optional-locks -C $cwd rev-parse --git-dir 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gitBranch = git --no-optional-locks -C $cwd -c core.hooksPath=NUL symbolic-ref --short HEAD 2>$null
        if (-not $gitBranch) {
            $gitBranch = git --no-optional-locks -C $cwd rev-parse --short HEAD 2>$null
        }
    }
}

$parts = @()

if ($model) { $parts += $model }
if ($cwd)   { $parts += (Split-Path -Leaf $cwd) }
if ($gitBranch) { $parts += $gitBranch }
# used_percentage が null の場合（コンパクト直後や応答待ちなど）のフォールバック
# session_id は英数字とハイフンだけ残し、TEMP 外のパスを作れないようにする
$sessionKey = "$($json.session_id)" -replace '[^A-Za-z0-9-]', ''
$cacheFile = $null
if ($sessionKey -and $env:TEMP) {
    try { $cacheFile = Join-Path $env:TEMP "claude-statusline-ctx-$sessionKey.txt" } catch {}
}
$ctxText = $null
if ($null -eq $usedPct) {
    $size = $json.context_window.context_window_size
    $tok  = $json.context_window.total_input_tokens
    # トークン数 0 も有効値として扱う（0% を表示する）。サイズ 0 は除算できないので除外
    if ($null -ne $tok -and $size -gt 0) { $usedPct = $tok * 100.0 / $size }
}
if ($null -ne $usedPct) {
    $ctxText = "ctx $([math]::Round($usedPct))%"
    if ($cacheFile) {
        try { Set-Content -LiteralPath $cacheFile -Value $ctxText -Encoding UTF8 -ErrorAction Stop } catch {}
    }
} elseif ($cacheFile -and (Test-Path -LiteralPath $cacheFile)) {
    # 直前の値を残す（~ は最新値でない印）。読めなければ黙って進む
    try { $ctxText = "~" + (Get-Content -LiteralPath $cacheFile -Raw -ErrorAction Stop).Trim() } catch {}
}
if ($ctxText) { $parts += $ctxText }
if ($null -ne $fiveHrPct)   { $parts += "5h $([math]::Round($fiveHrPct))%" }
if ($null -ne $sevenDayPct) { $parts += "7d $([math]::Round($sevenDayPct))%" }

[Console]::Write($parts -join " | ")
