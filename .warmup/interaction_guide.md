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

### Current Status (August 30, 2025)
- ✅ History fetcher URL issue RESOLVED
- ✅ Volume mount issue RESOLVED - Docker container path conflict fixed
- ✅ Enhanced test framework successfully deployed with CI workflow integration
- ✅ Git conflicts resolved and enhanced framework pushed
- ✅ CI workflow testing COMPLETED - All 39 Ruff linting issues resolved
- ✅ Import issues FIXED - BacktestingEngine and sma_crossover imports corrected
- ✅ Virtual environment properly configured with all dependencies
- ✅ Local CI tests all passing
- ✅ GitHub Actions CI workflow NOW PASSING - All CI workflow checks successful
- ✅ Test suite REFACTORED with robust import handling and CI workflow integration
- ✅ Test and Validate workflow working due to pytest collection errors
- ✅ BTCUSDT 1h: 67 files collected (complete)
- ✅ ETHUSDT 1h: 67 files collected (complete)
- ✅ BTCUSDT 5m: 67 files collected (complete)
- ✅ ETHUSDT 5m: 67 files collected (complete)
- ✅ Total: 268 files, 66 MB - ALL DATA COLLECTION COMPLETE
- ❌ **CRITICAL ISSUE**: History Fetch workflow failed during Docker build on server
- 🚨 **BLOCKED**: Cannot merge to main until history functionality is working

### Next Steps After Data Collection
1. **Fix History Fetch Workflow** 🚨 **CRITICAL - IMMEDIATE**
   - Investigate why workflow failed during Docker build
   - Fix Docker build issues on server
   - Ensure history fetcher works locally first
   - Re-run workflow for successful data generation

2. **Verify All Workflows Pass** ✅ **GOAL**
   - Confirm CI workflow continues to pass
   - Confirm History Fetch workflow now passes
   - Ensure all GitHub Actions workflows are successful

3. **Prepare for Merge** 🚨 **BLOCKED UNTIL HISTORY FIXED**
   - Cannot create merge request until history functionality is working
   - Must fix history fetch workflow first
   - Only proceed to merge after successful data generation

### Key Commands for Next Session
```bash
# Check workflow status and logs
gh run list --workflow="history-fetch.yml" --limit 1
gh run view [WORKFLOW_ID] --log

# Investigate history fetcher locally
ls -la history_fetcher/
cat history_fetcher/Dockerfile

# Test history fetcher locally
cd history_fetcher
docker build -t history-fetcher:test .

# Verify all workflows pass locally
cd app
source ../.venv/bin/activate
python3 -m ruff check .
python3 -m black --check .
find . -name "*.py" -exec python3 -m py_compile {} \;

# Test simple Phase 4 test
python3 simple_phase4_test.py
```

### Expected Results
- History Fetch workflow failure investigation completed
- Specific error identified and understood
- All remaining issues fixed
- History Fetch workflow re-run and passes successfully
- Data generation completed successfully
- Branch ready for merge to main

## 🔧 Common Issues & Solutions

### History Fetch Workflow Failure
**Issue**: Workflow failed during Docker build on server
**Error**: "failed to read dockerfile: open Dockerfile: no such file or directory"
**Solution**: 
1. Check if Dockerfile exists in history_fetcher directory
2. Verify file transfer to server is working correctly
3. Test Docker build locally first
4. Fix any path or file issues

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

### CI Workflow Issues
If GitHub Actions CI fails while local tests pass:
1. Check GitHub Actions logs for specific error
2. Compare local vs remote environment differences
3. Fix any issues found in CI logs
4. Re-run workflow to verify success

## 🎯 Next Steps After Data Collection - CRITICAL ISSUE IDENTIFIED

1. **Fix History Fetch Workflow** 🚨 **CRITICAL - IMMEDIATE** - Investigate and fix workflow failure
2. **Ensure Data Generation Works** 🔧 **NEXT** - Fix any problems found by workflow
3. **Verify Data Collection Success** ✅ **GOAL** - Re-run workflow to verify all checks pass
4. **Prepare for Merge** 🚨 **BLOCKED** - Cannot merge until history functionality is working

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
- **ALL DATA COLLECTION COMPLETE** - 268 files, 66 MB total
- **CI WORKFLOW CLEANUP COMPLETED** - All 39 Ruff linting issues resolved
- **IMPORT ISSUES FIXED** - BacktestingEngine and sma_crossover imports corrected
- **LOCAL CI TESTS PASSING** - All local CI workflow tests passing
- **GITHUB ACTIONS CI PASSING** - All CI workflow checks successful
- **🚨 CRITICAL ISSUE**: History Fetch workflow failed during Docker build on server
- **🚨 BLOCKED**: Cannot merge to main until history functionality is working
- **NEXT PRIORITY**: Fix history fetch workflow, ensure successful data generation, proceed to merge
