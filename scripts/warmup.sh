#!/usr/bin/env bash
set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ORIGIN="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
HASH="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo '—')"
GOAL="$(sed -n '1p' "$REPO_DIR/.warmup/goal.txt" 2>/dev/null || echo '(none set)')"

# Plan summary
DONE_CNT="$(grep -c '^- \[x\] ' "$REPO_DIR/.warmup/plan.md" 2>/dev/null || echo 0)"
TOT_CNT="$(grep -c '^- \['   "$REPO_DIR/.warmup/plan.md" 2>/dev/null || echo 0)"
NEXT_STEP="$(awk '/^- \[ \] /{sub(/^- \[ \] /,"");print;exit}' "$REPO_DIR/.warmup/plan.md" 2>/dev/null || echo '(no pending steps)')"
BACKLOG="$(awk '/^- \[ \] /{sub(/^- \[ \] /,"");print;cnt++; if(cnt==3) exit}' "$REPO_DIR/.warmup/plan.md" 2>/dev/null)"

echo "### TRADING BOTS — WARMUP CONTEXT ###"
echo "Goal today: $GOAL"
echo
echo "Repo: ${ORIGIN:-unknown} @ ${HASH}"
echo "Params (compose):"
if [ -f "$REPO_DIR/compose/docker-compose.yml" ]; then
  grep -E 'EXCHANGE:|SYMBOL:|TIMEFRAME:|ORDER_SIZE_USD' "$REPO_DIR/compose/docker-compose.yml" | sed 's/^[[:space:]]*/  /'
else
  echo "  (compose not found)"
fi
echo
echo "Plan: $DONE_CNT/$TOT_CNT done"
echo "Next: $NEXT_STEP"
[ -n "$BACKLOG" ] && { echo "Backlog:"; echo "$BACKLOG" | sed 's/^/  - /'; }
echo
echo "Server snapshot:"
sshpass -f ~/.ssh/tb_pw ssh tb '
  set -e
  OS="$( (lsb_release -ds 2>/dev/null) || (. /etc/os-release; echo $PRETTY_NAME) )"
  IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '"'"'{for(i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}'"'"')"
  [ -n "$IP" ] || IP="$(hostname -I | awk '"'"'{print $1}'"'"')"
  [ -n "$IP" ] || IP="$(curl -s ifconfig.me || true)"
  echo "  Host:" $(hostname) "|" "$OS" "| kernel" $(uname -r)
  echo "  Docker:" $(docker --version | cut -d, -f1) "| Compose" "$(docker compose version | head -1)"
  echo "  UI:    http://$IP:8080"
  echo "  Containers:"
  docker ps --format "    - {{.Names}} => {{.Image}} ({{.Status}})" || true
  echo "  State tail:"
  tail -n 5 /srv/trading-bots/data/paper_state.json 2>/dev/null || echo "    (no state yet)"
'
echo "### END WARMUP ###"
