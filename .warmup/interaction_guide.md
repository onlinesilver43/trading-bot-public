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
- ✅ Enhanced test framework successfully deployed
- ✅ Git conflicts resolved and enhanced framework pushed
- ✅ CI workflow testing COMPLETED - All 39 Ruff linting issues resolved
- ✅ Import issues FIXED - BacktestingEngine and sma_crossover imports corrected
- ✅ Virtual environment properly configured with all dependencies
- ✅ Local CI tests all passing
- ❌ GitHub Actions CI workflow failed (exit code 1) - needs investigation
- ✅ BTCUSDT 1h: 67 files collected (complete)
- ✅ ETHUSDT 1h: 67 files collected (complete)
- ✅ BTCUSDT 5m: 67 files collected (complete)
- ✅ ETHUSDT 5m: 67 files collected (complete)
- ✅ Total: 268 files, 66 MB - ALL DATA COLLECTION COMPLETE

### Next Steps After Data Collection
1. **Investigate GitHub Actions CI Failure** 🔍 **IMMEDIATE**
   - Check GitHub Actions logs for specific error
   - Identify what caused the workflow to fail
   - Determine if it's a code issue or workflow configuration issue

2. **Fix Remaining Issues** 🔧 **NEXT**
   - Address any problems found in CI logs
   - Ensure all code quality standards are met
   - Test fixes locally before re-running CI

3. **Verify CI Success** ✅ **GOAL**
   - Re-run GitHub Actions workflow
   - Confirm all checks pass
   - Ensure branch is ready for merge

4. **Prepare for Merge** 🚀 **FINAL**
   - Create merge request
   - Merge feature/reorganized-codebase to main
   - Begin Phase 5 development

### Key Commands for Next Session
```bash
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
- GitHub Actions CI failure investigation completed
- Specific error identified and understood
- All remaining issues fixed
- CI workflow re-run and passes successfully
- Branch ready for merge to main

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

### CI Workflow Issues
If GitHub Actions CI fails while local tests pass:
1. Check GitHub Actions logs for specific error
2. Compare local vs remote environment differences
3. Fix any issues found in CI logs
4. Re-run workflow to verify success

## 🎯 Next Steps After Data Collection - ALL DATA COLLECTION COMPLETE

1. **Investigate GitHub Actions CI Failure** 🔍 **IMMEDIATE** - Check CI logs for specific error
2. **Fix Remaining Issues** 🔧 **NEXT** - Address any problems found by CI workflow
3. **Verify CI Success** ✅ **GOAL** - Re-run workflow to verify all checks pass
4. **Prepare for Merge** 🚀 **FINAL** - Get branch into mergable state

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
- **GITHUB ACTIONS CI FAILED** - Exit code 1, needs investigation
- **NEXT PRIORITY** - Investigate CI failure, fix remaining issues, get CI passing
