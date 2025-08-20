#!/usr/bin/env bash
set -e
PLAN=".warmup/plan.md"
cmd="${1:-show}"; shift || true
case "$cmd" in
  show)   cat "$PLAN";;
  next)   awk '/^- \[ \] /{sub(/^- \[ \] /,"");print;exit}' "$PLAN" || echo "(no pending steps)";;
  done)
    # mark first unchecked as done
    ln=$(awk 'BEGIN{n=0}/^- \[ \] /{n=NR;print n;exit}' "$PLAN")
    [ -n "$ln" ] && sed -i "${ln}s/^- \[ \] /- [x] /" "$PLAN" || echo "No unchecked steps."
    ;;
  add)    [ -n "$1" ] || { echo "Usage: bash scripts/plan.sh add \"Step text\""; exit 1; }
          echo "- [ ] $1" >> "$PLAN";;
  reset)  sed -i 's/^- \[x\] /- [ ] /' "$PLAN";;
  *)      echo "Usage: bash scripts/plan.sh {show|next|done|add|reset}"; exit 1;;
esac
