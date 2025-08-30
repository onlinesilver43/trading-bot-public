# Assistant Guide - Trading Bot Repository

## Repository Overview
- **Type**: Trading bot with BTC/ETH bots + FastAPI UI
- **Deployment**: GitHub Actions → DigitalOcean droplet
- **Environment**: WSL-friendly, uses GitHub CLI and SSH
- **Current Phase**: Phase 4 Strategy Implementation (Components Implemented & Tested, All Workflows Passing)
- **🚨 CRITICAL ISSUE**: History Fetch workflow failed - cannot merge to main until resolved

## **🚨 CRITICAL ISSUE: History Functionality Blocking Merge to Main**

### **Current Status**: 
- **Phase 4**: ✅ **COMPLETE** - All components implemented, tested, and validated
- **Import System**: ✅ **REFACTORED** - Clean ImportResolver class implemented
- **All Tests**: ✅ **PASSING** - 33/33 tests with 100% success rate
- **History Functionality**: ❌ **FAILED** - Workflow failed during Docker build on server
- **Merge Status**: 🚨 **BLOCKED** - Cannot merge to main until history functionality is working

### **Immediate Priority**: Fix History Fetch Workflow
- **Issue**: Docker build failed with "failed to read dockerfile: open Dockerfile: no such file or directory"
- **Impact**: No historical data can be collected, blocking deployment testing
- **Requirement**: Must fix before creating merge request or proceeding to Phase 5

### **Self-Funding Development Strategy**
1. **Week 1**: Generate $200+ profit to fund development ✅ **COMPLETE - Phase 4 components built**
2. **Week 2**: Use profits to build full multi-bot system 🚨 **BLOCKED - History functionality must be fixed first**
3. **Week 3**: Complete AI agent, achieve self-funding
4. **Week 4+**: Unlimited scaling begins

### **Multi-Bot Architecture** ✅ **IMPLEMENTED**
- **Bot 1**: Core Strategy Bot (enhanced current bot) - 30% capital ✅ **READY**
- **Bot 2**: Scalping Bot (high-frequency) - 25% capital ✅ **READY**
- **Bot 3**: Momentum Bot (trend following) - 25% capital ✅ **READY**
- **Bot 4**: Arbitrage Bot (cross-exchange) - 15% capital ✅ **READY**
- **Bot 5**: Hedging Bot (risk management) - 5% capital ✅ **READY**

### **AI Agent Integration** ✅ **IMPLEMENTED**
- **Market Analysis**: Real-time condition monitoring ✅ **READY**
- **Strategy Selection**: Dynamic strategy switching ✅ **READY**
- **Bot Orchestration**: Coordinate all 5 bots simultaneously ✅ **READY**
- **Risk Management**: Portfolio-level risk control ✅ **READY**

---

## **🔧 ESSENTIAL COMMANDS & INTERACTIONS**

### **Local Development Environment**
```bash
# Navigate to project root
cd /mnt/c/tradingBot/repo

# Navigate to app directory (where most work happens)
cd app

# Activate virtual environment for testing
source ../.venv/bin/activate

# Run simple Phase 4 test (should show 4/4 tests passing)
python3 simple_phase4_test.py

# Test individual Phase 4 components
python3 strategy/test_local_data_connector.py  # Test data connector
python3 strategy/master_agent.py               # Test master agent
python3 strategy/dynamic_bot_orchestrator.py  # Test bot orchestrator
```

### **Production Environment (DigitalOcean Droplet)**
```bash
# SSH to droplet
sshpass -f ~/.ssh/tb_pw ssh tb

# Check running containers
docker ps

# Check bot status
curl http://127.0.0.1:8080/api/state

# Check system health
curl http://127.0.0.1:8080/api/system/health

# Check system resources
curl http://127.0.0.1:8080/api/system/resources

# Check system performance
curl http://127.0.0.1:8080/api/system/performance

# Check historical data collection status
curl http://127.0.0.1:8080/api/history/manifest
```

