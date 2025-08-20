#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ORIGIN="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
REPO_SLUG="$(echo "$ORIGIN" | sed -n 's#.*github.com[:/]\([^/][^/]*\)/\([^/.][^/]*\)\(\.git\)\?$#\1/\2#p')"

echo "### TRADING BOTS — WARMUP CONTEXT ###"
echo "Goal today: $(sed -n '1p' "$REPO_DIR/.warmup/goal.txt" 2>/dev/null || echo '')"
echo
echo "Repo: ${ORIGIN:-unknown} @ $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo '—')"
echo "Params (compose):"
grep -E 'EXCHANGE:|SYMBOL:|TIMEFRAME:|ORDER_SIZE_USD' "$REPO_DIR/compose/docker-compose.yml" | sed 's/^[[:space:]]*//' || echo "  (compose not found)"

echo
if command -v gh >/dev/null 2>&1 && [ -n "$REPO_SLUG" ]; then
  echo "Last deploy (GitHub Actions):"
  gh run list --repo "$REPO_SLUG" --limit 1 || echo "  (no runs yet)"
else
  echo "Last deploy (GitHub Actions): gh CLI not available or repo unknown"
fi

echo
echo "Recent commits:"
git -C "$REPO_DIR" log --oneline -n 3 2>/dev/null || echo "  (no commits)"

echo
echo "Notes (top):"
awk 'NR<=20{print} NR==21{print "..."; exit}' "$REPO_DIR/WARMUP_NOTES.md" 2>/dev/null || echo "  (no notes)"

echo
# Server snapshot
echo "Server snapshot:"
sshpass -f ~/.ssh/tb_pw ssh tb '
  set -e
  OS="$( (lsb_release -ds 2>/dev/null) || (. /etc/os-release; echo $PRETTY_NAME) )"
  IP="$(hostname -I | awk "{print \$1}")"
  echo "  Host:" $(hostname) "|" "$OS" "| kernel" $(uname -r)
  echo "  Docker:" $(docker --version | cut -d, -f1) "| Compose" "$(docker compose version | head -1)"
  echo "  UI:    http://'$IP':8080"
  echo "  Containers:"
  docker ps --format "    - {{.Names}} => {{.Image}} ({{.Status}})" || true
  echo "  State tail:"
  tail -n 5 /srv/trading-bots/data/paper_state.json 2>/dev/null || echo "    (no state yet)"
'
echo "### END WARMUP ###"
