# Assistant Guide - Trading Bot Repository

## Repository Overview
- **Type**: Trading bot with BTC/ETH bots + FastAPI UI
- **Deployment**: GitHub Actions → DigitalOcean droplet
- **Environment**: WSL-friendly, uses GitHub CLI and SSH
- **Current Phase**: Phase 4 Strategy Implementation (Phase 1, 2, & 3 Complete)

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

## **🚀 CURRENT STATUS - PHASE 3 COMPLETE, READY FOR PHASE 4**

### **Phase 1 & 2**: ✅ COMPLETE & VALIDATED
- Enhanced UI operational in production
- System monitoring, history fetcher, deployment management
- All endpoints tested and working

### **Phase 3**: ✅ COMPLETE & VALIDATED
- Market Regime Detection: Fully operational
- Strategy Module: Fully operational
- Strategy Performance Database: Implemented and tested
- Data Preprocessing Pipeline: Complete and tested
- Backtesting Framework: Operational
- **Comprehensive Testing**: 100% success rate (36/36 tests passing)
- **All Import Issues**: Resolved (fixed all `app.` imports to relative imports)

### **Phase 4**: 🚀 READY TO BEGIN
- Master Agent system development
- Multi-bot orchestration
- Strategy switching logic
- Risk management system

## **🔧 ESSENTIAL COMMANDS & INTERACTIONS**

### **Local Development Environment**
```bash
# Navigate to project root
cd /mnt/c/tradingBot/repo

# Navigate to app directory (where most work happens)
cd app

# Activate virtual environment for testing
source ../.venv/bin/activate

# Run comprehensive test suite (should show 100% success rate)
../.venv/bin/python3 comprehensive_test_suite.py

# Quick test individual components
python3 quick_test.py regime      # Test market regime detection
python3 quick_test.py strategy    # Test strategy module
python3 quick_test.py database    # Test performance database
python3 quick_test.py preprocessing # Test data preprocessing
python3 quick_test.py backtesting # Test backtesting framework
python3 quick_test.py all         # Test all components
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
```

### **GitHub & Deployment**
```bash
# Check current branch
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
```

## **🧪 TESTING FRAMEWORK**

### **Comprehensive Test Suite**
```bash
# Run full system test (36 tests, should all pass)
cd app
../.venv/bin/python3 comprehensive_test_suite.py

# Expected output: 100% success rate, all 36 tests passing
```

### **Individual Component Testing**
```bash
# Test market regime detection
python3 market_analysis/test_regime_detection.py

# Test strategy module
python3 test_strategy.py

# Test performance database
python3 strategy/performance_db.py

# Test data preprocessing
python3 data_collection/data_preprocessor.py

# Test backtesting framework
python3 strategy/backtesting.py
```

### **Quick Test Runner**
```bash
# Test all components quickly
python3 quick_test.py all

# Test specific component
python3 quick_test.py regime
python3 quick_test.py strategy
python3 quick_test.py database
```

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
│   └── backtesting.py      # Backtesting framework
├── data_collection/         # Data collection components
│   └── data_preprocessor.py # Data preprocessing pipeline
└── exports/                 # Export functionality
    └── writers.py          # Data export writers
```

### **Test Files**
```
app/
├── comprehensive_test_suite.py  # Full system test suite (36 tests)
├── test_phase3_suite.py        # Phase 3 component tests
├── quick_test.py               # Quick component testing
└── test_strategy.py            # Strategy testing
```

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
# Run comprehensive test to see what's failing
../.venv/bin/python3 comprehensive_test_suite.py

# Check specific component
python3 quick_test.py [component_name]
```

#### **Virtual Environment Issues**
```bash
# Ensure virtual environment is activated
source ../.venv/bin/activate

# Check Python path
which python3
python3 -c "import sys; print(sys.path)"
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

## **🚀 DEVELOPMENT WORKFLOW**

### **Daily Development Process**
1. **Start Session**: Navigate to app directory, activate virtual environment
2. **Verify Status**: Run comprehensive test suite (should show 100% success)
3. **Make Changes**: Implement new features or fixes
4. **Test Changes**: Run relevant tests to ensure nothing breaks
5. **Update Warmup Files**: Document changes and update status
6. **End Session**: Ensure all warmup files reflect current state

### **Before Making Changes**
```bash
# Always verify current state first
cd app
../.venv/bin/python3 comprehensive_test_suite.py

# Should show 100% success rate before making changes
```

### **After Making Changes**
```bash
# Test your changes
python3 quick_test.py [relevant_component]

# Run comprehensive test to ensure nothing broke
../.venv/bin/python3 comprehensive_test_suite.py

# Update warmup files to reflect new status
```

## **📝 WARMUP FILES UPDATE CADENCE - CRITICAL FOR ASSISTANTS**

### **ALWAYS Update These Files After Major Changes:**
- **`current-status.md`** - Update after every significant milestone or status change
- **`assistant-guide.md`** - Update when adding new procedures or changing status
- **`plan.md`** - Update when completing phases or changing priorities
- **`test.md`** - Update after testing milestones or changes

### **When to Update (Automatic, No User Prompt Needed):**
1. **After completing a phase** - Mark as complete and update next steps
2. **After deployment** - Update deployment status and validation results
3. **After testing** - Update test results and system status
4. **After changing priorities** - Update plan and immediate next steps
5. **After adding new features** - Update current status and capabilities
6. **Before ending session** - Ensure all files reflect current state

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

## **User Preferences**
- **Commands**: Run directly without asking for approval
- **WSL**: All commands should be WSL-friendly
- **Automation**: Prefer automated scripts over manual steps
- **Verification**: Always verify deployments with status checks
- **Branch Workflow**: NEVER merge to main without explicit approval
- **Deployment Strategy**: Always tag and deploy from feature branches first
- **Testing**: Test branches with deployments before merging to main
- **Warmup Files**: Always update after major changes (automatic, no prompt needed)

## **🎯 IMMEDIATE NEXT STEPS**

### **Current Priority: Phase 4 Strategy Implementation**
1. **Master Agent System**: Build AI orchestrator for multiple strategies
2. **Multi-Bot Orchestration**: Implement 3-bot architecture with strategy switching
3. **Risk Management**: Portfolio-level risk control and capital allocation
4. **Strategy Optimization**: Dynamic strategy selection based on market regime

### **Success Criteria for Phase 4**
- Master Agent can detect market conditions and select optimal strategies
- Multi-bot system can execute different strategies simultaneously
- Risk management system protects capital while maximizing returns
- System achieves $200+ profit in first week for self-funding

---

**🎯 GOAL: Build intelligent, self-funding trading system that scales from $1K to $100K+ in 1 year through AI-powered multi-strategy trading.**

**📋 STATUS: Phase 1, 2, & 3 COMPLETE - Ready for Phase 4 Strategy Implementation with Master Agent system and multi-bot architecture.**

**🚀 READY TO CONTINUE: All foundation components operational with 100% testing success rate. Focus on Phase 4: Strategy Implementation.**