### **GitHub & Deployment**
```bash
# Check current branch (should be feature/reorganized-codebase)
git branch --show-current

# Check status safely
git status --porcelain

# Check remote branches safely
git ls-remote --heads origin

# Create deploy tag
TAG="deploy-$(date -u +%Y%m%d-%H%M)-$(git rev-parse --short HEAD)"
git tag -a "$TAG" -m "Deploy"
git push origin "$TAG"

# Trigger deployment workflow
gh workflow run "Deploy to Droplet" --ref "$TAG"

# Watch deployment
gh run watch --exit-status

# Check CI workflow status
gh run list --workflow="ci.yml" --limit 1

# Trigger CI workflow
gh workflow run "CI" --ref feature/reorganized-codebase
```

---

## **🧪 TESTING FRAMEWORK**

### **Phase 4 Test Suite**
```bash
# Run simple Phase 4 test (4 tests, should all pass)
cd app
source ../.venv/bin/activate
python3 simple_phase4_test.py

# Expected output: 4/4 tests passing, all Phase 4 components working
```

### **Deployment Test Suite - CRITICAL FOR PRODUCTION VALIDATION**
```bash
# Run comprehensive deployment tests after deploying to production
cd app/testing
python3 deployment_test_suite.py

# This tests ALL production endpoints and Phase 4 components
# Expected: 100% endpoint success + Phase 4 component validation
# ✅ IMPROVED: Now uses API endpoints only (no SSH commands)
# ✅ RELIABLE: Faster, more consistent, no network dependency issues
```

### **CI Workflow Testing**
```bash
# Verify all CI workflows pass locally
cd app
source ../.venv/bin/activate
python3 -m ruff check .
python3 -m black --check .
find . -name "*.py" -exec python3 -m py_compile {} \;

# Expected: All tests passing locally
```

### **Comprehensive Test Suite**
```bash
# Run comprehensive test suite (30 tests, should all pass)
cd app
source ../.venv/bin/activate
python3 testing/comprehensive_test_suite.py

# This tests ALL components and validates CI workflows will pass
# Expected: 30/30 tests passing including pytest workflow validation
```

### **Test Framework Update Requirements**
**CRITICAL**: After adding ANY new component, update the test framework:

1. **`deployment_test_suite.py`** - Add component testing method
2. **`test_phase4_suite.py`** - Add component-specific tests  
3. **`comprehensive_test_suite.py`** - Integrate new component tests
4. **`simple_phase4_test.py`** - Add basic component validation

**Why Critical**: Without updates, new components won't be validated after deployment!

**REMINDER FOR ASSISTANTS**: Update the proper test framework after each component is added to ensure comprehensive testing coverage.

### **Individual Component Testing**
```bash
# Test test data connector
python3 strategy/test_local_data_connector.py

# Test master agent (basic functionality)
python3 strategy/master_agent.py

# Test dynamic bot orchestrator (basic functionality)
python3 strategy/dynamic_bot_orchestrator.py

# Test historical data analyzer (basic functionality)
python3 strategy/historical_data_analyzer.py
```

### **Historical Data Testing**
```bash
# Test data connector with test data
python3 strategy/test_local_data_connector.py

# Expected output: 6 test files, BTCUSDT/ETHUSDT, 1h/5m/1d intervals
# Should generate 720+ data points per symbol/interval combination
```

---

## **📁 PROJECT STRUCTURE**

