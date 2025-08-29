# Deployment Checklist - Post-Reorganization

## 🚨 CRITICAL: Verify Before Deploying

### **1. Directory Structure ✅**
- [x] `app/bot/` - Trading bot components
- [x] `app/ui/` - User interface components  
- [x] `app/core/` - Core utilities
- [x] `app/strategy/` - Trading strategies
- [x] `app/market_analysis/` - Market analysis
- [x] `app/data_collection/` - Data collection
- [x] `app/testing/` - All test files and reports
- [x] `app/main.py` - Main entry point

### **2. Docker Configuration ✅**
- [x] `compose/docker-compose.yml` updated for new structure
- [x] Bot service: `python /app/main.py`
- [x] UI service: `uvicorn ui.ui:app --host 0.0.0.0 --port 8080`

### **3. Entry Points ✅**
- [x] `app/main.py` - Imports from `bot.bot_main`
- [x] `app/ui/ui.py` - FastAPI app accessible as `ui.ui:app`

### **4. Import Paths ✅**
- [x] All `__init__.py` files created
- [x] Test suite updated with correct import paths
- [x] Python path handling in test suite

### **5. Testing ✅**
- [x] Comprehensive test suite: 100% success rate
- [x] All test files moved to `testing/` directory
- [x] Test reports and databases organized

### **6. Cleanup Required Before Deployment**
- [ ] Run cleanup script to remove test files from app directory
- [ ] Remove `__pycache__` directories
- [ ] Remove temporary files (`fix_imports.py`, etc.)
- [ ] Verify app directory is clean for deployment

## 🔧 Pre-Deployment Steps

### **Step 1: Clean App Directory**
```bash
cd app
python3 cleanup_deployment.py
```

### **Step 2: Verify Clean Structure**
```bash
# Should show clean app directory
ls -la app/

# Should NOT show:
# - comprehensive_test_report_*.json
# - *.db files
# - __pycache__ directories
# - fix_imports.py
```

### **Step 3: Test Deployment Locally**
```bash
# Test bot entry point
python3 main.py

# Test UI entry point  
python3 -m uvicorn ui.ui:app --host 0.0.0.0 --port 8080
```

### **Step 4: Verify Docker Build**
```bash
cd compose
docker-compose build
```

## 🚀 Deployment Commands

### **Create Feature Branch**
```bash
git checkout -b feature/reorganized-codebase
git add .
git commit -m "Reorganize codebase with proper directory structure

- Organize components into logical directories
- Update Docker deployment configuration
- Move test files to testing/ directory
- Create proper Python packages with __init__.py files
- Maintain 100% test success rate
- Ready for Phase 4 development"
```

### **Deploy to Test Environment**
```bash
# Create deploy tag
TAG="deploy-$(date -u +%Y%m%d-%H%M)-$(git rev-parse --short HEAD)"
git tag -a "$TAG" -m "Deploy reorganized codebase"
git push origin "$TAG"

# Trigger deployment
gh workflow run "Deploy to Droplet" --ref "$TAG"
```

## ⚠️ Potential Issues to Watch

### **1. Import Paths**
- Ensure all imports use relative paths within packages
- Verify `__init__.py` files export correct components

### **2. Docker Volume Mounts**
- Verify `/host_app` and `/host_compose` paths work with new structure
- Check that environment variables are correctly set

### **3. File Permissions**
- Ensure Docker can read from new directory structure
- Verify template files are accessible

### **4. Database Paths**
- Check that database files are created in correct locations
- Verify state and trade file paths work

## ✅ Success Criteria

- [ ] Docker containers start without errors
- [ ] Bot service runs and connects to exchange
- [ ] UI service responds on port 8080
- [ ] All API endpoints work correctly
- [ ] No import errors in logs
- [ ] System maintains 100% test success rate

## 🔄 Rollback Plan

If deployment fails:
1. **Immediate**: Revert to previous working tag
2. **Investigation**: Check Docker logs and import errors
3. **Fix**: Update import paths or directory structure
4. **Retest**: Verify locally before redeploying

---

**Status**: Ready for deployment after cleanup
**Last Updated**: August 29, 2025
**Next Step**: Run cleanup script and create feature branch
