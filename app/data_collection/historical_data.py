import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import ccxt
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data structure for historical analysis"""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    symbol: str


@dataclass
class DataCollectionConfig:
    """Configuration for data collection"""

    symbols: List[str]
    timeframes: List[str]
    start_date: str  # YYYY-MM-DD format
    end_date: str  # YYYY-MM-DD format
    data_dir: str
    max_retries: int = 3
    rate_limit_delay: float = 0.1


class HistoricalDataCollector:
    """Safe historical data collector that doesn't interfere with trading bot"""

    def __init__(self, config: DataCollectionConfig):
        self.config = config
        self.exchange = ccxt.binanceus({"enableRateLimit": True})
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Performance monitoring
        self.collection_stats = {
            "total_candles": 0,
            "total_size_mb": 0,
            "start_time": None,
            "end_time": None,
            "errors": 0,
            "retries": 0,
        }

        # Safety checks
        self.max_memory_mb = 512  # Max memory usage for data collection
        self.max_disk_gb = 10  # Max disk usage for data storage

    def _check_system_resources(self) -> bool:
        """Check if system has enough resources for data collection"""
        try:
            import psutil

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                logger.warning(f"High memory usage: {memory.percent}%")
                return False

            # Check disk space
            disk = psutil.disk_usage(self.data_dir)
            free_gb = disk.free / (1024**3)
            if free_gb < 5:  # Need at least 5GB free
                logger.warning(f"Low disk space: {free_gb:.2f}GB free")
                return False

            return True

        except ImportError:
            # If psutil not available, assume resources are OK
            return True

    def _safe_fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int, limit: int = 1000
    ) -> List[MarketData]:
        """Safely fetch OHLCV data with error handling and rate limiting"""
        try:
            # Rate limiting to prevent API abuse
            time.sleep(self.config.rate_limit_delay)

            # Fetch data from exchange
            ohlcv_data = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)

            # Convert to MarketData objects
            market_data = []
            for candle in ohlcv_data:
                if len(candle) >= 6:  # Ensure we have all required fields
                    data = MarketData(
                        timestamp=candle[0],
                        open=candle[1],
                        high=candle[2],
                        low=candle[3],
                        close=candle[4],
                        volume=candle[5],
                        timeframe=timeframe,
                        symbol=symbol,
                    )
                    market_data.append(data)

            return market_data

        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe} data: {e}")
            self.collection_stats["errors"] += 1
            return []

    def _save_data_safely(self, data: List[MarketData], filename: str) -> bool:
        """Safely save data to disk with error handling"""
        try:
            filepath = self.data_dir / filename

            # Convert dataclass objects to dictionaries
            data_dicts = [asdict(d) for d in data]

            # Save as JSON with compression
            with open(filepath, "w") as f:
                json.dump(data_dicts, f, indent=2)

            # Update collection stats
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            self.collection_stats["total_size_mb"] += file_size_mb
            self.collection_stats["total_candles"] += len(data)

            logger.info(
                f"Saved {len(data)} candles to {filename} ({file_size_mb:.2f}MB)"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
            self.collection_stats["errors"] += 1
            return False

    def collect_historical_data(self) -> Dict[str, Any]:
        """Main method to collect historical data safely"""
        logger.info("Starting historical data collection...")
        self.collection_stats["start_time"] = datetime.now().isoformat()

        # Check system resources before starting
        if not self._check_system_resources():
            logger.error("Insufficient system resources for data collection")
            return {"status": "error", "message": "Insufficient system resources"}

        try:
            # Load markets to ensure exchange connection
            self.exchange.load_markets()

            # Calculate date range
            start_date = datetime.strptime(self.config.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.config.end_date, "%Y-%m-%d")

            # Convert to timestamps
            since_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)

            # Collect data for each symbol and timeframe
            for symbol in self.config.symbols:
                for timeframe in self.config.timeframes:
                    logger.info(f"Collecting {symbol} {timeframe} data...")

                    # Calculate timeframe milliseconds
                    tf_ms = self._get_timeframe_ms(timeframe)
                    if not tf_ms:
                        logger.warning(f"Invalid timeframe: {timeframe}")
                        continue

                    # Collect data in chunks
                    current_ts = since_ts
                    all_data = []

                    while current_ts < end_ts:
                        # Check system resources periodically
                        if (
                            len(all_data) % 10000 == 0
                            and not self._check_system_resources()
                        ):
                            logger.warning(
                                "System resources low, pausing collection..."
                            )
                            time.sleep(60)  # Wait 1 minute

                        # Fetch data chunk
                        data_chunk = self._safe_fetch_ohlcv(
                            symbol, timeframe, current_ts, 1000
                        )

                        if not data_chunk:
                            logger.warning(
                                f"No data received for {symbol} {timeframe} at {current_ts}"
                            )
                            break

                        all_data.extend(data_chunk)

                        # Move to next chunk
                        if len(data_chunk) > 0:
                            current_ts = data_chunk[-1].timestamp + tf_ms
                        else:
                            current_ts += tf_ms * 1000  # Move forward by 1000 bars

                        # Safety check - don't collect too much data at once
                        if len(all_data) > 100000:  # 100k candles max per session
                            logger.info(
                                f"Reached safety limit for {symbol} {timeframe}, saving data..."
                            )
                            break

                    # Save collected data
                    if all_data:
                        filename = f"{symbol.replace('/', '_')}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
                        self._save_data_safely(all_data, filename)

                    # Rate limiting between symbols/timeframes
                    time.sleep(1)

            # Save collection manifest
            self._save_collection_manifest()

            self.collection_stats["end_time"] = datetime.now().isoformat()
            logger.info("Historical data collection completed successfully")

            return {
                "status": "success",
                "stats": self.collection_stats,
                "message": "Historical data collection completed",
            }

        except Exception as e:
            logger.error(f"Error during data collection: {e}")
            self.collection_stats["end_time"] = datetime.now().isoformat()
            return {
                "status": "error",
                "message": str(e),
                "stats": self.collection_stats,
            }

    def _get_timeframe_ms(self, timeframe: str) -> Optional[int]:
        """Convert timeframe string to milliseconds"""
        try:
            unit = timeframe[-1]
            n = int(timeframe[:-1])

            multipliers = {
                "s": 1000,  # seconds
                "m": 60000,  # minutes
                "h": 3600000,  # hours
                "d": 86400000,  # days
                "w": 604800000,  # weeks
                "M": 2592000000,  # months (approximate)
            }

            return n * multipliers.get(unit, 0)
        except (ValueError, KeyError):
            return None

    def _save_collection_manifest(self):
        """Save collection manifest with metadata"""
        manifest = {
            "collection_date": datetime.now().isoformat(),
            "config": asdict(self.config),
            "stats": self.collection_stats,
            "files": [],
        }

        # List all collected data files
        for file_path in self.data_dir.glob("*.json"):
            if file_path.name != "manifest.json":
                file_info = {
                    "filename": file_path.name,
                    "size_mb": file_path.stat().st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                }
                manifest["files"].append(file_info)

        # Save manifest
        manifest_path = self.data_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Collection manifest saved to {manifest_path}")


# Safe configuration for initial testing
DEFAULT_CONFIG = DataCollectionConfig(
    symbols=["BTC/USDT"],
    timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
    start_date="2020-01-01",  # 5+ years of data
    end_date=datetime.now().strftime("%Y-%m-%d"),
    data_dir="/srv/trading-bots/historical_data",
    max_retries=3,
    rate_limit_delay=0.1,
)
