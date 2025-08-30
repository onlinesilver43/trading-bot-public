#!/usr/bin/env python3
"""
Data Preprocessing Pipeline
Handles data cleaning, validation, and preparation for strategy testing
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OHLCVData:
    """OHLCV data structure with validation"""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        """Validate data after initialization"""
        if self.high < max(self.open, self.close):
            raise ValueError(f"High price ({self.high}) must be >= max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError(f"Low price ({self.low}) must be <= min(open, close)")
        if self.volume < 0:
            raise ValueError(f"Volume ({self.volume}) must be >= 0")


class DataPreprocessor:
    """Data preprocessing pipeline for market data"""

    def __init__(self):
        self.validation_errors = []
        self.cleaning_stats = {
            "total_records": 0,
            "valid_records": 0,
            "cleaned_records": 0,
            "removed_records": 0,
            "outliers_removed": 0,
        }

    def generate_synthetic_data(
        self,
        days: int = 365,
        base_price: float = 100.0,
        volatility: float = 0.02,
        trend: float = 0.0001,
    ) -> List[OHLCVData]:
        """Generate synthetic OHLCV data for testing"""
        logger.info(f"Generating {days} days of synthetic data...")

        np.random.seed(42)  # For reproducible results
        data = []
        current_price = base_price
        current_time = int(datetime.now().timestamp() * 1000)

        for i in range(days):
            # Generate daily OHLCV data
            # Random walk with trend and volatility
            daily_return = np.random.normal(trend, volatility)
            current_price *= 1 + daily_return

            # Generate OHLC from daily return
            daily_volatility = abs(daily_return) * 0.5
            open_price = current_price
            close_price = current_price * (
                1 + np.random.normal(0, daily_volatility * 0.3)
            )
            high_price = max(open_price, close_price) * (
                1 + abs(np.random.normal(0, daily_volatility * 0.2))
            )
            low_price = min(open_price, close_price) * (
                1 - abs(np.random.normal(0, daily_volatility * 0.2))
            )

            # Generate volume (correlated with price movement)
            volume = np.random.lognormal(10, 0.5) * (1 + abs(daily_return) * 10)

            # Create OHLCV data point
            ohlcv = OHLCVData(
                timestamp=current_time + (i * 24 * 60 * 60 * 1000),  # Daily intervals
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )

            data.append(ohlcv)

        logger.info(f"Generated {len(data)} synthetic OHLCV records")
        return data

    def validate_data(self, data: List[OHLCVData]) -> Tuple[List[OHLCVData], List[str]]:
        """Validate OHLCV data for consistency and quality"""
        logger.info("Validating data quality...")

        valid_data = []
        errors = []

        for i, record in enumerate(data):
            try:
                # Basic OHLCV validation
                if record.high < max(record.open, record.close):
                    errors.append(
                        f"Record {i}: High price ({record.high}) < max(open, close)"
                    )
                    continue

                if record.low > min(record.open, record.close):
                    errors.append(
                        f"Record {i}: Low price ({record.low}) > min(open, close)"
                    )
                    continue

                if record.volume < 0:
                    errors.append(f"Record {i}: Negative volume ({record.volume})")
                    continue

                # Price sanity checks
                if record.close <= 0 or record.open <= 0:
                    errors.append(f"Record {i}: Non-positive prices")
                    continue

                # Volume sanity checks
                if record.volume > 1e12:  # Unrealistic volume
                    errors.append(f"Record {i}: Unrealistic volume ({record.volume})")
                    continue

                valid_data.append(record)

            except Exception as e:
                errors.append(f"Record {i}: Validation error - {e}")
                continue

        self.validation_errors = errors
        self.cleaning_stats["total_records"] = len(data)
        self.cleaning_stats["valid_records"] = len(valid_data)

        logger.info(f"Validation complete: {len(valid_data)}/{len(data)} records valid")
        if errors:
            logger.warning(f"Found {len(errors)} validation errors")

        return valid_data, errors

    def clean_data(
        self,
        data: List[OHLCVData],
        remove_outliers: bool = True,
        outlier_threshold: float = 3.0,
        fill_gaps: bool = True,
    ) -> List[OHLCVData]:
        """Clean and normalize the data"""
        logger.info("Cleaning and normalizing data...")

        if not data:
            return []

        # Convert to pandas for easier manipulation
        df = pd.DataFrame(
            [
                {
                    "timestamp": d.timestamp,
                    "open": d.open,
                    "high": d.high,
                    "low": d.low,
                    "close": d.close,
                    "volume": d.volume,
                }
                for d in data
            ]
        )

        original_count = len(df)

        # Remove outliers if requested
        if remove_outliers:
            # Calculate price change outliers
            df["price_change"] = df["close"].pct_change().abs()
            price_threshold = (
                df["price_change"].mean() + outlier_threshold * df["price_change"].std()
            )

            # Calculate volume outliers
            volume_threshold = (
                df["volume"].mean() + outlier_threshold * df["volume"].std()
            )

            # Remove outliers
            outliers_mask = (df["price_change"] > price_threshold) | (
                df["volume"] > volume_threshold
            )
            outliers_removed = outliers_mask.sum()

            if outliers_removed > 0:
                df = df[~outliers_mask]
                logger.info(f"Removed {outliers_removed} outlier records")
                self.cleaning_stats["outliers_removed"] = outliers_removed

        # Fill gaps if requested
        if fill_gaps:
            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Calculate expected time intervals
            time_diffs = df["timestamp"].diff()
            expected_interval = (
                time_diffs.mode().iloc[0] if len(time_diffs) > 1 else 86400000
            )  # Default to 1 day

            # Find gaps
            gaps = time_diffs > expected_interval * 1.5

            if gaps.any():
                gap_count = gaps.sum()
                logger.info(
                    f"Found {gap_count} time gaps, filling with interpolation..."
                )

                # Create complete timestamp range
                full_range = pd.date_range(
                    start=pd.to_datetime(df["timestamp"].min(), unit="ms"),
                    end=pd.to_datetime(df["timestamp"].max(), unit="ms"),
                    freq="D",
                )

                # Reindex and interpolate
                df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("date").reindex(full_range)

                # Interpolate missing values
                df = df.interpolate(method="linear")

                # Convert back to timestamp
                df["timestamp"] = df.index.astype(np.int64) // 10**6
                df = df.reset_index(drop=True)

        # Normalize data
        df = self._normalize_data(df)

        # Convert back to OHLCVData objects
        cleaned_data = []
        for _, row in df.iterrows():
            try:
                ohlcv = OHLCVData(
                    timestamp=int(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                cleaned_data.append(ohlcv)
            except Exception as e:
                logger.warning(f"Error creating OHLCV record: {e}")
                continue

        self.cleaning_stats["cleaned_records"] = len(cleaned_data)
        self.cleaning_stats["removed_records"] = original_count - len(cleaned_data)

        logger.info(
            f"Data cleaning complete: {len(cleaned_data)}/{original_count} records retained"
        )
        return cleaned_data

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data for consistent scaling"""
        # Ensure all prices are positive
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            df[col] = df[col].abs()

        # Ensure high >= max(open, close) and low <= min(open, close)
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        # Normalize volume to reasonable range
        if df["volume"].max() > 0:
            df["volume"] = df["volume"] / df["volume"].max() * 1000

        return df

    def calculate_technical_indicators(
        self, data: List[OHLCVData]
    ) -> Dict[str, List[float]]:
        """Calculate common technical indicators"""
        logger.info("Calculating technical indicators...")

        if not data:
            return {}

        # Extract price data
        closes = [d.close for d in data]
        volumes = [d.volume for d in data]

        indicators = {}

        # Simple Moving Averages
        indicators["sma_20"] = self._calculate_sma(closes, 20)
        indicators["sma_50"] = self._calculate_sma(closes, 50)
        indicators["sma_200"] = self._calculate_sma(closes, 200)

        # Exponential Moving Averages
        indicators["ema_12"] = self._calculate_ema(closes, 12)
        indicators["ema_26"] = self._calculate_ema(closes, 26)

        # RSI
        indicators["rsi_14"] = self._calculate_rsi(closes, 14)

        # MACD
        macd_line, signal_line = self._calculate_macd(closes)
        indicators["macd_line"] = macd_line
        indicators["signal_line"] = signal_line

        # Bollinger Bands
        bb_upper, bb_lower = self._calculate_bollinger_bands(closes, 20, 2)
        indicators["bb_upper"] = bb_upper
        indicators["bb_lower"] = bb_lower

        # Volume indicators
        indicators["volume_sma"] = self._calculate_sma(volumes, 20)
        indicators["volume_ratio"] = [
            (
                v / indicators["volume_sma"][i]
                if i < len(indicators["volume_sma"])
                else 1.0
            )
            for i, v in enumerate(volumes)
        ]

        logger.info(f"Calculated {len(indicators)} technical indicators")
        return indicators

    def _calculate_sma(self, data: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return []

        sma = []
        for i in range(period - 1, len(data)):
            sma.append(sum(data[i - period + 1 : i + 1]) / period)

        return sma

    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return []

        ema = []
        multiplier = 2 / (period + 1)

        # First EMA is SMA
        first_sma = sum(data[:period]) / period
        ema.append(first_sma)

        for i in range(period, len(data)):
            ema_value = (data[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(ema_value)

        return ema

    def _calculate_rsi(self, data: List[float], period: int) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return []

        rsi = []
        gains = []
        losses = []

        # Calculate price changes
        for i in range(1, len(data)):
            change = data[i] - data[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        # Calculate RSI
        for i in range(period, len(gains)):
            avg_gain = sum(gains[i - period : i]) / period
            avg_loss = sum(losses[i - period : i]) / period

            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_value = 100 - (100 / (1 + rs))
                rsi.append(rsi_value)

        return rsi

    def _calculate_macd(self, data: List[float]) -> Tuple[List[float], List[float]]:
        """Calculate MACD line and signal line"""
        if len(data) < 26:
            return [], []

        ema_12 = self._calculate_ema(data, 12)
        ema_26 = self._calculate_ema(data, 26)

        # MACD line
        macd_line = []
        for i in range(len(ema_26)):
            if i < len(ema_12):
                macd_line.append(ema_12[i] - ema_26[i])
            else:
                macd_line.append(0)

        # Signal line (9-period EMA of MACD)
        signal_line = self._calculate_ema(macd_line, 9)

        return macd_line, signal_line

    def _calculate_bollinger_bands(
        self, data: List[float], period: int, std_dev: float
    ) -> Tuple[List[float], List[float]]:
        """Calculate Bollinger Bands"""
        if len(data) < period:
            return [], []

        bb_upper = []
        bb_lower = []

        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            sma = sum(window) / period
            variance = sum((x - sma) ** 2 for x in window) / period
            std = variance**0.5

            bb_upper.append(sma + (std_dev * std))
            bb_lower.append(sma - (std_dev * std))

        return bb_upper, bb_lower

    def export_data(
        self, data: List[OHLCVData], indicators: Dict[str, List[float]], filename: str
    ) -> bool:
        """Export processed data to file"""
        try:
            # Create output directory
            output_dir = Path("processed_data")
            output_dir.mkdir(exist_ok=True)

            # Prepare data for export
            export_data = []
            for i, record in enumerate(data):
                row = {
                    "timestamp": record.timestamp,
                    "open": record.open,
                    "high": record.high,
                    "low": record.low,
                    "close": record.close,
                    "volume": record.volume,
                }

                # Add indicators
                for indicator_name, indicator_values in indicators.items():
                    if i < len(indicator_values):
                        row[indicator_name] = indicator_values[i]
                    else:
                        row[indicator_name] = None

                export_data.append(row)

            # Convert to DataFrame and export
            df = pd.DataFrame(export_data)
            output_path = output_dir / filename

            if filename.endswith(".csv"):
                df.to_csv(output_path, index=False)
            elif filename.endswith(".json"):
                df.to_json(output_path, orient="records", indent=2)
            else:
                df.to_csv(output_path.with_suffix(".csv"), index=False)

            logger.info(f"Data exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False

    def get_cleaning_stats(self) -> Dict[str, Any]:
        """Get data cleaning statistics"""
        return self.cleaning_stats.copy()


# Example usage and testing
if __name__ == "__main__":
    # Test the data preprocessor
    preprocessor = DataPreprocessor()

    print("🧪 Testing Data Preprocessing Pipeline...")

    # Generate synthetic data
    print("\n📊 Generating synthetic data...")
    synthetic_data = preprocessor.generate_synthetic_data(days=100)
    print(f"   Generated {len(synthetic_data)} records")

    # Validate data
    print("\n✅ Validating data...")
    valid_data, errors = preprocessor.validate_data(synthetic_data)
    print(f"   Valid records: {len(valid_data)}")
    print(f"   Validation errors: {len(errors)}")

    # Clean data
    print("\n🧹 Cleaning data...")
    cleaned_data = preprocessor.clean_data(
        valid_data, remove_outliers=True, fill_gaps=True
    )
    print(f"   Cleaned records: {len(cleaned_data)}")

    # Calculate indicators
    print("\n📈 Calculating technical indicators...")
    indicators = preprocessor.calculate_technical_indicators(cleaned_data)
    print(f"   Calculated {len(indicators)} indicators:")
    for name, values in indicators.items():
        print(f"     {name}: {len(values)} values")

    # Export data
    print("\n💾 Exporting processed data...")
    success = preprocessor.export_data(cleaned_data, indicators, "test_data.csv")
    print(f"   Export successful: {success}")

    # Show cleaning stats
    print("\n📊 Data Cleaning Statistics:")
    stats = preprocessor.get_cleaning_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Data preprocessing pipeline test completed!")
