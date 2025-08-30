#!/usr/bin/env python3
"""
Local Data Connector
Reads historical data directly from the collected data directory
for the Historical Analysis Bot
"""

import logging
import json
import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalDataConnector:
    """
    Local Data Connector

    This class reads historical data directly from the collected data directory:
    1. Reads from /srv/trading-bots/history/ on the production server
    2. Provides data to the Historical Analysis Bot
    3. Works with the existing data collection infrastructure
    """

    def __init__(self, data_dir: str = "/srv/trading-bots/history"):
        self.data_dir = Path(data_dir)
        self.manifest_path = self.data_dir / "manifest.json"

        logger.info(f"Local Data Connector initialized for: {data_dir}")

    def get_available_data(self) -> Dict[str, Any]:
        """Get available historical data from local directory"""
        try:
            logger.info("📊 Getting available historical data from local directory...")

            if not self.manifest_path.exists():
                logger.error(f"Manifest file not found: {self.manifest_path}")
                return {}

            with open(self.manifest_path, "r") as f:
                manifest = json.load(f)

            # Extract statistics
            stats = manifest.get("statistics", {})
            total_files = stats.get("total_files", 0)
            total_size_mb = stats.get("total_size_bytes", 0) / (1024 * 1024)

            logger.info(f"Found {total_files} data files")
            logger.info(f"Total size: {total_size_mb:.2f} MB")

            # Extract available symbols and intervals
            data = manifest.get("data", {})
            symbols = list(data.keys())
            intervals = set()

            for symbol_data in data.values():
                for interval in symbol_data.keys():
                    intervals.add(interval)

            logger.info(f"Available symbols: {', '.join(symbols)}")
            logger.info(f"Available intervals: {', '.join(intervals)}")

            return {
                "manifest": manifest,
                "statistics": {
                    "total_files": total_files,
                    "total_size_mb": total_size_mb,
                    "symbols": symbols,
                    "intervals": list(intervals),
                    "last_updated": manifest.get("last_updated", "Unknown"),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting available data: {str(e)}")
            return {}

    def get_symbol_data(
        self, symbol: str, interval: str, limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """Get historical data for a specific symbol and interval"""
        try:
            logger.info(f"📊 Getting {symbol} {interval} data...")

            # Check if data exists
            data_dir = self.data_dir / "parquet" / symbol / interval
            if not data_dir.exists():
                logger.error(f"Data directory not found: {data_dir}")
                return None

            # Get all available months
            month_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
            month_dirs.sort()

            if not month_dirs:
                logger.error(f"No month directories found in {data_dir}")
                return None

            logger.info(f"Found {len(month_dirs)} month directories")

            # Read data from each month
            all_data = []
            for month_dir in month_dirs:
                # month = month_dir.name  # Not currently used
                parquet_files = list(month_dir.glob("*.parquet"))

                if not parquet_files:
                    logger.warning(f"No parquet files found in {month_dir}")
                    continue

                for parquet_file in parquet_files:
                    try:
                        df = pq.read_table(parquet_file).to_pandas()
                        all_data.append(df)
                        logger.info(f"Read {len(df)} rows from {parquet_file.name}")
                    except Exception as e:
                        logger.error(f"Error reading {parquet_file}: {str(e)}")
                        continue

            if not all_data:
                logger.error("No data could be read from any files")
                return None

            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Combined {len(combined_df)} total rows")

            # Sort by timestamp if available
            if "timestamp" in combined_df.columns:
                combined_df = combined_df.sort_values("timestamp")

            # Limit results if requested
            if limit and len(combined_df) > limit:
                combined_df = combined_df.tail(limit)
                logger.info(f"Limited to {limit} most recent rows")

            return combined_df

        except Exception as e:
            logger.error(f"Error getting symbol data: {str(e)}")
            return None

    def get_data_summary(self) -> Dict[str, Any]:
        """Get a summary of all available data"""
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
    """Test the local data connector"""
    print("🚀 Local Data Connector - Phase 4 Integration")
    print("=" * 60)

    # Initialize connector
    connector = LocalDataConnector()

    # Test data access
    print("\n📊 Testing local data access...")
    data_info = connector.get_available_data()

    if data_info:
        print("✅ Local data access successful!")
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
        print("❌ Local data access failed!")
        print("Make sure the data directory exists and contains collected data")


if __name__ == "__main__":
    main()
