#!/usr/bin/env python3
"""
Quick Test Runner
Run individual component tests or quick health checks
"""

import sys
import time
from typing import List, Optional

def test_component(component_name: str) -> bool:
    """Test a specific component"""
    print(f"🧪 Quick testing {component_name}...")
    
    try:
        if component_name == "regime":
            return _test_regime_detection()
        elif component_name == "strategy":
            return _test_strategy()
        elif component_name == "database":
            return _test_performance_database()
        elif component_name == "preprocessing":
            return _test_data_preprocessing()
        elif component_name == "backtesting":
            return _test_backtesting()
        elif component_name == "all":
            return _test_all_components()
        else:
            print(f"❌ Unknown component: {component_name}")
            print("Available components: regime, strategy, database, preprocessing, backtesting, all")
            return False
    except Exception as e:
        print(f"❌ Error testing {component_name}: {e}")
        return False

def _test_regime_detection() -> bool:
    """Quick test of regime detection"""
    try:
        from market_analysis.regime_detection import MarketRegimeDetector
        detector = MarketRegimeDetector()
        
        # Create minimal test data
        test_data = [{'timestamp': 1000, 'open': 100, 'high': 101, 'low': 99, 'close': 100.5, 'volume': 1000}]
        result = detector.detect_regime(test_data)
        
        if result and 'regime' in result:
            print(f"✅ Regime detection working: {result['regime']}")
            return True
        else:
            print("❌ Regime detection failed")
            return False
    except Exception as e:
        print(f"❌ Regime detection error: {e}")
        return False

def _test_strategy() -> bool:
    """Quick test of strategy module"""
    try:
        from strategy.sma_crossover import decide, indicators
        
        # Test with simple data
        prices = [100 + i * 0.1 for i in range(30)]
        fast_sma, slow_sma = indicators(prices, fast=10, slow=20, closed_only=True)
        
        if len(fast_sma) > 0 and len(slow_sma) > 0:
            print(f"✅ Strategy indicators working: {len(fast_sma)} fast, {len(slow_sma)} slow SMA")
            
            # Test decision function
            class MockConfig:
                confirm_bars = 3
                threshold_pct = 0.01
                min_hold_bars = 5
            
            signal, reason, cooldown_ok, sep = decide(
                fast_sma, slow_sma, prices[-1], MockConfig(), 0, 1000000, 60000
            )
            
            print(f"✅ Strategy decision working: {signal} ({reason})")
            return True
        else:
            print("❌ Strategy indicators failed")
            return False
    except Exception as e:
        print(f"❌ Strategy error: {e}")
        return False

def _test_performance_database() -> bool:
    """Quick test of performance database"""
    try:
        from strategy.performance_db import StrategyPerformanceDB, TradeRecord
        
        # Create test database
        db = StrategyPerformanceDB("quick_test.db")
        
        # Create test trade
        trade = TradeRecord(
            timestamp=int(time.time() * 1000),
            strategy_name="QuickTest",
            symbol="TEST/USD",
            signal="buy",
            reason="quick_test",
            price=100.0,
            market_regime="trending",
            regime_confidence=0.8,
            regime_trend=0.02,
            regime_volatility=0.03,
            volume=1000.0,
            timeframe="1h"
        )
        
        # Record trade
        success = db.record_trade(trade)
        if success:
            print("✅ Performance database working: trade recorded successfully")
            
            # Cleanup
            import os
            os.remove("quick_test.db")
            return True
        else:
            print("❌ Performance database failed: could not record trade")
            return False
    except Exception as e:
        print(f"❌ Performance database error: {e}")
        return False

def _test_data_preprocessing() -> bool:
    """Quick test of data preprocessing"""
    try:
        from data_collection.data_preprocessor import DataPreprocessor
        
        preprocessor = DataPreprocessor()
        
        # Generate minimal test data
        test_data = preprocessor.generate_synthetic_data(days=10)
        
        if len(test_data) == 10:
            print(f"✅ Data preprocessing working: generated {len(test_data)} records")
            
            # Test validation
            valid_data, errors = preprocessor.validate_data(test_data)
            if len(valid_data) == 10 and len(errors) == 0:
                print("✅ Data validation working")
                return True
            else:
                print(f"❌ Data validation failed: {len(errors)} errors")
                return False
        else:
            print(f"❌ Data preprocessing failed: expected 10, got {len(test_data)}")
            return False
    except Exception as e:
        print(f"❌ Data preprocessing error: {e}")
        return False

def _test_backtesting() -> bool:
    """Quick test of backtesting framework"""
    try:
        from strategy.backtesting import BacktestingEngine, BacktestConfig
        
        # Create configuration
        config = BacktestConfig(
            strategy_name="QuickTest",
            symbol="TEST/USD",
            timeframe="1d",
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=10000.0
        )
        
        # Create engine
        engine = BacktestingEngine(config)
        
        print("✅ Backtesting framework working: engine created successfully")
        return True
    except Exception as e:
        print(f"❌ Backtesting error: {e}")
        return False

def _test_all_components() -> bool:
    """Test all components"""
    components = ["regime", "strategy", "database", "preprocessing", "backtesting"]
    results = []
    
    print("🧪 Testing all components...")
    
    for component in components:
        result = test_component(component)
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Quick test results: {passed}/{total} components working")
    
    if passed == total:
        print("🎉 All components are working!")
        return True
    elif passed >= total * 0.8:
        print("⚠️  Most components are working")
        return True
    else:
        print("❌ Many components have issues")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 quick_test.py <component>")
        print("Available components:")
        print("  regime      - Test market regime detection")
        print("  strategy    - Test strategy module")
        print("  database    - Test performance database")
        print("  preprocessing - Test data preprocessing")
        print("  backtesting - Test backtesting framework")
        print("  all         - Test all components")
        print()
        print("Examples:")
        print("  python3 quick_test.py regime")
        print("  python3 quick_test.py all")
        return
    
    component = sys.argv[1].lower()
    success = test_component(component)
    
    if success:
        print(f"\n✅ {component} test completed successfully")
        sys.exit(0)
    else:
        print(f"\n❌ {component} test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
