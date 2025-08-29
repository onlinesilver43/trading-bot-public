#!/usr/bin/env python3
"""
Production Data Connector
Connects to the existing production server to get real historical data
for the Historical Analysis Bot
"""

import asyncio
import logging
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionDataConnector:
    """
    Production Data Connector
    
    This class connects to the existing production server to:
    1. Get real historical data from the existing Binance data collection
    2. Access the existing data infrastructure
    3. Provide data to the Historical Analysis Bot
    """
    
    def __init__(self, production_url: str = "http://64.23.214.191:8080"):
        self.production_url = production_url
        self.session = requests.Session()
        
        # Data endpoints
        self.endpoints = {
            "history_manifest": "/api/history/manifest",
            "history_status": "/api/history/status",
            "system_health": "/api/system/health",
            "exports": "/exports"
        }
        
        logger.info(f"Production Data Connector initialized for: {production_url}")
    
    async def test_connection(self) -> bool:
        """Test connection to production server"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.session.get, f"{self.production_url}/api/system/health"
            )
            
            if response.status_code == 200:
                logger.info("✅ Production server connection successful")
                return True
            else:
                logger.error(f"❌ Production server connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Production server connection error: {str(e)}")
            return False
    
    async def get_available_data(self) -> Dict[str, Any]:
        """Get available historical data from production server"""
        try:
            logger.info("📊 Getting available historical data...")
            
            # Get history manifest
            manifest_response = await asyncio.get_event_loop().run_in_executor(
                None, self.session.get, f"{self.production_url}{self.endpoints['history_manifest']}"
            )
            
            if manifest_response.status_code != 200:
                logger.error(f"Failed to get history manifest: {manifest_response.status_code}")
                return {}
            
            manifest = manifest_response.json()
            logger.info(f"Found {len(manifest.get('files', []))} data files")
            
            # Get history status
            status_response = await asyncio.get_event_loop().run_in_executor(
                None, self.session.get, f"{self.production_url}{self.endpoints['history_status']}"
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                logger.info(f"Data directory: {status.get('data_directory', 'Unknown')}")
                logger.info(f"Total size: {status.get('total_size_mb', 0):.2f} MB")
            
            return {
                "manifest": manifest,
                "status": status if status_response.status_code == 200 else {},
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting available data: {str(e)}")
            return {}
    
    async def get_symbol_data(self, symbol: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Get historical data for a specific symbol and timeframe"""
        try:
            logger.info(f"📈 Getting {timeframe} data for {symbol}...")
            
            # Try to get data from exports endpoint
            export_url = f"{self.production_url}{self.endpoints['exports']}"
            
            # Check if there's a direct data endpoint
            data_response = await asyncio.get_event_loop().run_in_executor(
                None, self.session.get, f"{export_url}/{symbol}_{timeframe}.csv"
            )
            
            if data_response.status_code == 200:
                # Parse CSV data
                from io import StringIO
                csv_data = StringIO(data_response.text)
                data = pd.read_csv(csv_data)
                
                # Standardize column names
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                elif 'date' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['date'])
                
                # Ensure required columns exist
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                if all(col in data.columns for col in required_cols):
                    data = data[required_cols].copy()
                    data['symbol'] = symbol
                    data['source'] = 'production_server'
                    
                    # Sort by timestamp and limit results
                    data = data.sort_values('timestamp').tail(limit).reset_index(drop=True)
                    
                    logger.info(f"✅ Loaded {len(data)} data points for {symbol} {timeframe}")
                    return data
                else:
                    logger.warning(f"Missing required columns for {symbol} {timeframe}")
                    return None
            else:
                logger.warning(f"No direct data available for {symbol} {timeframe}")
                return None
                
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
            files = manifest.get("files", [])
            
            # Analyze available data
            symbols = set()
            timeframes = set()
            total_size_mb = 0
            
            for file_info in files:
                filename = file_info.get("filename", "")
                size_mb = file_info.get("size_mb", 0)
                
                # Parse filename to extract symbol and timeframe
                if "-" in filename:
                    parts = filename.split("-")
                    if len(parts) >= 3:
                        symbol = parts[0]
                        timeframe = parts[1]
                        symbols.add(symbol)
                        timeframes.add(timeframe)
                        total_size_mb += size_mb
            
            return {
                "available_symbols": list(symbols),
                "available_timeframes": list(timeframes),
                "total_files": len(files),
                "total_size_mb": round(total_size_mb, 2),
                "last_updated": manifest.get("collection_date", "Unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market data summary: {str(e)}")
            return {"error": str(e)}
    
    async def download_data_sample(self, symbol: str, timeframe: str, output_dir: str = "data_samples") -> str:
        """Download a sample of data for local analysis"""
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Get data
            data = await self.get_symbol_data(symbol, timeframe, limit=1000)
            
            if data is not None and not data.empty:
                # Save to local file
                filename = f"{symbol}_{timeframe}_sample.csv"
                filepath = output_path / filename
                
                data.to_csv(filepath, index=False)
                logger.info(f"✅ Data sample saved to: {filepath}")
                
                return str(filepath)
            else:
                logger.warning(f"No data available for {symbol} {timeframe}")
                return ""
                
        except Exception as e:
            logger.error(f"Error downloading data sample: {str(e)}")
            return ""

async def main():
    """Test the Production Data Connector"""
    print("🚀 Production Data Connector - Phase 4 Integration")
    print("=" * 60)
    
    # Initialize connector
    connector = ProductionDataConnector()
    
    # Test connection
    print("Testing connection to production server...")
    if await connector.test_connection():
        print("✅ Connection successful!")
        
        # Get available data
        print("\n📊 Getting available data...")
        summary = await connector.get_market_data_summary()
        
        if "error" not in summary:
            print(f"Available symbols: {', '.join(summary['available_symbols'][:5])}")
            print(f"Available timeframes: {', '.join(summary['available_timeframes'])}")
            print(f"Total files: {summary['total_files']}")
            print(f"Total size: {summary['total_size_mb']} MB")
            print(f"Last updated: {summary['last_updated']}")
            
            # Try to get sample data
            if summary['available_symbols']:
                symbol = summary['available_symbols'][0]
                timeframe = summary['available_timeframes'][0] if summary['available_timeframes'] else "1h"
                
                print(f"\n📈 Getting sample data for {symbol} {timeframe}...")
                data = await connector.get_symbol_data(symbol, timeframe, limit=100)
                
                if data is not None and not data.empty:
                    print(f"✅ Successfully loaded {len(data)} data points")
                    print(f"Data range: {data['timestamp'].min()} to {data['timestamp'].max()}")
                    print(f"Columns: {list(data.columns)}")
                else:
                    print("❌ No data available")
        else:
            print(f"❌ Error: {summary['error']}")
    else:
        print("❌ Connection failed!")

if __name__ == "__main__":
    asyncio.run(main())