### **Core Application (`app/`)**
```
app/
├── bot_main.py              # Main bot logic
├── bot.py                   # Bot utilities and functions
├── ui.py                    # FastAPI main application
├── ui_enhanced.py           # Enhanced UI functions
├── ui_routes.py             # UI route definitions
├── ui_helpers.py            # UI helper functions
├── core/                    # Core trading utilities
│   └── utils.py            # Time, SMA, and utility functions
├── exchange/                # Exchange integration
│   └── ccxt_client.py      # CCXT client wrapper
├── portfolio/               # Portfolio management
│   └── portfolio.py        # Portfolio tracking and calculations
├── state/                   # State management
│   └── store.py            # JSON state persistence
├── market_analysis/         # Market analysis components
│   └── regime_detection.py # Market regime detection
├── strategy/                # Strategy components
│   ├── performance_db.py   # Strategy performance database
│   ├── backtesting.py      # Backtesting framework
│   ├── master_agent.py     # Master Agent system ✅ NEW
│   ├── dynamic_bot_orchestrator.py # Bot orchestration ✅ NEW
│   ├── historical_data_analyzer.py # Data analysis ✅ NEW
│   ├── strategy_discovery.py # Strategy discovery ✅ NEW
│   ├── multi_bot_orchestrator.py # Multi-bot management ✅ NEW
│   ├── production_data_connector.py # Production integration ✅ NEW
│   ├── local_data_connector.py # Local data access ✅ NEW
│   └── test_local_data_connector.py # Test data generation ✅ NEW
├── data_collection/         # Data collection components
│   └── data_preprocessor.py # Data preprocessing pipeline
└── exports/                 # Export functionality
    └── writers.py          # Data export writers
```

### **Test Files**
```
app/
├── comprehensive_test_suite.py  # Full system test suite (30 tests)
├── test_phase3_suite.py        # Phase 3 component tests
├── simple_phase4_test.py       # Phase 4 system test ✅ NEW
├── quick_test.py               # Quick component testing
└── test_strategy.py            # Strategy testing
```

---

## **🚨 CRITICAL: Terminal Commands to AVOID**
- **NEVER use `git branch -a`** - This command breaks the terminal due to long output
- **NEVER use `git status` with long output** - Can cause terminal issues
- **Use `git branch` instead** - Shows only local branches safely
- **Use `git status --porcelain`** - For clean, safe status output

### **✅ SAFE Git Commands for Terminal**
- **Check current branch**: `git branch --show-current`
- **List local branches**: `git branch`
- **Check status safely**: `git status --porcelain`
- **Check remote branches safely**: `git ls-remote --heads origin`
- **Get commit info**: `git log --oneline -5`

---

## **🔍 DEBUGGING & TROUBLESHOOTING**

### **Common Issues & Solutions**

#### **Import Errors**
```bash
# If you see "No module named 'app'" errors:
# Check for any remaining 'app.' imports in files
grep -r "from app\." app/

# Fix by changing to relative imports:
# from app.core.utils → from core.utils
# from app.state.store → from state.store
```

#### **Test Failures**
```bash
# Run simple Phase 4 test to see what's failing
source ../.venv/bin/activate
python3 simple_phase4_test.py

# Check specific component
python3 strategy/test_local_data_connector.py
```

#### **Virtual Environment Issues**
```bash
# Ensure virtual environment is activated
source ../.venv/bin/activate

# Check Python path
which python3
python3 -c "import sys; print(sys.path)"
```

#### **CI Workflow Issues**
```bash
# If GitHub Actions CI fails while local tests pass:
# 1. Check GitHub Actions logs for specific error
# 2. Compare local vs remote environment differences
# 3. Fix any issues found in CI logs
# 4. Re-run workflow to verify success
```

### **Logs & Monitoring**
```bash
# Check bot logs (if running)
docker logs [container_name]

# Check system resources
curl http://127.0.0.1:8080/api/system/resources

# Check API health
curl http://127.0.0.1:8080/api/system/health
```

---

## **📊 PERFORMANCE MONITORING**

### **System Health Endpoints**
- **`/api/system/health`**: CPU, memory, disk usage
- **`/api/system/resources`**: Detailed resource information
- **`/api/system/performance`**: Performance metrics
- **`/api/state`**: Bot trading state and portfolio

### **Expected Performance**
- **CPU Usage**: < 10% under normal load
- **Memory Usage**: < 2GB for trading bot
- **Disk Usage**: < 5GB for data storage
- **API Response Time**: < 100ms for most endpoints

