#!/usr/bin/env python3
"""
Phase 3 Automated Test Suite
Automatically tests all Phase 3 components and provides comprehensive reporting
"""

import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Result of a single test"""
    component: str
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP", "ERROR"
    duration: float
    message: str
    details: Dict[str, Any] = None

@dataclass
class ComponentStatus:
    """Status of a component"""
    name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    overall_status: str  # "OPERATIONAL", "PARTIAL", "FAILED"
    last_test_time: datetime

class Phase3TestSuite:
    """Automated test suite for Phase 3 components"""
    
    def __init__(self):
        self.test_results: List[TestResult] = []
        self.component_status: Dict[str, ComponentStatus] = {}
        self.start_time = None
        self.end_time = None
        
        # Test configuration
        self.run_performance_tests = True
        self.run_integration_tests = True
        self.create_test_data = True
        self.cleanup_after_tests = False
        
        # Initialize component status
        self._init_component_status()
    
    def _init_component_status(self):
        """Initialize component status tracking"""
        components = [
            "Market Regime Detection",
            "Strategy Module", 
            "Strategy Performance Database",
            "Data Preprocessing Pipeline",
            "Backtesting Framework",
            "Integration Tests"
        ]
        
        for component in components:
            self.component_status[component] = ComponentStatus(
                name=component,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_tests=0,
                overall_status="UNKNOWN",
                last_test_time=datetime.now()
            )
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Phase 3 tests"""
        self.start_time = datetime.now()
        logger.info("🚀 Starting Phase 3 Automated Test Suite")
        logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Test individual components
            self._test_market_regime_detection()
            self._test_strategy_module()
            self._test_performance_database()
            self._test_data_preprocessing()
            self._test_backtesting_framework()
            
            # Test integration
            if self.run_integration_tests:
                self._test_integration()
            
            # Generate final report
            self.end_time = datetime.now()
            report = self._generate_test_report()
            
            logger.info("✅ All tests completed")
            return report
            
        except Exception as e:
            logger.error(f"❌ Test suite failed with error: {e}")
            traceback.print_exc()
            return {"status": "ERROR", "error": str(e)}
    
    def _test_market_regime_detection(self):
        """Test market regime detection system"""
        component = "Market Regime Detection"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test import
            start_time = time.time()
            from market_analysis.regime_detection import MarketRegimeDetector
            detector = MarketRegimeDetector()
            duration = time.time() - start_time
            
            self._record_test_result(component, "Import Test", "PASS", duration, 
                                   "Successfully imported MarketRegimeDetector")
            
            # Test regime detection
            start_time = time.time()
            test_data = self._create_test_market_data()
            regime_result = detector.detect_regime(test_data)
            duration = time.time() - start_time
            
            if regime_result and hasattr(regime_result, 'regime'):
                self._record_test_result(component, "Regime Detection", "PASS", duration,
                                       f"Detected regime: {regime_result.regime.value}")
            else:
                self._record_test_result(component, "Regime Detection", "FAIL", duration,
                                       "Regime detection failed to return valid result")
            
            # Test existing test file
            start_time = time.time()
            import subprocess
            result = subprocess.run([sys.executable, "market_analysis/test_regime_detection.py"], 
                                  capture_output=True, text=True, timeout=30)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self._record_test_result(component, "Test File Execution", "PASS", duration,
                                       "Test file executed successfully")
            else:
                self._record_test_result(component, "Test File Execution", "FAIL", duration,
                                       f"Test file failed: {result.stderr}")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _test_strategy_module(self):
        """Test strategy module"""
        component = "Strategy Module"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test import
            start_time = time.time()
            from strategy.sma_crossover import decide, indicators
            duration = time.time() - start_time
            
            self._record_test_result(component, "Import Test", "PASS", duration,
                                   "Successfully imported strategy functions")
            
            # Test indicators function
            start_time = time.time()
            test_prices = [100 + i * 0.1 for i in range(50)]
            fast_sma, slow_sma = indicators(test_prices, fast=10, slow=20, closed_only=True)
            duration = time.time() - start_time
            
            if len(fast_sma) > 0 and len(slow_sma) > 0:
                self._record_test_result(component, "Indicators Function", "PASS", duration,
                                       f"Generated {len(fast_sma)} fast SMA, {len(slow_sma)} slow SMA values")
            else:
                self._record_test_result(component, "Indicators Function", "FAIL", duration,
                                       "Indicators function failed to generate SMA values")
            
            # Test decide function
            start_time = time.time()
            class MockConfig:
                confirm_bars = 3
                threshold_pct = 0.01
                min_hold_bars = 5
            
            signal, reason, cooldown_ok, sep = decide(
                fast_sma, slow_sma, test_prices[-1], MockConfig(), 0, 1000000, 60000
            )
            duration = time.time() - start_time
            
            if signal in ["buy", "sell", "none"]:
                self._record_test_result(component, "Decision Function", "PASS", duration,
                                       f"Generated signal: {signal}, reason: {reason}")
            else:
                self._record_test_result(component, "Decision Function", "FAIL", duration,
                                       f"Decision function returned invalid signal: {signal}")
            
            # Test strategy test file
            start_time = time.time()
            import subprocess
            result = subprocess.run([sys.executable, "test_strategy.py"], 
                                  capture_output=True, text=True, timeout=30)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self._record_test_result(component, "Strategy Test File", "PASS", duration,
                                       "Strategy test file executed successfully")
            else:
                self._record_test_result(component, "Strategy Test File", "FAIL", duration,
                                       f"Strategy test file failed: {result.stderr}")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _test_performance_database(self):
        """Test strategy performance database"""
        component = "Strategy Performance Database"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test import
            start_time = time.time()
            from strategy.performance_db import StrategyPerformanceDB, TradeRecord
            duration = time.time() - start_time
            
            self._record_test_result(component, "Import Test", "PASS", duration,
                                   "Successfully imported performance database classes")
            
            # Test database creation
            start_time = time.time()
            db = StrategyPerformanceDB("test_perf.db")
            duration = time.time() - start_time
            
            self._record_test_result(component, "Database Creation", "PASS", duration,
                                   "Successfully created test performance database")
            
            # Test trade recording
            start_time = time.time()
            test_trade = TradeRecord(
                timestamp=int(time.time() * 1000),
                strategy_name="TestStrategy",
                symbol="TEST/USD",
                signal="buy",
                reason="test",
                price=100.0,
                market_regime="trending",
                regime_confidence=0.8,
                regime_trend=0.02,
                regime_volatility=0.03,
                volume=1000.0,
                timeframe="1h"
            )
            
            success = db.record_trade(test_trade)
            duration = time.time() - start_time
            
            if success:
                self._record_test_result(component, "Trade Recording", "PASS", duration,
                                       "Successfully recorded test trade")
            else:
                self._record_test_result(component, "Trade Recording", "FAIL", duration,
                                       "Failed to record test trade")
            
            # Test performance calculation
            start_time = time.time()
            metrics = db.calculate_performance("TestStrategy", "TEST/USD", "1h", 
                                            "2024-01-01", "2024-12-31")
            duration = time.time() - start_time
            
            if metrics and hasattr(metrics, 'total_trades'):
                self._record_test_result(component, "Performance Calculation", "PASS", duration,
                                       f"Calculated performance for {metrics.total_trades} trades")
            else:
                self._record_test_result(component, "Performance Calculation", "FAIL", duration,
                                       "Failed to calculate performance metrics")
            
            # Cleanup test database
            if self.cleanup_after_tests:
                import os
                os.remove("test_perf.db")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _test_data_preprocessing(self):
        """Test data preprocessing pipeline"""
        component = "Data Preprocessing Pipeline"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test import
            start_time = time.time()
            from data_collection.data_preprocessor import DataPreprocessor, OHLCVData
            duration = time.time() - start_time
            
            self._record_test_result(component, "Import Test", "PASS", duration,
                                   "Successfully imported data preprocessing classes")
            
            # Test synthetic data generation
            start_time = time.time()
            preprocessor = DataPreprocessor()
            test_data = preprocessor.generate_synthetic_data(days=50)
            duration = time.time() - start_time
            
            if len(test_data) == 50:
                self._record_test_result(component, "Data Generation", "PASS", duration,
                                       f"Generated {len(test_data)} synthetic OHLCV records")
            else:
                self._record_test_result(component, "Data Generation", "FAIL", duration,
                                       f"Expected 50 records, got {len(test_data)}")
            
            # Test data validation
            start_time = time.time()
            valid_data, errors = preprocessor.validate_data(test_data)
            duration = time.time() - start_time
            
            if len(valid_data) == len(test_data) and len(errors) == 0:
                self._record_test_result(component, "Data Validation", "PASS", duration,
                                       f"All {len(valid_data)} records passed validation")
            else:
                self._record_test_result(component, "Data Validation", "FAIL", duration,
                                       f"Validation failed: {len(errors)} errors")
            
            # Test data cleaning
            start_time = time.time()
            cleaned_data = preprocessor.clean_data(valid_data, remove_outliers=True, fill_gaps=True)
            duration = time.time() - start_time
            
            if len(cleaned_data) > 0:
                self._record_test_result(component, "Data Cleaning", "PASS", duration,
                                       f"Cleaned {len(cleaned_data)} records")
            else:
                self._record_test_result(component, "Data Cleaning", "FAIL", duration,
                                       "Data cleaning failed")
            
            # Test technical indicators
            start_time = time.time()
            indicators = preprocessor.calculate_technical_indicators(cleaned_data)
            duration = time.time() - start_time
            
            if len(indicators) > 0:
                self._record_test_result(component, "Technical Indicators", "PASS", duration,
                                       f"Calculated {len(indicators)} technical indicators")
            else:
                self._record_test_result(component, "Technical Indicators", "FAIL", duration,
                                       "Failed to calculate technical indicators")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _test_backtesting_framework(self):
        """Test backtesting framework"""
        component = "Backtesting Framework"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test import
            start_time = time.time()
            from strategy.backtesting import BacktestingEngine, BacktestConfig
            duration = time.time() - start_time
            
            self._record_test_result(component, "Import Test", "PASS", duration,
                                   "Successfully imported backtesting classes")
            
            # Test configuration creation
            start_time = time.time()
            config = BacktestConfig(
                strategy_name="TestStrategy",
                symbol="TEST/USD",
                timeframe="1d",
                start_date="2024-01-01",
                end_date="2024-12-31",
                initial_capital=10000.0
            )
            duration = time.time() - start_time
            
            self._record_test_result(component, "Configuration Creation", "PASS", duration,
                                   "Successfully created backtest configuration")
            
            # Test engine creation
            start_time = time.time()
            engine = BacktestingEngine(config)
            duration = time.time() - start_time
            
            self._record_test_result(component, "Engine Creation", "PASS", duration,
                                   "Successfully created backtesting engine")
            
            # Test with minimal data
            start_time = time.time()
            from data_collection.data_preprocessor import DataPreprocessor
            preprocessor = DataPreprocessor()
            test_data = preprocessor.generate_synthetic_data(days=100)
            duration = time.time() - start_time
            
            if len(test_data) == 100:
                self._record_test_result(component, "Test Data Preparation", "PASS", duration,
                                       f"Prepared {len(test_data)} test data points")
            else:
                self._record_test_result(component, "Test Data Preparation", "FAIL", duration,
                                       f"Expected 100 data points, got {len(test_data)}")
            
            # Run a quick backtest with minimal data
            start_time = time.time()
            try:
                # Create minimal test data for quick backtest
                test_data = preprocessor.generate_synthetic_data(days=20)
                # Run a very short backtest
                result = engine.run_backtest(test_data)
                duration = time.time() - start_time
                
                if result and hasattr(result, 'total_trades'):
                    self._record_test_result(component, "Quick Backtest", "PASS", duration,
                                           f"Quick backtest completed: {result.total_trades} trades")
                else:
                    self._record_test_result(component, "Quick Backtest", "FAIL", duration,
                                           "Quick backtest failed to return valid result")
            except Exception as e:
                self._record_test_result(component, "Quick Backtest", "FAIL", duration,
                                       f"Quick backtest error: {e}")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _test_integration(self):
        """Test integration between components"""
        component = "Integration Tests"
        logger.info(f"\n🧪 Testing {component}...")
        
        try:
            # Test end-to-end workflow
            start_time = time.time()
            
            # Generate data
            from data_collection.data_preprocessor import DataPreprocessor
            preprocessor = DataPreprocessor()
            data = preprocessor.generate_synthetic_data(days=50)
            
            # Detect regime
            from market_analysis.regime_detection import MarketRegimeDetector
            detector = MarketRegimeDetector()
            # Convert OHLCVData objects to dictionary format expected by regime detection
            market_data = [
                {
                    'timestamp': d.timestamp,
                    'open': d.open,
                    'high': d.high,
                    'low': d.low,
                    'close': d.close,
                    'volume': d.volume
                }
                for d in data
            ]
            regime = detector.detect_regime(market_data)
            
            # Generate strategy signal
            from strategy.sma_crossover import indicators, decide
            closes = [d.close for d in data]
            fast_sma, slow_sma = indicators(closes, 10, 20, True)
            
            class MockConfig:
                confirm_bars = 3
                threshold_pct = 0.01
                min_hold_bars = 5
            
            signal, reason, cooldown_ok, sep = decide(
                fast_sma, slow_sma, closes[-1], MockConfig(), 0, 1000000, 60000
            )
            
            # Record in performance database
            from strategy.performance_db import StrategyPerformanceDB, TradeRecord
            db = StrategyPerformanceDB("test_integration.db")
            
            trade = TradeRecord(
                timestamp=int(time.time() * 1000),
                strategy_name="IntegrationTest",
                symbol="TEST/USD",
                signal=signal if signal != "none" else "buy",
                reason=reason,
                price=closes[-1],
                market_regime=regime.regime.value,
                regime_confidence=regime.confidence,
                regime_trend=regime.trend_strength,
                regime_volatility=regime.volatility,
                volume=data[-1].volume,
                timeframe="1d"
            )
            
            success = db.record_trade(trade)
            duration = time.time() - start_time
            
            if success and regime and signal:
                self._record_test_result(component, "End-to-End Workflow", "PASS", duration,
                                       "Successfully completed full workflow: data → regime → signal → database")
            else:
                self._record_test_result(component, "End-to-End Workflow", "FAIL", duration,
                                       "Workflow failed at some step")
            
            # Cleanup
            if self.cleanup_after_tests:
                import os
                os.remove("test_integration.db")
            
        except Exception as e:
            self._record_test_result(component, "Component Test", "ERROR", 0,
                                   f"Error testing component: {e}")
            logger.error(f"Error testing {component}: {e}")
    
    def _create_test_market_data(self) -> List[Dict[str, Any]]:
        """Create test market data for regime detection"""
        import random
        data = []
        base_price = 100.0
        
        for i in range(100):
            # Random walk with some trend
            change = random.gauss(0.001, 0.02)
            base_price *= (1 + change)
            
            data.append({
                'timestamp': int(time.time() * 1000) + i * 60000,
                'open': base_price,
                'high': base_price * (1 + abs(random.gauss(0, 0.01))),
                'low': base_price * (1 - abs(random.gauss(0, 0.01))),
                'close': base_price * (1 + random.gauss(0, 0.01)),
                'volume': random.uniform(100, 1000)
            })
        
        return data
    
    def _record_test_result(self, component: str, test_name: str, status: str, 
                           duration: float, message: str, details: Dict[str, Any] = None):
        """Record a test result"""
        result = TestResult(
            component=component,
            test_name=test_name,
            status=status,
            duration=duration,
            message=message,
            details=details or {}
        )
        
        self.test_results.append(result)
        
        # Update component status
        if component in self.component_status:
            comp_status = self.component_status[component]
            comp_status.total_tests += 1
            comp_status.last_test_time = datetime.now()
            
            if status == "PASS":
                comp_status.passed_tests += 1
            elif status == "FAIL":
                comp_status.failed_tests += 1
            elif status == "SKIP":
                comp_status.skipped_tests += 1
            elif status == "ERROR":
                comp_status.error_tests += 1
            
            # Determine overall status
            if comp_status.failed_tests == 0 and comp_status.error_tests == 0:
                comp_status.overall_status = "OPERATIONAL"
            elif comp_status.passed_tests > 0:
                comp_status.overall_status = "PARTIAL"
            else:
                comp_status.overall_status = "FAILED"
        
        # Log result
        status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "ERROR": "💥"}
        logger.info(f"{status_emoji.get(status, '❓')} {component} - {test_name}: {status}")
        if message:
            logger.info(f"   {message}")
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == "PASS"])
        failed_tests = len([r for r in self.test_results if r.status == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r.status == "SKIP"])
        error_tests = len([r for r in self.test_results if r.status == "ERROR"])
        
        total_duration = sum(r.duration for r in self.test_results)
        
        # Calculate overall success rate
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if failed_tests == 0 and error_tests == 0:
            overall_status = "ALL TESTS PASSED"
        elif passed_tests > 0:
            overall_status = "PARTIAL SUCCESS"
        else:
            overall_status = "ALL TESTS FAILED"
        
        report = {
            "test_suite": "Phase 3 Automated Test Suite",
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": total_duration,
            "overall_status": overall_status,
            "success_rate": success_rate,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "error_tests": error_tests
            },
            "component_status": {
                name: {
                    "overall_status": status.overall_status,
                    "total_tests": status.total_tests,
                    "passed_tests": status.passed_tests,
                    "failed_tests": status.failed_tests,
                    "skipped_tests": status.skipped_tests,
                    "error_tests": status.error_tests,
                    "last_test_time": status.last_test_time.isoformat()
                }
                for name, status in self.component_status.items()
            },
            "detailed_results": [
                {
                    "component": r.component,
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.test_results
            ]
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted test report"""
        print("\n" + "="*80)
        print("🚀 PHASE 3 AUTOMATED TEST SUITE REPORT")
        print("="*80)
        
        # Overall summary
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   Status: {report['overall_status']}")
        print(f"   Success Rate: {report['success_rate']:.1f}%")
        print(f"   Total Tests: {report['summary']['total_tests']}")
        print(f"   Passed: {report['summary']['passed_tests']} ✅")
        print(f"   Failed: {report['summary']['failed_tests']} ❌")
        print(f"   Skipped: {report['summary']['skipped_tests']} ⏭️")
        print(f"   Errors: {report['summary']['error_tests']} 💥")
        print(f"   Total Duration: {report['total_duration']:.2f}s")
        
        # Component status
        print(f"\n🔧 COMPONENT STATUS:")
        for component, status in report['component_status'].items():
            status_emoji = {
                "OPERATIONAL": "✅",
                "PARTIAL": "⚠️", 
                "FAILED": "❌",
                "UNKNOWN": "❓"
            }
            emoji = status_emoji.get(status['overall_status'], "❓")
            print(f"   {emoji} {component}: {status['overall_status']}")
            print(f"      Tests: {status['passed_tests']}/{status['total_tests']} passed")
        
        # Failed tests details
        failed_tests = [r for r in report['detailed_results'] if r['status'] in ['FAIL', 'ERROR']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS DETAILS:")
            for test in failed_tests:
                print(f"   {test['component']} - {test['test_name']}")
                print(f"      Status: {test['status']}")
                print(f"      Message: {test['message']}")
                print()
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if report['success_rate'] == 100:
            print("   🎉 All tests passed! Phase 3 is ready for production.")
        elif report['success_rate'] >= 80:
            print("   ⚠️  Most tests passed. Review failed tests before production.")
        elif report['success_rate'] >= 50:
            print("   🚨 Significant issues found. Fix critical failures before continuing.")
        else:
            print("   💥 Major issues detected. Phase 3 needs significant work.")
        
        print("="*80)

def main():
    """Main function to run the test suite"""
    print("🧪 Phase 3 Automated Test Suite")
    print("Testing all Phase 3 components automatically...")
    
    # Create and run test suite
    test_suite = Phase3TestSuite()
    report = test_suite.run_all_tests()
    
    # Print results
    if report and 'status' != 'ERROR':
        test_suite.print_report(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"phase3_test_report_{timestamp}.json"
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if report['success_rate'] == 100:
            sys.exit(0)  # Success
        elif report['success_rate'] >= 80:
            sys.exit(1)  # Partial success
        else:
            sys.exit(2)  # Failure
    else:
        print("❌ Test suite failed to run")
        sys.exit(3)

if __name__ == "__main__":
    main()
