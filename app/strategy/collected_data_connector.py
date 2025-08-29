#!/usr/bin/env python3
"""
Collected Data Connector
Connects to the collected historical data on the production server
"""

import asyncio
import logging
import subprocess
import json
import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollectedDataConnector:
    """
    Collected Data Connector
    
    This class connects to the collected historical data on the production server:
    1. Access collected parquet files directly
    2. Provide data to the Historical Analysis Bot
    3. Support multiple symbols and timeframes
    """
    
    def __init__(self, server_alias: str = "tb"):
        self.server_alias = server_alias
        self.base_path = "/srv/trading-bots/history/parquet"
        
        logger.info(f"Collected Data Connector initialized for server: {server_alias}")
    
    def run_ssh_command(self, command: str) -> tuple:
        """Run SSH command on the production server"""
        try:
            ssh_cmd = f'sshpass -f ~/.ssh/tb_pw ssh {self.server_alias} "{command}"'
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception as e:
            return "", str(e), -1
    
    async def get_available_data(self) -> Dict[str, Any]:
        """Get available historical data from collected files"""
        try:
            logger.info("📊 Getting available collected data information...")
            
            # Get manifest
            stdout, stderr, code = self.run_ssh_command("cat /srv/trading-bots/history/manifest.json | jq '.'")
            if code != 0:
                logger.error(f"Failed to get manifest: {stderr}")
                return {}
            
            try:
                manifest = json.loads(stdout)
                logger.info(f"Found {manifest.get('statistics', {}).get('total_files', 0)} data files")
                
                return {
                    "manifest": manifest,
                    "timestamp": datetime.now().isoformat()
                }
            except json.JSONDecodeError:
                logger.error("Failed to parse manifest JSON")
                return {}
            
        except Exception as e:
            logger.error(f"Error getting available data: {str(e)}")
            return {}
    
    async def get_symbol_data(self, symbol: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Get historical data for a specific symbol and timeframe"""
        try:
            logger.info(f"📈 Getting {timeframe} data for {symbol}...")
            
            # Find available year-month directories
            command = f"ls {self.base_path}/{symbol}/{timeframe}/ | head -5"
            stdout, stderr, code = self.run_ssh_command(command)
            
            if code != 0 or not stdout.strip():
                logger.warning(f"No data found for {symbol} {timeframe}")
                return None
            
            # Get data from the first available year-month
            year_month = stdout.strip().split('\n')[0]
            logger.info(f"Using data from {year_month}")
            
            # List files in that directory
            command = f"ls {self.base_path}/{symbol}/{timeframe}/{year_month}/ | head -1"
            stdout, stderr, code = self.run_ssh_command(command)
            
            if code != 0 or not stdout.strip():
                logger.warning(f"No files found in {year_month}")
                return None
            
            filename = stdout.strip()
            file_path = f"{self.base_path}/{symbol}/{timeframe}/{year_month}/{filename}"
            
            # Copy file to local temp directory
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                local_path = tmp_file.name
            
            # Copy file from server to local temp
            copy_cmd = f"scp {self.server_alias}:{file_path} {local_path}"
            copy_result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
            
            if copy_result.returncode != 0:
                logger.error(f"Failed to copy file: {copy_result.stderr}")
                return None
            
            try:
                # Read parquet file
                df = pq.read_table(local_path).to_pandas()
                logger.info(f"✅ Loaded {len(df)} data points for {symbol} {timeframe}")
                
                # Standardize column names
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                elif 'date' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['date'])
                
                # Ensure required columns exist
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required_cols):
                    df = df[required_cols].copy()
                    df['symbol'] = symbol
                    df['source'] = 'collected_data'
                    
                    # Sort by timestamp and limit results
                    df = df.sort_values('timestamp').tail(limit).reset_index(drop=True)
                    
                    logger.info(f"✅ Processed {len(df)} data points for {symbol} {timeframe}")
                    return df
                else:
                    logger.warning(f"Missing required columns for {symbol} {timeframe}")
                    return None
                    
            finally:
                # Clean up temp file
                if os.path.exists(local_path):
                    os.unlink(local_path)
                
        except Exception as e:
            logger.error(f"Error getting {symbol} {timeframe} data: {str(e)}")
            return None
    
    async def get_market_data_summary(self) -> Dict[str, Any]:
        """Get summary of available market data"""
        try:
            available_data = await self.get_available_data()
            
            if not available_data:
                return {"error": "Could not connect to production server"}
            
            manifest = available_data.get("manifest", {})
            statistics = manifest.get("statistics", {})
            
            return {
                "available_symbols": list(statistics.get("symbols", {}).keys()),
                "available_timeframes": list(statistics.get("intervals", {}).keys()),
                "total_files": statistics.get("total_files", 0),
                "total_size_mb": round(statistics.get("total_size_bytes", 0) / (1024 * 1024), 2),
                "last_updated": manifest.get("collection_date", "Unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market data summary: {str(e)}")
            return {"error": str(e)}
    
    async def test_connection(self) -> bool:
        """Test connection to production server"""
        try:
            stdout, stderr, code = self.run_ssh_command("echo 'Connection test successful'")
            
            if code == 0 and "Connection test successful" in stdout:
                logger.info("✅ Production server connection successful")
                return True
            else:
                logger.error(f"❌ Production server connection failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Production server connection error: {str(e)}")
            return False

async def main():
    """Test the collected data connector"""
    print("🚀 Collected Data Connector - Phase 4 Integration")
    print("=" * 60)
    
    connector = CollectedDataConnector()
    
    # Test connection
    print("Testing connection to production server...")
    if not await connector.test_connection():
        print("❌ Connection failed!")
        return
    
    print("✅ Connection successful!")
    
    # Get available data
    print("\n📊 Getting available data...")
    summary = await connector.get_market_data_summary()
    
    if "error" in summary:
        print(f"❌ Error: {summary['error']}")
        return
    
    print(f"Available symbols: {', '.join(summary['available_symbols'])}")
    print(f"Available timeframes: {', '.join(summary['available_timeframes'])}")
    print(f"Total files: {summary['total_files']}")
    print(f"Total size: {summary['total_size_mb']} MB")
    print(f"Last updated: {summary['last_updated']}")
    
    # Test getting actual data
    print("\n📈 Testing data retrieval...")
    
    # Test BTCUSDT 1h
    print("Testing BTCUSDT 1h data...")
    btc_data = await connector.get_symbol_data("BTCUSDT", "1h", limit=100)
    
    if btc_data is not None:
        print(f"✅ BTCUSDT 1h data loaded successfully!")
        print(f"   Shape: {btc_data.shape}")
        print(f"   Columns: {list(btc_data.columns)}")
        print(f"   First few rows:")
        print(btc_data.head(3).to_string())
    else:
        print("❌ Failed to load BTCUSDT 1h data")
    
    # Test ETHUSDT 1h
    print("\nTesting ETHUSDT 1h data...")
    eth_data = await connector.get_symbol_data("ETHUSDT", "1h", limit=100)
    
    if eth_data is not None:
        print(f"✅ ETHUSDT 1h data loaded successfully!")
        print(f"   Shape: {eth_data.shape}")
    else:
        print("❌ Failed to load ETHUSDT 1h data")

if __name__ == "__main__":
    asyncio.run(main())
