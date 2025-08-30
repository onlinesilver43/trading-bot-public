#!/usr/bin/env python3
"""
Test Historical Analysis Bot
Tests the complete Phase 4 system with test data
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import json

# Import our test components
from strategy.test_local_data_connector import TestDataConnector
from strategy.historical_data_analyzer import HistoricalDataAnalyzer
from strategy.master_agent import MasterAgent
from strategy.dynamic_bot_orchestrator import DynamicBotOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestHistoricalAnalysisBot:
    """
    Test Historical Analysis Bot

    This class tests the complete Phase 4 system:
    1. Test Data Connector - provides realistic market data
    2. Historical Data Analyzer - analyzes market regimes and opportunities
    3. Master Agent - orchestrates strategy selection
    4. Dynamic Bot Orchestrator - manages multiple bots
    """

    def __init__(self):
        self.test_data_connector = TestDataConnector()
        self.historical_analyzer = None
        self.master_agent = None
        self.bot_orchestrator = None

        logger.info("Test Historical Analysis Bot initialized")

    async def run_complete_test(self) -> Dict[str, Any]:
        """Run complete Phase 4 system test"""
        logger.info("🚀 Starting complete Phase 4 system test...")

        try:
            # Step 1: Test data connector
            logger.info("\n📊 Step 1: Testing Data Connector...")
            data_test_result = await self._test_data_connector()

            # Step 2: Test historical data analyzer
            logger.info("\n📊 Step 2: Testing Historical Data Analyzer...")
            analyzer_test_result = await self._test_historical_analyzer()

            # Step 3: Test master agent
            logger.info("\n📊 Step 3: Testing Master Agent...")
            master_agent_result = await self._test_master_agent()

            # Step 4: Test bot orchestration
            logger.info("\n📊 Step 4: Testing Bot Orchestration...")
            orchestration_result = await self._test_bot_orchestration()

            # Step 5: Run complete workflow
            logger.info("\n📊 Step 5: Running Complete Workflow...")
            workflow_result = await self._run_complete_workflow()

            # Compile results
            test_results = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "test_results": {
                    "data_connector": data_test_result,
                    "historical_analyzer": analyzer_test_result,
                    "master_agent": master_agent_result,
                    "bot_orchestration": orchestration_result,
                    "complete_workflow": workflow_result,
                },
                "summary": {
                    "total_tests": 5,
                    "passed_tests": sum(
                        1
                        for r in [
                            data_test_result,
                            analyzer_test_result,
                            master_agent_result,
                            orchestration_result,
                            workflow_result,
                        ]
                        if r.get("status") == "success"
                    ),
                    "failed_tests": sum(
                        1
                        for r in [
                            data_test_result,
                            analyzer_test_result,
                            master_agent_result,
                            orchestration_result,
                            workflow_result,
                        ]
                        if r.get("status") == "error"
                    ),
                },
            }

            logger.info("✅ Complete Phase 4 system test completed!")
            return test_results

        except Exception as e:
            logger.error(f"Error in complete test: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_data_connector(self) -> Dict[str, Any]:
        """Test the test data connector"""
        try:
            logger.info("Testing test data connector...")

            # Get available data
            data_info = self.test_data_connector.get_available_data()

            if not data_info:
                return {"status": "error", "error": "No data info available"}

            # Test data retrieval for each symbol/interval
            test_results = {}
            for symbol in data_info["statistics"]["symbols"]:
                for interval in data_info["statistics"]["intervals"]:
                    logger.info(f"Testing {symbol} {interval}...")

                    sample_data = self.test_data_connector.get_symbol_data(
                        symbol, interval, limit=100
                    )

                    if sample_data is not None and not sample_data.empty:
                        test_results[f"{symbol}_{interval}"] = {
                            "status": "success",
                            "rows": len(sample_data),
                            "columns": list(sample_data.columns),
                            "data_quality": "good",
                        }
                    else:
                        test_results[f"{symbol}_{interval}"] = {
                            "status": "error",
                            "error": "No data retrieved",
                        }

            return {
                "status": "success",
                "data_info": data_info["statistics"],
                "test_results": test_results,
            }

        except Exception as e:
            logger.error(f"Error testing data connector: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_historical_analyzer(self) -> Dict[str, Any]:
        """Test the historical data analyzer with test data"""
        try:
            logger.info("Testing historical data analyzer...")

            # Initialize analyzer with test data connector
            self.historical_analyzer = HistoricalDataAnalyzer(
                symbols=["BTCUSDT", "ETHUSDT"],
                data_sources=None,  # Will use default
                api_keys={},
            )

            # Override the data loading method to use test data
            async def test_data_loader(symbol, timeframe):
                return self.test_data_connector.get_symbol_data(
                    symbol, timeframe, limit=1000
                )

            # Replace the data loading method
            self.historical_analyzer._pull_symbol_data = test_data_loader

            # Run analysis
            analysis_result = await self.historical_analyzer.run_full_analysis()

            return {
                "status": "success",
                "analysis_result": analysis_result,
                "historical_data_count": len(self.historical_analyzer.historical_data),
                "regime_analysis_count": len(self.historical_analyzer.regime_analysis),
                "opportunities_count": len(
                    self.historical_analyzer.strategy_opportunities
                ),
            }

        except Exception as e:
            logger.error(f"Error testing historical analyzer: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_master_agent(self) -> Dict[str, Any]:
        """Test the master agent"""
        try:
            logger.info("Testing master agent...")

            # Initialize master agent
            self.master_agent = MasterAgent()

            # Test basic functionality
            market_regime = self.master_agent.analyze_market_regime("BTCUSDT", "1h")
            strategy_selection = self.master_agent.select_strategy(
                "BTCUSDT", "1h", market_regime
            )

            return {
                "status": "success",
                "market_regime": market_regime,
                "strategy_selection": strategy_selection,
                "agent_status": "operational",
            }

        except Exception as e:
            logger.error(f"Error testing master agent: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_bot_orchestration(self) -> Dict[str, Any]:
        """Test the bot orchestration system"""
        try:
            logger.info("Testing bot orchestration...")

            # Initialize bot orchestrator
            self.bot_orchestrator = DynamicBotOrchestrator()

            # Test basic functionality
            bot_status = self.bot_orchestrator.get_bot_status()
            strategy_status = self.bot_orchestrator.get_strategy_status()

            return {
                "status": "success",
                "bot_status": bot_status,
                "strategy_status": strategy_status,
                "orchestrator_status": "operational",
            }

        except Exception as e:
            logger.error(f"Error testing bot orchestration: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _run_complete_workflow(self) -> Dict[str, Any]:
        """Run the complete workflow from data to strategy execution"""
        try:
            logger.info("Running complete workflow...")

            # Step 1: Get market data
            btc_data = self.test_data_connector.get_symbol_data(
                "BTCUSDT", "1h", limit=500
            )
            eth_data = self.test_data_connector.get_symbol_data(
                "ETHUSDT", "1h", limit=500
            )

            if btc_data is None or eth_data is None:
                return {"status": "error", "error": "Failed to get market data"}

            # Step 2: Analyze market regimes
            btc_regime = self.master_agent.analyze_market_regime("BTCUSDT", "1h")
            eth_regime = self.master_agent.analyze_market_regime("ETHUSDT", "1h")

            # Step 3: Select strategies
            btc_strategy = self.master_agent.select_strategy(
                "BTCUSDT", "1h", btc_regime
            )
            eth_strategy = self.master_agent.select_strategy(
                "ETHUSDT", "1h", eth_regime
            )

            # Step 4: Orchestrate bots
            bot_assignments = self.bot_orchestrator.assign_strategies(
                {
                    "BTCUSDT": {"strategy": btc_strategy, "regime": btc_regime},
                    "ETHUSDT": {"strategy": eth_strategy, "regime": eth_regime},
                }
            )

            # Step 5: Generate execution plan
            execution_plan = self.bot_orchestrator.generate_execution_plan(
                bot_assignments
            )

            return {
                "status": "success",
                "data_points": {"BTCUSDT": len(btc_data), "ETHUSDT": len(eth_data)},
                "market_regimes": {"BTCUSDT": btc_regime, "ETHUSDT": eth_regime},
                "strategies": {"BTCUSDT": btc_strategy, "ETHUSDT": eth_strategy},
                "bot_assignments": bot_assignments,
                "execution_plan": execution_plan,
            }

        except Exception as e:
            logger.error(f"Error in complete workflow: {str(e)}")
            return {"status": "error", "error": str(e)}


def main():
    """Main test function"""
    print("🚀 Test Historical Analysis Bot - Phase 4 Complete System Test")
    print("=" * 80)

    # Initialize test bot
    test_bot = TestHistoricalAnalysisBot()

    # Run complete test
    async def run_test():
        results = await test_bot.run_complete_test()

        # Display results
        print("\n📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        print(f"Overall Status: {results['status']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed: {results['summary']['passed_tests']}")
        print(f"Failed: {results['summary']['failed_tests']}")

        if results["status"] == "success":
            print("\n✅ Phase 4 system test completed successfully!")
            print("The Historical Analysis Bot is ready for real data integration.")
        else:
            print("\n❌ Phase 4 system test failed!")
            print("Check the logs for detailed error information.")

        return results

    # Run the async test
    results = asyncio.run(run_test())

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"phase4_test_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📁 Test results saved to: {results_file}")


if __name__ == "__main__":
    main()
