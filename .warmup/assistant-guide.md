# Assistant Guide - Trading Bot Repository

## Repository Overview
- **Type**: Trading bot with BTC/ETH bots + FastAPI UI
- **Deployment**: GitHub Actions → DigitalOcean droplet
- **Environment**: WSL-friendly, uses GitHub CLI and SSH

## **NEW: Strategic Direction - Self-Funding Unlimited Scaling**

### **Current Goal**: Build self-funding, unlimited scaling trading system
- **Target**: $1K → $50K+ in 1 year through multi-bot, multi-coin trading
- **Strategy**: Get profitable from day 1, self-fund development
- **Timeline**: 1-week sprint to complete system, 4 weeks to self-funding

### **Self-Funding Development Strategy**
1. **Week 1**: Generate $200+ profit to fund development
2. **Week 2**: Use profits to build full multi-bot system  
3. **Week 3**: Complete AI agent, achieve self-funding
4. **Week 4+**: Unlimited scaling begins

### **Multi-Bot Architecture**
- **Bot 1**: Core Strategy Bot (enhanced current bot) - 30% capital
- **Bot 2**: Scalping Bot (high-frequency) - 25% capital
- **Bot 3**: Momentum Bot (trend following) - 25% capital
- **Bot 4**: Arbitrage Bot (cross-exchange) - 15% capital
- **Bot 5**: Hedging Bot (risk management) - 5% capital

### **AI Agent Integration**
- **Market Analysis**: Real-time condition monitoring
- **Strategy Selection**: Dynamic strategy switching
- **Bot Orchestration**: Coordinate all 5 bots simultaneously
- **Risk Management**: Portfolio-level risk control

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
  - **NEW**: `history-fetch.yml` - Historical data collection for strategy backtesting

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
- **Branch Workflow**: NEVER merge to main without explicit approval
- **Deployment Strategy**: Always tag and deploy from feature branches first
- **Testing**: Test branches with deployments before merging to main

## Current Status
- **Phase**: Building self-funding, unlimited scaling system
- **Goal**: $1K → $50K+ in 1 year through multi-bot, multi-coin trading
- **Timeline**: 1-week sprint to complete system, 4 weeks to self-funding
- **Infrastructure**: DO droplet, Docker Compose, GitHub Actions

## Notes
- Repository has many deployment tags (deploy-YYYYMMDD-HHMM-SHA format)
- Working directory is clean, usually on main branch
- Uses SSH with password file for droplet access
- Prefers comprehensive solutions over quick fixes
- **NEW**: Focus on immediate profitability and self-funding development