---

## **🚀 DEVELOPMENT WORKFLOW**

### **Daily Development Process**
1. **Start Session**: Navigate to app directory, activate virtual environment
2. **Verify Status**: Run full pytest validation + simple Phase 4 test
3. **Make Changes**: Implement new features or fixes
4. **Test Changes**: Run full pytest validation + relevant tests to ensure nothing breaks
5. **Update Warmup Files**: Document changes and update status
6. **End Session**: Ensure all warmup files reflect current state

### **Before Making Changes**
```bash
# Always verify current state first
cd app
source ../.venv/bin/activate

# CRITICAL: Run full pytest validation (same as GitHub Actions)
python3 -m pytest --collect-only --tb=no
python3 -m pytest app/ --cov=app --cov-report=xml

# Should show all tests collecting and running without import errors
# This catches the same issues GitHub Actions will find

# Also run simple Phase 4 test
python3 simple_phase4_test.py
# Should show 4/4 tests passing before making changes
```

### **After Making Changes**
```bash
# Test your changes
python3 strategy/[relevant_component].py

# CRITICAL: Run full pytest validation to ensure nothing broke
python3 -m pytest --collect-only --tb=no
python3 -m pytest app/ --cov=app --cov-report=xml

# Run simple Phase 4 test to ensure nothing broke
python3 simple_phase4_test.py

# Update warmup files to reflect new status
```

---

## **📝 WARMUP FILES UPDATE CADENCE - CRITICAL FOR ASSISTANTS**

### **ALWAYS Update These Files After Major Changes:**
- **`current-status.md`** - Update after every significant milestone or status change
- **`assistant-guide.md`** - Update when adding new procedures or changing status
- **`plan.md`** - Update when completing phases or changing priorities
- **`test.md`** - Update after testing milestones or changes

### **WARMUP FILES UPDATE CADENCE - CRITICAL FOR ASSISTANTS**
**Proactive Updates Required**: Update warmup files on a regular cadence, not just when user reminds you
- **Daily**: Update status after each development session
- **Weekly**: Comprehensive updates to all warmup files
- **After Each Phase**: Complete status update across all files
- **Before Ending Session**: Ensure all files reflect current state

**Why Critical**: Without regular updates, warmup files become outdated and misleading, causing confusion in future sessions

### **When to Update (Automatic, No User Prompt Needed):**
1. **After completing a phase** - Mark as complete and update next steps
2. **After deployment** - Update deployment status and validation results
3. **After testing** - Update test results and system status
4. **After changing priorities** - Update plan and immediate next steps
5. **After adding new features** - Update current status and capabilities
6. **Before ending session** - Ensure all files reflect current state

---

## **🏗️ REFACTORING PRINCIPLES - CRITICAL FOR ASSISTANTS**

### **ALWAYS REFACTOR, NEVER JUST PATCH**
**Critical Principle**: When encountering issues in the codebase, always opt for refactoring if it will make the code:
- **Easier to maintain** - Clean, logical structure
- **More stable** - Robust error handling and edge cases
- **Easier to read** - Clear, understandable code
- **More modular** - Separated concerns and responsibilities

**Examples of Refactoring vs Patching:**
- ❌ **PATCHING**: Skip failing tests, add try/catch everywhere, comment out problematic code
- ✅ **REFACTORING**: Create clean import resolvers, restructure modules, implement proper error handling

**Why This Matters**: 
- Patches create technical debt and make future maintenance harder
- Refactoring improves the overall codebase quality and developer experience
- Clean code is easier to debug, test, and extend

### **REFACTORING CHECKLIST:**
1. **Identify the root cause** of the issue
2. **Design a clean solution** that improves the codebase
3. **Implement the solution** with proper error handling
4. **Test thoroughly** to ensure the refactoring works
5. **Document the changes** for future developers

