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
    $null = git -C $cwd rev-parse --git-dir 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gitBranch = git -C $cwd -c core.hooksPath=NUL symbolic-ref --short HEAD 2>$null
        if (-not $gitBranch) {
            $gitBranch = git -C $cwd rev-parse --short HEAD 2>$null
        }
    }
}

$parts = @()

# Current directory (substitute USERPROFILE with ~)
if ($cwd) {
    $homeDir = $env:USERPROFILE
    if ($cwd.StartsWith($homeDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        $displayDir = "~" + $cwd.Substring($homeDir.Length)
    } else {
        $displayDir = $cwd
    }
    $parts += $displayDir
}

if ($gitBranch)          { $parts += $gitBranch }
if ($model)              { $parts += $model }
if ($null -ne $usedPct)     { $parts += "ctx:$([math]::Round($usedPct))%" }
if ($null -ne $fiveHrPct)   { $parts += "5h:$([math]::Round($fiveHrPct))%" }
if ($null -ne $sevenDayPct) { $parts += "7d:$([math]::Round($sevenDayPct))%" }

[Console]::Write($parts -join "  ")
