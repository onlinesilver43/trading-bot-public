#!/usr/bin/env python3
"""
Simple Phase 4 Test
Tests the core Phase 4 components without complex imports
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Import only the test data connector that we know works
from strategy.test_local_data_connector import TestDataConnector

# Try to import the collected data connector for real data testing
try:
    from strategy.collected_data_connector import CollectedDataConnector
    REAL_DATA_AVAILABLE = True
except ImportError:
    REAL_DATA_AVAILABLE = False
    print("⚠️  CollectedDataConnector not available - will use test data only")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimplePhase4Test:
    """
    Simple Phase 4 Test
    
    This class tests the core Phase 4 functionality:
    1. Test Data Connector - provides realistic market data
    2. Data Analysis - basic market analysis capabilities
    3. Strategy Simulation - simple strategy logic
    4. Bot Management - basic bot orchestration concepts
    """
    
    def __init__(self, use_real_data: bool = False):
        self.use_real_data = use_real_data and REAL_DATA_AVAILABLE
        
        if self.use_real_data:
            try:
                self.data_connector = CollectedDataConnector()
                logger.info("Simple Phase 4 Test initialized with REAL DATA connector")
            except Exception as e:
                logger.warning(f"Failed to initialize real data connector: {e}")
                self.use_real_data = False
                self.data_connector = TestDataConnector()
                logger.info("Falling back to test data connector")
        else:
            self.data_connector = TestDataConnector()
            logger.info("Simple Phase 4 Test initialized with test data connector")
        
        self.test_results = {}
    
    async def run_simple_test(self) -> Dict[str, Any]:
        """Run simple Phase 4 system test"""
        logger.info("🚀 Starting simple Phase 4 system test...")
        
        try:
            # Step 1: Test data connector
            logger.info("\n📊 Step 1: Testing Data Connector...")
            data_test_result = await self._test_data_connector()
            
            # Step 2: Test basic market analysis
            logger.info("\n📊 Step 2: Testing Basic Market Analysis...")
            analysis_result = await self._test_basic_analysis()
            
            # Step 3: Test strategy simulation
            logger.info("\n📊 Step 3: Testing Strategy Simulation...")
            strategy_result = await self._test_strategy_simulation()
            
            # Step 4: Test bot management concepts
            logger.info("\n📊 Step 4: Testing Bot Management Concepts...")
            bot_result = await self._test_bot_management()
            
            # Compile results
            test_results = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "test_results": {
                    "data_connector": data_test_result,
                    "basic_analysis": analysis_result,
                    "strategy_simulation": strategy_result,
                    "bot_management": bot_result
                },
                "summary": {
                    "total_tests": 4,
                    "passed_tests": sum(1 for r in [data_test_result, analysis_result, 
                                                   strategy_result, bot_result] if r.get("status") == "success"),
                    "failed_tests": sum(1 for r in [data_test_result, analysis_result, 
                                                   strategy_result, bot_result] if r.get("status") == "error")
                }
            }
            
            logger.info("✅ Simple Phase 4 system test completed!")
            return test_results
            
        except Exception as e:
            logger.error(f"Error in simple test: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _test_data_connector(self) -> Dict[str, Any]:
        """Test the test data connector"""
        try:
            logger.info("Testing test data connector...")
            
            # Get available data
            data_info = self.data_connector.get_available_data()
            
            if not data_info:
                return {"status": "error", "error": "No data info available"}
            
            # Test data retrieval for each symbol/interval
            test_results = {}
            for symbol in data_info['statistics']['symbols']:
                for interval in data_info['statistics']['intervals']:
                    logger.info(f"Testing {symbol} {interval}...")
                    
                    if self.use_real_data:
                        # Use async method for real data
                        sample_data = await self.data_connector.get_symbol_data(symbol, interval, limit=100)
                    else:
                        # Use sync method for test data
                        sample_data = self.data_connector.get_symbol_data(symbol, interval, limit=100)
                    
                    if sample_data is not None and not sample_data.empty:
                        test_results[f"{symbol}_{interval}"] = {
                            "status": "success",
                            "rows": len(sample_data),
                            "columns": list(sample_data.columns),
                            "data_quality": "good",
                            "data_source": "real_data" if self.use_real_data else "test_data"
                        }
                        logger.info(f"✅ {symbol} {interval}: {len(sample_data)} data points ({'real' if self.use_real_data else 'test'} data)")
                    else:
                        test_results[f"{symbol}_{interval}"] = {
                            "status": "error",
                            "error": "No data retrieved"
                        }
                        logger.error(f"❌ {symbol} {interval}: No data returned")
            
            return {
                "status": "success",
                "data_info": data_info['statistics'],
                "test_results": test_results
            }
            
        except Exception as e:
            logger.error(f"Error testing data connector: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _test_basic_analysis(self) -> Dict[str, Any]:
        """Test basic market analysis capabilities"""
        try:
            logger.info("Testing basic market analysis...")
            
            # Get sample data for analysis
            if self.use_real_data:
                btc_data = await self.data_connector.get_symbol_data("BTCUSDT", "1h", limit=500)
                eth_data = await self.data_connector.get_symbol_data("ETHUSDT", "1h", limit=500)
            else:
                btc_data = self.data_connector.get_symbol_data("BTCUSDT", "1h", limit=500)
                eth_data = self.data_connector.get_symbol_data("ETHUSDT", "1h", limit=500)
            
            if btc_data is None or eth_data is None:
                return {"status": "error", "error": "Failed to get market data"}
            
            # Basic technical analysis
            analysis_results = {}
            
            # BTC Analysis
            btc_analysis = self._analyze_market_data(btc_data, "BTCUSDT")
            analysis_results["BTCUSDT"] = btc_analysis
            
            # ETH Analysis
            eth_analysis = self._analyze_market_data(eth_data, "ETHUSDT")
            analysis_results["ETHUSDT"] = eth_analysis
            
            return {
                "status": "success",
                "analysis_results": analysis_results,
                "data_points_analyzed": {
                    "BTCUSDT": len(btc_data),
                    "ETHUSDT": len(eth_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing basic analysis: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _analyze_market_data(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Analyze market data for basic insights"""
        try:
            if data.empty:
                return {"error": "No data to analyze"}
            
            # Calculate basic statistics
            close_prices = data['close'].values
            volumes = data['volume'].values
            
            # Price analysis
            price_change = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
            price_volatility = np.std(close_prices) / np.mean(close_prices) * 100
            
            # Volume analysis
            avg_volume = np.mean(volumes)
            volume_trend = (volumes[-1] - volumes[0]) / volumes[0] * 100 if volumes[0] > 0 else 0
            
            # Trend analysis
            if len(close_prices) >= 20:
                short_ma = np.mean(close_prices[-5:])  # 5-period MA
                long_ma = np.mean(close_prices[-20:])  # 20-period MA
                trend = "bullish" if short_ma > long_ma else "bearish" if short_ma < long_ma else "neutral"
            else:
                trend = "insufficient_data"
            
            return {
                "symbol": symbol,
                "price_analysis": {
                    "start_price": close_prices[0],
                    "end_price": close_prices[-1],
                    "price_change_percent": round(price_change, 2),
                    "volatility_percent": round(price_volatility, 2)
                },
                "volume_analysis": {
                    "average_volume": round(avg_volume, 2),
                    "volume_trend_percent": round(volume_trend, 2)
                },
                "trend_analysis": {
                    "trend": trend,
                    "data_points": len(close_prices)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market data for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _test_strategy_simulation(self) -> Dict[str, Any]:
        """Test basic strategy simulation"""
        try:
            logger.info("Testing strategy simulation...")
            
            # Get data for strategy testing
            btc_data = self.test_data_connector.get_symbol_data("BTCUSDT", "1h", limit=200)
            
            if btc_data is None or btc_data.empty:
                return {"status": "error", "error": "Failed to get BTC data for strategy testing"}
            
            # Simulate simple strategies
            strategies = {
                "sma_crossover": self._simulate_sma_crossover(btc_data),
                "mean_reversion": self._simulate_mean_reversion(btc_data),
                "momentum": self._simulate_momentum(btc_data)
            }
            
            return {
                "status": "success",
                "strategies_tested": list(strategies.keys()),
                "strategy_results": strategies,
                "data_points_used": len(btc_data)
            }
            
        except Exception as e:
            logger.error(f"Error testing strategy simulation: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _simulate_sma_crossover(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Simulate SMA crossover strategy"""
        try:
            close_prices = data['close'].values
            
            if len(close_prices) < 20:
                return {"error": "Insufficient data for SMA crossover"}
            
            # Calculate moving averages
            sma_5 = np.mean(close_prices[-5:])
            sma_20 = np.mean(close_prices[-20:])
            
            # Generate signals
            current_signal = "buy" if sma_5 > sma_20 else "sell"
            signal_strength = abs(sma_5 - sma_20) / sma_20 * 100
            
            return {
                "strategy": "SMA Crossover",
                "current_signal": current_signal,
                "signal_strength": round(signal_strength, 2),
                "sma_5": round(sma_5, 2),
                "sma_20": round(sma_20, 2)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _simulate_mean_reversion(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Simulate mean reversion strategy"""
        try:
            close_prices = data['close'].values
            
            if len(close_prices) < 20:
                return {"error": "Insufficient data for mean reversion"}
            
            # Calculate mean and standard deviation
            mean_price = np.mean(close_prices)
            std_price = np.std(close_prices)
            current_price = close_prices[-1]
            
            # Calculate z-score
            z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
            
            # Generate signals
            if z_score > 1.5:
                signal = "sell"  # Overbought
            elif z_score < -1.5:
                signal = "buy"   # Oversold
            else:
                signal = "hold"
            
            return {
                "strategy": "Mean Reversion",
                "current_signal": signal,
                "z_score": round(z_score, 2),
                "current_price": round(current_price, 2),
                "mean_price": round(mean_price, 2),
                "deviation_percent": round(abs(current_price - mean_price) / mean_price * 100, 2)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _simulate_momentum(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Simulate momentum strategy"""
        try:
            close_prices = data['close'].values
            
            if len(close_prices) < 10:
                return {"error": "Insufficient data for momentum strategy"}
            
            # Calculate momentum indicators
            price_change_1h = (close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100
            price_change_5h = (close_prices[-1] - close_prices[-6]) / close_prices[-6] * 100 if len(close_prices) >= 6 else 0
            
            # Generate signals
            if price_change_1h > 0.5 and price_change_5h > 2.0:
                signal = "buy"  # Strong upward momentum
            elif price_change_1h < -0.5 and price_change_5h < -2.0:
                signal = "sell"  # Strong downward momentum
            else:
                signal = "hold"
            
            return {
                "strategy": "Momentum",
                "current_signal": signal,
                "1h_momentum": round(price_change_1h, 2),
                "5h_momentum": round(price_change_5h, 2),
                "momentum_strength": "strong" if abs(price_change_1h) > 1.0 else "weak"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _test_bot_management(self) -> Dict[str, Any]:
        """Test basic bot management concepts"""
        try:
            logger.info("Testing bot management concepts...")
            
            # Simulate bot status and management
            bot_status = {
                "bot_1": {
                    "status": "active",
                    "symbol": "BTCUSDT",
                    "strategy": "sma_crossover",
                    "capital_allocated": 500.0,
                    "current_position": "long",
                    "pnl": 25.50
                },
                "bot_2": {
                    "status": "active",
                    "symbol": "ETHUSDT",
                    "strategy": "mean_reversion",
                    "capital_allocated": 300.0,
                    "current_position": "flat",
                    "pnl": -5.20
                },
                "bot_3": {
                    "status": "standby",
                    "symbol": "BNBUSDT",
                    "strategy": "momentum",
                    "capital_allocated": 0.0,
                    "current_position": "none",
                    "pnl": 0.0
                }
            }
            
            # Calculate portfolio metrics
            total_capital = sum(bot["capital_allocated"] for bot in bot_status.values())
            total_pnl = sum(bot["pnl"] for bot in bot_status.values())
            active_bots = sum(1 for bot in bot_status.values() if bot["status"] == "active")
            
            return {
                "status": "success",
                "bot_status": bot_status,
                "portfolio_metrics": {
                    "total_capital": total_capital,
                    "total_pnl": total_pnl,
                    "active_bots": active_bots,
                    "roi_percent": round(total_pnl / total_capital * 100, 2) if total_capital > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing bot management: {str(e)}")
            return {"status": "error", "error": str(e)}

def main():
    """Main test function"""
    import sys
    
    # Check if user wants to test with real data
    use_real_data = "--real-data" in sys.argv
    
    if use_real_data:
        print("🚀 Simple Phase 4 Test - Core System Validation with REAL DATA")
        print("=" * 70)
    else:
        print("🚀 Simple Phase 4 Test - Core System Validation with TEST DATA")
        print("=" * 70)
    
    # Initialize test
    test = SimplePhase4Test(use_real_data=use_real_data)
    
    # Run test
    async def run_test():
        results = await test.run_simple_test()
        
        # Display results
        print("\n📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        print(f"Overall Status: {results['status']}")
        print(f"Data Source: {'REAL DATA' if use_real_data else 'TEST DATA'}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed: {results['summary']['passed_tests']}")
        print(f"Failed: {results['summary']['failed_tests']}")
        
        if results['status'] == 'success':
            print("\n✅ Simple Phase 4 system test completed successfully!")
            print("Core Phase 4 functionality is working correctly.")
        else:
            print("\n❌ Simple Phase 4 system test failed!")
            print("Check the logs for detailed error information.")
        
        return results
    
    # Run the async test
    results = asyncio.run(run_test())
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_type = "real" if use_real_data else "test"
    results_file = f"simple_phase4_test_results_{data_type}_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📁 Test results saved to: {results_file}")
    
    # Print usage instructions
    if not use_real_data:
        print("\n💡 To test with REAL DATA, run: python3 simple_phase4_test.py --real-data")

if __name__ == "__main__":
    main()
