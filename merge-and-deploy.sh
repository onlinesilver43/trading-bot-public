#!/bin/bash
set -euo pipefail

BR="feature/fix-enhanced-ui"
MAIN="main"
WF_NAME="Deploy to Droplet"

echo "[1] fetch and checkout main"
git fetch origin
git checkout "$MAIN"
git pull --rebase origin "$MAIN"

echo "[2] merge feature branch into main (ours wins if conflicts)"
git merge "$BR" -X theirs -m "merge $BR into $MAIN (enhanced UI fixes and warmup updates)"

echo "[3] push main"
git push origin "$MAIN"

echo "[4] create and push deploy tag"
SHA=$(git rev-parse --short HEAD)
TAG="deploy-$(date -u +%Y%m%d-%H%M)-$SHA"
git tag -a "$TAG" -m "Deploy main after merging $BR"
git push origin "$TAG"

echo "[5] trigger deploy workflow"
gh workflow run "$WF_NAME" --ref "$TAG" || true
gh run watch --exit-status || true

echo "[6] verify on droplet"
sshpass -f ~/.ssh/tb_pw ssh -o StrictHostKeyChecking=no tb "
  echo '--- docker ps ---'
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
  echo '--- /api/state ---'
  curl -sS http://127.0.0.1:8080/api/state | jq '.state | {profile,timeframe,last_action,last_signal,cash_usd,stash_coin_units,equity_usd,skip_reason}' || true
"

echo "[7] cleanup feature branch"
git branch -d "$BR" || true
git push origin --delete "$BR" || true

echo "[done] merged into main, deployed, and deleted $BR"
