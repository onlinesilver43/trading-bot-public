# Trading Bot Interaction Guide

## 🚀 Quick Start Commands

### Check System Status
```bash
# Check running containers
sshpass -f ~/.ssh/tb_pw ssh tb "docker ps"

# Check system health
curl http://127.0.0.1:8080/api/system/health

# Check bot status
curl http://127.0.0.1:8080/api/state
```

### Data Collection Status
```bash
# Check current data collection
sshpass -f ~/.ssh/tb_pw ssh tb "cat /srv/trading-bots/history/manifest.json | jq '.statistics'"

# List collected files
sshpass -f ~/.ssh/tb_pw ssh tb "ls -la /srv/trading-bots/history/parquet/"
```

### Run Data Collection Script
```bash
# Run comprehensive data collection
python3 scripts/collect_historical_data.py
```

## 📊 Expected Data Collection Results

### Target Data Collection
- **BTCUSDT 1h**: ~67 files (2020-2025)
- **BTCUSDT 5m**: ~67 files (2020-2025) 
- **ETHUSDT 1h**: ~67 files (2020-2025)
- **ETHUSDT 5m**: ~67 files (2020-2025)
- **Total**: ~268 files, ~100+ MB

### Current Status (August 29, 2025)
- ✅ History fetcher URL issue RESOLVED
- ✅ Volume mount issue RESOLVED - Docker container path conflict fixed
- ✅ BTCUSDT 1h: 67 files collected (complete)
- 🔄 ETHUSDT 1h: Pending collection
- 🔄 BTCUSDT 5m: Pending collection
- 🔄 ETHUSDT 5m: Pending collection

## 🔧 Common Issues & Solutions

### Manifest Not Updating
The manifest.json file needs to be updated after each collection. The script handles this automatically.

### Parquet Conversion Errors
Some recent files (2025) may have timestamp conversion issues. This is normal and doesn't affect older data.

### 404 Errors for Recent Data
Recent months (2025-08) may not be available yet. This is expected behavior.

### File Storage Verification
After data collection, verify that files are properly stored and accessible:
```bash
# Check file count
sshpass -f ~/.ssh/tb_pw ssh tb "find /srv/trading-bots/history/parquet/ -name '*.parquet' | wc -l"

# Check file sizes
sshpass -f ~/.ssh/tb_pw ssh tb "du -sh /srv/trading-bots/history/parquet/*"
```

## 🎯 Next Steps After Data Collection - VOLUME MOUNT ISSUE RESOLVED

1. **Complete Remaining Data Collection** - Finish ETHUSDT 1h, BTCUSDT 5m, ETHUSDT 5m
2. **Test Phase 4 Components** with real data
3. **Run Historical Analysis Bot** with collected data
4. **Begin Strategy Discovery** with real market patterns
5. **Test Master Agent** strategy selection

## 📋 Script Usage

```bash
# Run full data collection
python3 scripts/collect_historical_data.py

# Check status only
python3 scripts/collect_historical_data.py --status

# Collect specific symbol/interval
python3 scripts/collect_historical_data.py --symbol BTCUSDT --interval 1h
```

## 🚨 Critical Notes

- **Always use the script** instead of manual commands
- **Check manifest.json** for accurate file counts
- **Parquet files** are the primary data format
- **CSV files** are intermediate format only
- **Volume mount** must be `/srv/trading-bots/history:/app/history`
- **Volume mount issue RESOLVED** - Docker container path conflict fixed
- **File storage VERIFIED** - Data properly accessible on host system
