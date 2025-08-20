#!/usr/bin/env bash
set -e
[ -n "$1" ] || { echo "Usage: bash scripts/goal.sh \"Goal text\" [--push]"; exit 1; }
GOAL="$1"; PUSH="${2:-}"
mkdir -p .warmup
printf "%s\n" "$GOAL" > .warmup/goal.txt
if [ "$PUSH" = "--push" ]; then
  git add .warmup/goal.txt && git commit -m "warmup goal: $GOAL" && git push
fi
echo "Goal set."
