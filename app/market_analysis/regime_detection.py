import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types"""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


@dataclass
class RegimeMetrics:
    """Market regime metrics and indicators"""

    regime: MarketRegime
    confidence: float  # 0.0 to 1.0
    trend_strength: float  # -1.0 to 1.0 (negative = bearish, positive = bullish)
    volatility: float  # 0.0 to 1.0
    volume_trend: float  # -1.0 to 1.0
    momentum: float  # -1.0 to 1.0
    timestamp: int
    indicators: Dict[str, float]


class MarketRegimeDetector:
    """Real-time market regime detection system"""

    def __init__(self, lookback_periods: int = 100):
        self.lookback_periods = lookback_periods
        self.regime_history: List[RegimeMetrics] = []

        # Regime detection thresholds
        self.trend_threshold = 0.02  # 2% trend strength threshold
        self.volatility_threshold = 0.03  # 3% volatility threshold
        self.volume_threshold = 0.5  # Volume trend threshold
        self.momentum_threshold = 0.01  # Momentum threshold

        # Performance monitoring
        self.detection_stats = {
            "total_detections": 0,
            "regime_changes": 0,
            "last_regime": MarketRegime.UNKNOWN,
            "processing_time_ms": 0,
        }

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)

        ema = [None] * len(prices)
        ema[period - 1] = sum(prices[:period]) / period

        multiplier = 2 / (period + 1)

        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier))

        return ema

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)

        rsi = [None] * len(prices)
        gains = []
        losses = []

        # Calculate price changes
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Calculate RSI for first valid period
        if avg_loss == 0:
            rsi[period] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100 - (100 / (1 + rs))

        # Calculate RSI for remaining periods
        for i in range(period + 1, len(prices)):
            gain = gains[i - 1]
            loss = losses[i - 1]

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> List[float]:
        """Calculate Average True Range for volatility measurement"""
        if len(highs) < period + 1:
            return [None] * len(highs)

        atr = [None] * len(highs)
        true_ranges = []

        # Calculate True Range for first period
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(tr1, tr2, tr3))

        # Calculate initial ATR
        atr[period] = sum(true_ranges[:period]) / period

        # Calculate ATR for remaining periods
        for i in range(period + 1, len(highs)):
            tr = true_ranges[i - 1]
            atr[i] = (atr[i - 1] * (period - 1) + tr) / period

        return atr

    def _calculate_volume_trend(self, volumes: List[float], period: int = 20) -> float:
        """Calculate volume trend strength"""
        if len(volumes) < period:
            return 0.0

        recent_volumes = volumes[-period:]
        earlier_volumes = (
            volumes[-2 * period : -period]
            if len(volumes) >= 2 * period
            else volumes[:-period]
        )

        if not earlier_volumes:
            return 0.0

        recent_avg = np.mean(recent_volumes)
        earlier_avg = np.mean(earlier_volumes)

        if earlier_avg == 0:
            return 0.0

        volume_change = (recent_avg - earlier_avg) / earlier_avg
        return np.clip(volume_change, -1.0, 1.0)

    def _calculate_momentum(self, prices: List[float], period: int = 10) -> float:
        """Calculate price momentum"""
        if len(prices) < period:
            return 0.0

        recent_prices = prices[-period:]
        earlier_prices = (
            prices[-2 * period : -period]
            if len(prices) >= 2 * period
            else prices[:-period]
        )

        if not earlier_prices:
            return 0.0

        recent_avg = np.mean(recent_prices)
        earlier_avg = np.mean(earlier_prices)

        if earlier_avg == 0:
            return 0.0

        momentum = (recent_avg - earlier_avg) / earlier_avg
        return np.clip(momentum, -1.0, 1.0)

    def detect_regime(self, market_data: List[Dict]) -> RegimeMetrics:
        """Detect current market regime from market data"""
        import time

        start_time = time.time()

        try:
            # Extract price and volume data
            closes = [float(candle["close"]) for candle in market_data]
            highs = [float(candle["high"]) for candle in market_data]
            lows = [float(candle["low"]) for candle in market_data]
            volumes = [float(candle["volume"]) for candle in market_data]

            if len(closes) < self.lookback_periods:
                logger.warning(
                    f"Insufficient data for regime detection: {len(closes)} < {self.lookback_periods}"
                )
                return RegimeMetrics(
                    regime=MarketRegime.UNKNOWN,
                    confidence=0.0,
                    trend_strength=0.0,
                    volatility=0.0,
                    volume_trend=0.0,
                    momentum=0.0,
                    timestamp=market_data[-1]["timestamp"] if market_data else 0,
                    indicators={},
                )

            # Calculate technical indicators
            ema_20 = self._calculate_ema(closes, 20)
            ema_50 = self._calculate_ema(closes, 50)
            rsi = self._calculate_rsi(closes, 14)
            atr = self._calculate_atr(highs, lows, closes, 14)

            # Get latest values
            current_close = closes[-1]
            current_ema_20 = ema_20[-1]
            current_ema_50 = ema_50[-1]
            current_rsi = rsi[-1]
            current_atr = atr[-1]

            # Calculate trend strength
            if current_ema_20 and current_ema_50 and current_close:
                trend_strength = (current_ema_20 - current_ema_50) / current_close
                trend_strength = np.clip(trend_strength, -1.0, 1.0)
            else:
                trend_strength = 0.0

            # Calculate volatility
            if current_atr and current_close:
                volatility = current_atr / current_close
                volatility = np.clip(volatility, 0.0, 1.0)
            else:
                volatility = 0.0

            # Calculate volume trend
            volume_trend = self._calculate_volume_trend(volumes, 20)

            # Calculate momentum
            momentum = self._calculate_momentum(closes, 10)

            # Determine market regime
            regime = self._classify_regime(
                trend_strength, volatility, volume_trend, momentum, current_rsi
            )

            # Calculate confidence
            confidence = self._calculate_confidence(
                trend_strength, volatility, volume_trend, momentum
            )

            # Create regime metrics
            metrics = RegimeMetrics(
                regime=regime,
                confidence=confidence,
                trend_strength=trend_strength,
                volatility=volatility,
                volume_trend=volume_trend,
                momentum=momentum,
                timestamp=market_data[-1]["timestamp"],
                indicators={
                    "ema_20": current_ema_20,
                    "ema_50": current_ema_50,
                    "rsi": current_rsi,
                    "atr": current_atr,
                    "close": current_close,
                },
            )

            # Update regime history
            self.regime_history.append(metrics)
            if len(self.regime_history) > 1000:  # Keep last 1000 detections
                self.regime_history = self.regime_history[-1000:]

            # Update detection stats
            self.detection_stats["total_detections"] += 1
            if self.detection_stats["last_regime"] != regime:
                self.detection_stats["regime_changes"] += 1
            self.detection_stats["last_regime"] = regime

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            self.detection_stats["processing_time_ms"] = processing_time

            logger.info(
                f"Regime detected: {regime.value} (confidence: {confidence:.2f}, trend: {trend_strength:.3f}, volatility: {volatility:.3f})"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error in regime detection: {e}")
            return RegimeMetrics(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                trend_strength=0.0,
                volatility=0.0,
                volume_trend=0.0,
                momentum=0.0,
                timestamp=market_data[-1]["timestamp"] if market_data else 0,
                indicators={},
            )

    def _classify_regime(
        self,
        trend_strength: float,
        volatility: float,
        volume_trend: float,
        momentum: float,
        rsi: float,
    ) -> MarketRegime:
        """Classify market regime based on indicators"""

        # High volatility regime
        if volatility > self.volatility_threshold:
            return MarketRegime.VOLATILE

        # Strong trend regimes
        if abs(trend_strength) > self.trend_threshold:
            if trend_strength > 0 and volume_trend > self.volume_threshold:
                return MarketRegime.BULL
            elif trend_strength < 0 and volume_trend > self.volume_threshold:
                return MarketRegime.BEAR

        # Sideways regime (low trend, low volatility)
        if (
            abs(trend_strength) < self.trend_threshold * 0.5
            and volatility < self.volatility_threshold * 0.5
        ):
            return MarketRegime.SIDEWAYS

        # Momentum-based classification
        if abs(momentum) > self.momentum_threshold:
            if momentum > 0 and rsi and rsi < 70:
                return MarketRegime.BULL
            elif momentum < 0 and rsi and rsi > 30:
                return MarketRegime.BEAR

        # Default to sideways if unclear
        return MarketRegime.SIDEWAYS

    def _calculate_confidence(
        self,
        trend_strength: float,
        volatility: float,
        volume_trend: float,
        momentum: float,
    ) -> float:
        """Calculate confidence level of regime detection"""
        confidence_factors = []

        # Trend strength confidence
        trend_confidence = min(abs(trend_strength) / self.trend_threshold, 1.0)
        confidence_factors.append(trend_confidence)

        # Volume trend confidence
        volume_confidence = min(abs(volume_trend), 1.0)
        confidence_factors.append(volume_confidence)

        # Momentum confidence
        momentum_confidence = min(abs(momentum) / self.momentum_threshold, 1.0)
        confidence_factors.append(momentum_confidence)

        # Volatility confidence (lower volatility = higher confidence for trend regimes)
        volatility_confidence = 1.0 - min(volatility / self.volatility_threshold, 1.0)
        confidence_factors.append(volatility_confidence)

        # Average confidence
        return np.mean(confidence_factors)

    def get_regime_summary(self) -> Dict:
        """Get summary of regime detection performance"""
        if not self.regime_history:
            return {"message": "No regime detection history available"}

        # Current regime
        current_regime = self.regime_history[-1]

        # Regime distribution
        regime_counts = {}
        for metrics in self.regime_history:
            regime = metrics.regime.value
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        # Performance metrics
        avg_confidence = np.mean([m.confidence for m in self.regime_history])
        avg_processing_time = np.mean([m.timestamp for m in self.regime_history])

        return {
            "current_regime": {
                "regime": current_regime.regime.value,
                "confidence": current_regime.confidence,
                "trend_strength": current_regime.trend_strength,
                "volatility": current_regime.volatility,
                "timestamp": current_regime.timestamp,
            },
            "regime_distribution": regime_counts,
            "performance": {
                "total_detections": self.detection_stats["total_detections"],
                "regime_changes": self.detection_stats["regime_changes"],
                "avg_confidence": avg_confidence,
                "avg_processing_time_ms": avg_processing_time,
            },
            "detection_stats": self.detection_stats,
        }