### **RECENT REFACTORING EXAMPLE - Import System:**
**Problem**: Complex, fragile import logic in test suite causing failures
**❌ Patching Approach**: Skip failing tests, comment out problematic imports
**✅ Refactoring Approach**: 
- Created `ImportResolver` class with clean, maintainable import logic
- Separated import concerns from test logic
- Implemented multiple import strategies with proper error handling
- Made the system extensible for future import needs

**Result**: Clean, maintainable import system that can be easily extended and debugged

---

## **🧪 TEST FRAMEWORK UPDATE REQUIREMENTS - CRITICAL FOR ASSISTANTS**

### **MANDATORY: Update Test Framework After Adding New Components**

#### **When Adding New Components:**
1. **Update `deployment_test_suite.py`** - Add new component testing methods
2. **Update `test_phase4_suite.py`** - Add component-specific test cases
3. **Update `comprehensive_test_suite.py`** - Integrate new component tests
4. **Update `simple_phase4_test.py`** - Add basic component validation

#### **Component Testing Integration Pattern:**
```python
# Example: Adding new component "Strategy Engine"
def test_strategy_engine(self) -> Dict[str, Any]:
    """Test Strategy Engine component after deployment"""
    print("\n🎯 Testing Strategy Engine...")
    
    strategy_results = {
        "strategy_creation": {"status": "not_tested", "error": None},
        "strategy_execution": {"status": "not_tested", "error": None},
        "strategy_performance": {"status": "not_tested", "error": None}
    }
    
    try:
        # Test component functionality
        # Add specific test logic here
        
        return {
            "status": "completed",
            "components": strategy_results,
            "summary": {"tested": 3, "success": 2, "warning": 1, "error": 0}
        }
    except Exception as e:
        # Handle errors
        return {"status": "error", "error": str(e)}
```

#### **Integration Points to Update:**
1. **`deployment_test_suite.py`** - Add to `run_comprehensive_test()` method
2. **Summary printing** - Include new component results in deployment summary
3. **Test reporting** - Ensure new components appear in test reports
4. **Success criteria** - Update deployment success criteria if needed

#### **Why This is Critical:**
- **Without test framework updates**, new components won't be validated after deployment
- **Deployment tests will miss** new functionality, leading to false positives
- **Production validation** becomes incomplete and unreliable
- **Component failures** won't be caught until manual testing

#### **Example Update Sequence:**
```bash
# 1. Add new component to codebase
# 2. Update deployment_test_suite.py with test method
# 3. Update run_comprehensive_test() to include new test
# 4. Update summary printing to show new component results
# 5. Test locally to ensure test framework works
# 6. Deploy and run deployment tests
# 7. Verify new component appears in test results
```

### **Update Pattern:**
```markdown
## **✅ What Was Accomplished:**
- [x] Feature A implemented and tested
- [x] Feature B deployed to production
- [x] Feature C validated and working

## **📋 Next Session Will Focus On:**
- Next phase implementation
- New features to build
- Testing requirements
- Deployment plans
```

---

## **User Preferences**
- **Commands**: Run directly without asking for approval
- **WSL**: All commands should be WSL-friendly
- **Automation**: Prefer automated scripts over manual steps
- **Verification**: Always verify deployments with status checks
- **Branch Workflow**: NEVER merge to main without explicit approval
- **Deployment Strategy**: Always tag and deploy from feature branches first
- **Testing**: Test branches with deployments before merging to main
- **Warmup Files**: Always update after major changes (automatic, no prompt needed)

---

**🎯 GOAL**: Build intelligent, self-funding trading system that scales from $1K to $100K+ in 1 year through AI-powered multi-strategy trading.

**📋 STATUS**: Phase 4 components implemented and deployed. Enhanced test framework working with real data. All CI tests passing. All workflows passing. Ready for deployment validation and merge to main to begin Phase 5 development.

**🚀 READY TO CONTINUE**: Phase 4 components deployed and working. All workflows passing. All tests passing. Ready to complete deployment validation and merge branch to main to begin Phase 5 development.

