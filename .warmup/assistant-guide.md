# Assistant Guide - Trading Bot Repository

## Repository Overview
- **Type**: Trading bot with BTC/ETH bots + FastAPI UI
- **Deployment**: GitHub Actions → DigitalOcean droplet
- **Environment**: WSL-friendly, uses GitHub CLI and SSH

## Deployment Method
**Standard deployment workflow:**
1. Create deploy tag: `TAG="deploy-$(date -u +%Y%m%d-%H%M)-$(git rev-parse --short HEAD)"`
2. Push tag: `git tag -a "$TAG" -m "Deploy" && git push origin "$TAG"`
3. Trigger workflow: `gh workflow run "Deploy to Droplet" --ref "$TAG"`
4. Watch deployment: `gh run watch --exit-status`
5. Verify: SSH to droplet and check docker ps + /api/state

**Full deployment script:**
```bash
#!/bin/bash
set -euo pipefail

echo "[1] Creating deploy tag..."
SHA=$(git rev-parse --short HEAD)
TAG="deploy-$(date -u +%Y%m%d-%H%M)-$SHA"
git tag -a "$TAG" -m "Manual deployment trigger"
git push origin "$TAG"

echo "[2] Triggering deploy workflow..."
gh workflow run "Deploy to Droplet" --ref "$TAG"

echo "[3] Watching deployment..."
gh run watch --exit-status

echo "[4] Verifying deployment..."
sshpass -f ~/.ssh/tb_pw ssh -o StrictHostKeyChecking=no tb "
  echo '--- docker ps ---'
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
  echo '--- /api/state ---'
  curl -sS http://127.0.0.1:8080/api/state | jq '.state | {profile,timeframe,last_action,last_signal,cash_usd,stash_coin_units,equity_usd,skip_reason}' || true
"

echo "[done] Deployed and verified $TAG"
```

## Git Workflows
- **Branch strategy**: Feature branches → main → auto-deploy
- **Tagging**: Timestamp-based deploy tags (deploy-YYYYMMDD-HHMM-SHA)
- **Workflows**: 
  - `deploy.yml` - Main deployment to droplet
  - `ci.yml` - CI checks
  - `rollback.yml` - Rollback capability

## Key Commands
- **SSH to droplet**: `sshpass -f ~/.ssh/tb_pw ssh tb`
- **Check containers**: `docker ps` on droplet
- **Check bot state**: `curl http://127.0.0.1:8080/api/state` on droplet
- **GitHub CLI**: Use `gh` for workflow management

## User Preferences
- **Commands**: Run directly without asking for approval
- **WSL**: All commands should be WSL-friendly
- **Automation**: Prefer automated scripts over manual steps
- **Verification**: Always verify deployments with status checks

## Current Status
- **Phase**: Phase 1 live (BTC bot + UI via CI)
- **Next**: Add second paper bot (ETH/USD 5m), confirm auto-deploy, add UI pair display
- **Infrastructure**: DO droplet, Docker Compose, GitHub Actions

## Notes
- Repository has many deployment tags (deploy-YYYYMMDD-HHMM-SHA format)
- Working directory is clean, usually on main branch
- Uses SSH with password file for droplet access
- Prefers comprehensive solutions over quick fixes

