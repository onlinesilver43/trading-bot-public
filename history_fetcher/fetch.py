#!/usr/bin/env python3
"""
History Fetcher for Binance Vision Data
Downloads historical trading data and processes it into organized formats
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('history_fetcher.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BinanceVisionFetcher:
    """Fetches historical data from Binance Vision"""
    
    def __init__(self, base_dir: str = "/srv/trading-bots/history"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        self.raw_dir = self.base_dir / "raw"
        self.csv_dir = self.base_dir / "csv"
        self.parquet_dir = self.base_dir / "parquet"
        
        for dir_path in [self.raw_dir, self.csv_dir, self.parquet_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Binance Vision base URL
        self.base_url = "https://data.binance.vision/api/data"
        
        # Supported intervals and symbols
        self.intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
        
        # Initialize manifest
        self.manifest_path = self.base_dir / "manifest.json"
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict:
        """Load or create manifest file"""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
        
        # Create new manifest
        manifest = {
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "data": {},
            "statistics": {
                "total_files": 0,
                "total_size_bytes": 0,
                "symbols": {},
                "intervals": {}
            }
        }
        self._save_manifest(manifest)
        return manifest
    
    def _save_manifest(self, manifest: Dict):
        """Save manifest to file"""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
    
    def _update_manifest(self, symbol: str, interval: str, file_info: Dict):
        """Update manifest with new file information"""
        if symbol not in self.manifest["data"]:
            self.manifest["data"][symbol] = {}
        
        if interval not in self.manifest["data"][symbol]:
            self.manifest["data"][symbol][interval] = []
        
        # Check if file already exists
        existing_files = [f["filename"] for f in self.manifest["data"][symbol][interval]]
        if file_info["filename"] not in existing_files:
            self.manifest["data"][symbol][interval].append(file_info)
            self.manifest["statistics"]["total_files"] += 1
            self.manifest["statistics"]["total_size_bytes"] += file_info["size_bytes"]
        
        # Update statistics
        if symbol not in self.manifest["statistics"]["symbols"]:
            self.manifest["statistics"]["symbols"][symbol] = 0
        if interval not in self.manifest["statistics"]["intervals"]:
            self.manifest["statistics"]["intervals"][interval] = 0
        
        self.manifest["statistics"]["symbols"][symbol] += 1
        self.manifest["statistics"]["intervals"][interval] += 1
        
        self.manifest["last_updated"] = datetime.utcnow().isoformat()
        self._save_manifest(self.manifest)
    
    def _download_file(self, url: str, filepath: Path, force: bool = False) -> bool:
        """Download a file from URL"""
        if filepath.exists() and not force:
            logger.info(f"File already exists: {filepath}")
            return True
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filepath.name) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            logger.info(f"Downloaded: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            if filepath.exists():
                filepath.unlink()  # Remove partial file
            return False
    
    def _process_csv_to_parquet(self, csv_path: Path, parquet_path: Path):
        """Convert CSV to optimized Parquet format"""
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Rename columns for clarity
            df.columns = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ]
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Convert numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'taker_buy_base', 'taker_buy_quote']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Create partitioned directory structure
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to Parquet with partitioning
            df.to_parquet(
                parquet_path,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            logger.info(f"Converted to Parquet: {parquet_path}")
            
        except Exception as e:
            logger.error(f"Failed to convert {csv_path} to Parquet: {e}")
    
    def fetch_data(self, symbol: str, interval: str, from_date: str, to_date: str, 
                   fill_daily: bool = False, force: bool = False) -> bool:
        """Fetch data for specific symbol, interval, and date range"""
        logger.info(f"Fetching {symbol} {interval} data from {from_date} to {to_date}")
        
        # Parse dates
        start_date = datetime.strptime(from_date, "%Y-%m")
        end_date = datetime.strptime(to_date, "%Y-%m")
        
        current_date = start_date
        success_count = 0
        total_count = 0
        
        while current_date <= end_date:
            # Format date for filename
            date_str = current_date.strftime("%Y-%m")
            filename = f"{symbol}-{interval}-{date_str}.zip"
            
            # URLs for different data types
            urls = [
                f"{self.base_url}/klines/{symbol}/{interval}/{filename}",
                f"{self.base_url}/trades/{symbol}/{filename}",
                f"{self.base_url}/aggTrades/{symbol}/{filename}"
            ]
            
            for url in urls:
                try:
                    # Determine file type from URL
                    if "klines" in url:
                        file_type = "klines"
                        csv_filename = f"{symbol}-{interval}-{date_str}.csv"
                        parquet_filename = f"{symbol}-{interval}-{date_str}.parquet"
                    elif "trades" in url:
                        file_type = "trades"
                        csv_filename = f"{symbol}-trades-{date_str}.csv"
                        parquet_filename = f"{symbol}-trades-{date_str}.parquet"
                    elif "aggTrades" in url:
                        file_type = "aggTrades"
                        csv_filename = f"{symbol}-aggTrades-{date_str}.csv"
                        parquet_filename = f"{symbol}-aggTrades-{date_str}.parquet"
                    else:
                        continue
                    
                    # Download file
                    zip_path = self.raw_dir / filename
                    csv_path = self.csv_dir / csv_filename
                    parquet_path = self.parquet_dir / symbol / interval / date_str / parquet_filename
                    
                    # Create directories
                    parquet_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Download if needed
                    if self._download_file(url, zip_path, force):
                        # Extract and process
                        try:
                            import zipfile
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                zip_ref.extractall(self.csv_dir)
                            
                            # Process to Parquet
                            if csv_path.exists():
                                self._process_csv_to_parquet(csv_path, parquet_path)
                                
                                # Update manifest
                                file_info = {
                                    "filename": filename,
                                    "file_type": file_type,
                                    "date": date_str,
                                    "size_bytes": zip_path.stat().st_size,
                                    "csv_path": str(csv_path),
                                    "parquet_path": str(parquet_path),
                                    "downloaded_at": datetime.utcnow().isoformat()
                                }
                                self._update_manifest(symbol, interval, file_info)
                                
                                success_count += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to process {filename}: {e}")
                    
                    total_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process {url}: {e}")
            
            # Move to next month
            current_date += relativedelta(months=1)
            
            # Add daily data if requested
            if fill_daily and interval in ["1h", "4h"]:
                # Download daily data for gaps
                daily_filename = f"{symbol}-1d-{date_str}.zip"
                daily_url = f"{self.base_url}/klines/{symbol}/1d/{daily_filename}"
                daily_path = self.raw_dir / daily_filename
                
                if self._download_file(daily_url, daily_path, force):
                    logger.info(f"Downloaded daily data: {daily_filename}")
        
        logger.info(f"Completed: {success_count}/{total_count} files processed successfully")
        return success_count > 0
    
    def get_manifest_summary(self) -> Dict:
        """Get summary of available data"""
        return {
            "total_files": self.manifest["statistics"]["total_files"],
            "total_size_mb": round(self.manifest["statistics"]["total_size_bytes"] / (1024 * 1024), 2),
            "symbols": list(self.manifest["data"].keys()),
            "intervals": list(self.manifest["statistics"]["intervals"].keys()),
            "last_updated": self.manifest["last_updated"]
        }
    
    def cleanup_old_files(self, days: int = 30):
        """Clean up old raw files to save space"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        for file_path in self.raw_dir.glob("*.zip"):
            if file_path.stat().st_mtime < cutoff_time.timestamp():
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up {file_path}: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Binance Vision History Fetcher")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol (default: BTCUSDT)")
    parser.add_argument("--interval", default="5m", help="Time interval (default: 5m)")
    parser.add_argument("--from", dest="from_date", default="2019-01", help="Start date YYYY-MM (default: 2019-01)")
    parser.add_argument("--to", dest="to_date", default="2025-08", help="End date YYYY-MM (default: 2025-08)")
    parser.add_argument("--fill-daily", action="store_true", help="Fill gaps with daily data")
    parser.add_argument("--force", action="store_true", help="Force re-download existing files")
    parser.add_argument("--base-dir", default="/srv/trading-bots/history", help="Base directory for data storage")
    
    args = parser.parse_args()
    
    # Initialize fetcher
    fetcher = BinanceVisionFetcher(args.base_dir)
    
    # Fetch data
    success = fetcher.fetch_data(
        symbol=args.symbol,
        interval=args.interval,
        from_date=args.from_date,
        to_date=args.to_date,
        fill_daily=args.fill_daily,
        force=args.force
    )
    
    if success:
        # Print summary
        summary = fetcher.get_manifest_summary()
        logger.info("=== FETCH SUMMARY ===")
        logger.info(f"Total files: {summary['total_files']}")
        logger.info(f"Total size: {summary['total_size_mb']} MB")
        logger.info(f"Symbols: {', '.join(summary['symbols'])}")
        logger.info(f"Intervals: {', '.join(summary['intervals'])}")
        logger.info(f"Last updated: {summary['last_updated']}")
        
        # Cleanup old files
        fetcher.cleanup_old_files()
        
        logger.info("History fetching completed successfully!")
    else:
        logger.error("History fetching failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
