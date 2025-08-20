#!/usr/bin/env bash
set -e
[ -n "$1" ] || { echo "Usage: bash scripts/note.sh \"your note\" [--push]"; exit 1; }
NOTE="$1"; PUSH="$2"
STAMP="$(date -u +'%Y-%m-%d %H:%M:%SZ')"
echo "- [$STAMP] $NOTE" >> WARMUP_NOTES.md
if [ "$PUSH" = "--push" ]; then
  git add WARMUP_NOTES.md && git commit -m "warmup note: $NOTE" && git push
fi
echo "Added note."
