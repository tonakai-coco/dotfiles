#!/bin/sh
input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
five_hour_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
seven_day_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

# Git branch (skip optional locks to avoid contention)
git_branch=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
  git_branch=$(git -C "$cwd" -c core.hooksPath=/dev/null symbolic-ref --short HEAD 2>/dev/null \
    || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
fi

# Build status line parts
parts=""

# Current directory (show home as ~)
if [ -n "$cwd" ]; then
  home="$HOME"
  display_dir="${cwd#$home}"
  if [ "$display_dir" != "$cwd" ]; then
    display_dir="~$display_dir"
  fi
  parts="$display_dir"
fi

# Git branch
if [ -n "$git_branch" ]; then
  parts="$parts  $git_branch"
fi

# Model name
if [ -n "$model" ]; then
  parts="$parts  $model"
fi

# Context window usage
if [ -n "$used_pct" ]; then
  used_fmt=$(printf "%.0f" "$used_pct")
  parts="$parts  ctx:${used_fmt}%"
fi

# 5-hour rate limit usage (only shown when available, i.e. after first API response)
if [ -n "$five_hour_pct" ]; then
  five_fmt=$(printf "%.0f" "$five_hour_pct")
  parts="$parts  5h:${five_fmt}%"
fi

# 7-day rate limit usage (only shown when available)
if [ -n "$seven_day_pct" ]; then
  seven_fmt=$(printf "%.0f" "$seven_day_pct")
  parts="$parts  7d:${seven_fmt}%"
fi

printf "%s" "$parts"
