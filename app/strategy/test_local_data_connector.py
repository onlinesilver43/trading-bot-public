#!/usr/bin/env python3
"""
Test Local Data Connector
Tests the Historical Analysis Bot with available data
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataConnector:
    """
    Test Data Connector

    This class provides test data for the Historical Analysis Bot:
    1. Creates realistic market data for testing
    2. Simulates the data structure from the production server
    3. Allows testing of the analysis components
    """

    def __init__(self):
        logger.info("Test Data Connector initialized for testing")

    def generate_test_data(
        self, symbol: str, interval: str, days: int = 30
    ) -> pd.DataFrame:
        """Generate realistic test data for analysis"""
        try:
            logger.info(f"📊 Generating test data for {symbol} {interval}")

            # Calculate number of data points based on interval
            if interval == "1h":
                points_per_day = 24
            elif interval == "5m":
                points_per_day = 288
            elif interval == "1d":
                points_per_day = 1
            else:
                points_per_day = 24

            total_points = days * points_per_day

            # Generate timestamps
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            if interval == "1h":
                timestamps = pd.date_range(start=start_time, end=end_time, freq="H")
            elif interval == "5m":
                timestamps = pd.date_range(start=start_time, end=end_time, freq="5T")
            elif interval == "1d":
                timestamps = pd.date_range(start=start_time, end=end_time, freq="D")
            else:
                timestamps = pd.date_range(start=start_time, end=end_time, freq="H")

            # Ensure we have the right number of points
            timestamps = timestamps[:total_points]

            # Generate realistic price data
            np.random.seed(42)  # For reproducible results

            # Start with a base price
            if symbol == "BTCUSDT":
                base_price = 50000
            elif symbol == "ETHUSDT":
                base_price = 3000
            else:
                base_price = 100

            # Generate price movements
            price_changes = np.random.normal(
                0, 0.02, len(timestamps)
            )  # 2% daily volatility
            prices = [base_price]

            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(
                    max(new_price, base_price * 0.1)
                )  # Prevent negative prices

            # Generate OHLCV data
            data = []
            for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
                # Generate realistic OHLCV
                volatility = 0.01  # 1% intraday volatility

                open_price = price
                high_price = price * (1 + abs(np.random.normal(0, volatility)))
                low_price = price * (1 - abs(np.random.normal(0, volatility)))
                close_price = price * (1 + np.random.normal(0, volatility * 0.5))

                volume = np.random.lognormal(10, 1)  # Realistic volume distribution

                data.append(
                    {
                        "timestamp": timestamp,
                        "open": round(open_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "close": round(close_price, 2),
                        "volume": round(volume, 2),
                        "symbol": symbol,
                        "interval": interval,
                    }
                )

            df = pd.DataFrame(data)
            logger.info(f"✅ Generated {len(df)} data points for {symbol} {interval}")

            return df

        except Exception as e:
            logger.error(f"Error generating test data: {str(e)}")
            return pd.DataFrame()

    def get_available_data(self) -> Dict[str, Any]:
        """Get available test data information"""
        try:
            logger.info("📊 Getting available test data information...")

            # Define available test data
            test_symbols = ["BTCUSDT", "ETHUSDT"]
            test_intervals = ["1h", "5m", "1d"]

            return {
                "manifest": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "data": {
                        symbol: {
                            interval: [
                                {
                                    "filename": f"{symbol}-{interval}-test.parquet",
                                    "file_type": "klines",
                                    "date": "test",
                                    "size_bytes": 10000,
                                    "parquet_path": f"/test/data/{symbol}/{interval}/test.parquet",
                                    "downloaded_at": datetime.now().isoformat(),
                                }
                            ]
                        }
                        for symbol in test_symbols
                        for interval in test_intervals
                    },
                },
                "statistics": {
                    "total_files": len(test_symbols) * len(test_intervals),
                    "total_size_mb": 0.1,
                    "symbols": test_symbols,
                    "intervals": test_intervals,
                    "last_updated": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting available data: {str(e)}")
            return {}

    def get_symbol_data(
        self, symbol: str, interval: str, limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """Get test data for a specific symbol and interval"""
        try:
            logger.info(f"📊 Getting test data for {symbol} {interval}")

            # Generate test data
            df = self.generate_test_data(symbol, interval, days=30)

            if df.empty:
                logger.error(f"Failed to generate test data for {symbol} {interval}")
                return None

            # Limit results if requested
            if limit and len(df) > limit:
                df = df.tail(limit)
                logger.info(f"Limited to {limit} most recent rows")

            return df

        except Exception as e:
            logger.error(f"Error getting symbol data: {str(e)}")
            return None

    def get_data_summary(self) -> Dict[str, Any]:
        """Get a summary of all available test data"""
        try:
            data_info = self.get_available_data()

            if not data_info:
                return {}

            # Get sample data for each symbol/interval combination
            summary = {"overview": data_info["statistics"], "sample_data": {}}

            data = data_info["manifest"].get("data", {})
            for symbol, intervals in data.items():
                summary["sample_data"][symbol] = {}

                for interval in intervals:
                    # Get a small sample of data
                    sample_df = self.get_symbol_data(symbol, interval, limit=100)
                    if sample_df is not None:
                        summary["sample_data"][symbol][interval] = {
                            "rows": len(sample_df),
                            "columns": list(sample_df.columns),
                            "date_range": {
                                "start": (
                                    sample_df.iloc[0].to_dict()
                                    if len(sample_df) > 0
                                    else None
                                ),
                                "end": (
                                    sample_df.iloc[-1].to_dict()
                                    if len(sample_df) > 0
                                    else None
                                ),
                            },
                        }

            return summary

        except Exception as e:
            logger.error(f"Error getting data summary: {str(e)}")
            return {}


def main():
    """Test the test data connector"""
    print("🚀 Test Data Connector - Phase 4 Integration")
    print("=" * 60)

    # Initialize connector
    connector = TestDataConnector()

    # Test data access
    print("\n📊 Testing test data access...")
    data_info = connector.get_available_data()

    if data_info:
        print("✅ Test data access successful!")
        print(f"📁 Total files: {data_info['statistics']['total_files']}")
        print(f"💾 Total size: {data_info['statistics']['total_size_mb']:.2f} MB")
        print(f"🔤 Symbols: {', '.join(data_info['statistics']['symbols'])}")
        print(f"⏰ Intervals: {', '.join(data_info['statistics']['intervals'])}")

        # Test getting sample data
        print("\n📊 Testing data retrieval...")
        for symbol in data_info["statistics"]["symbols"]:
            for interval in data_info["statistics"]["intervals"]:
                print(f"\n🔍 Testing {symbol} {interval}...")
                sample_data = connector.get_symbol_data(symbol, interval, limit=10)

                if sample_data is not None:
                    print(f"✅ Retrieved {len(sample_data)} rows")
                    print(f"📋 Columns: {', '.join(sample_data.columns)}")
                    if len(sample_data) > 0:
                        print(f"📅 Sample data: {sample_data.iloc[0].to_dict()}")
                else:
                    print("❌ Failed to retrieve data")

        # Get comprehensive summary
        print("\n📊 Getting comprehensive data summary...")
        summary = connector.get_data_summary()
        if summary:
            print("✅ Data summary generated successfully")
            print(f"📁 Overview: {summary['overview']}")
        else:
            print("❌ Failed to generate data summary")

    else:
        print("❌ Test data access failed!")


if __name__ == "__main__":
    main()
