# Trading Bots – Plan

- [x] Create DO droplet (Ubuntu 25.04) and connect from WSL (sshpass alias: tb)
- [x] Install Docker + Compose; create /srv/trading-bots; add swap
- [x] Build paper SMA bot + FastAPI UI; run via Compose
- [x] Create GitHub repo (onlinesilver43/trading-bot) + CI/CD (GitHub Actions → SCP)
- [x] Switch to binanceus; inject API keys via GH Secrets → droplet .env
- [ ] Add second bot: ETH/USD, TIMEFRAME=5m (own service)
- [ ] UI: show current pair/timeframe + multi-bot status (BTC & ETH)
- [ ] Optional: domain + reverse proxy later
