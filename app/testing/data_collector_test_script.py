#!/usr/bin/env python3
"""
Safe test script for historical data collector
This script tests the data collection system without affecting the main trading bot
"""

import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_collection import HistoricalDataCollector, DataCollectionConfig
from datetime import datetime, timedelta


def test_data_collector():
    """Test the historical data collector with a small dataset"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting safe test of historical data collector...")

    # Test configuration - only collect 1 day of data for testing
    test_config = DataCollectionConfig(
        symbols=["BTC/USDT"],
        timeframes=["1h", "4h"],  # Start with larger timeframes for testing
        start_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        data_dir="/srv/trading-bots/historical_data_test",  # Separate test directory
        max_retries=2,
        rate_limit_delay=0.2,  # Slower rate limiting for testing
    )

    try:
        # Create collector instance
        collector = HistoricalDataCollector(test_config)

        # Test system resource checking
        logger.info("Testing system resource checking...")
        resources_ok = collector._check_system_resources()
        logger.info(f"System resources OK: {resources_ok}")

        # Test exchange connection
        logger.info("Testing exchange connection...")
        markets = collector.exchange.load_markets()
        logger.info(f"Loaded {len(markets)} markets from exchange")

        # Test small data collection
        logger.info("Testing small data collection...")
        result = collector.collect_historical_data()

        logger.info("Test completed!")
        logger.info(f"Result: {result}")

        return result

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Run the test
    result = test_data_collector()

    # Print result summary
    print("\n" + "=" * 50)
    print("TEST RESULT SUMMARY")
    print("=" * 50)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Message: {result.get('message', 'No message')}")

    if "stats" in result:
        stats = result["stats"]
        print(f"Total candles: {stats.get('total_candles', 0)}")
        print(f"Total size: {stats.get('total_size_mb', 0):.2f} MB")
        print(f"Errors: {stats.get('errors', 0)}")

    print("=" * 50)

    # Exit with appropriate code
    if result.get("status") == "success":
        sys.exit(0)
    else:
        sys.exit(1)
