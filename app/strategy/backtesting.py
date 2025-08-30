#!/usr/bin/env python3
"""
Backtesting Framework
Tests strategies against historical data with market regime integration
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .sma_crossover import decide, indicators
from .performance_db import StrategyPerformanceDB, TradeRecord
from ..market_analysis.regime_detection import MarketRegimeDetector
from ..data_collection.data_preprocessor import DataPreprocessor, OHLCVData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""

    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    position_size: float = 0.1  # 10% of capital per trade
    commission: float = 0.001  # 0.1% commission per trade
    slippage: float = 0.0005  # 0.05% slippage per trade


@dataclass
class BacktestResult:
    """Results of a backtest"""

    config: BacktestConfig
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    final_capital: float
    trade_history: List[Dict[str, Any]]
    market_regime_stats: Dict[str, int]


class BacktestingEngine:
    """Backtesting engine for trading strategies"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.performance_db = StrategyPerformanceDB("backtest_performance.db")
        self.regime_detector = MarketRegimeDetector()
        self.data_preprocessor = DataPreprocessor()

        # Backtest state
        self.current_capital = config.initial_capital
        self.position = None  # None, "long", or "short"
        self.entry_price = 0.0
        self.entry_time = 0
        self.trades = []

        # Performance tracking
        self.equity_curve = []
        self.drawdown_curve = []
        self.peak_capital = config.initial_capital

    def run_backtest(self, data: List[OHLCVData]) -> BacktestResult:
        """Run backtest on historical data"""
        logger.info(f"Starting backtest for {self.config.strategy_name}")
        logger.info(f"Data points: {len(data)}")
        logger.info(f"Initial capital: ${self.config.initial_capital:,.2f}")

        # Reset state
        self.current_capital = self.config.initial_capital
        self.position = None
        self.entry_price = 0.0
        self.entry_time = 0
        self.trades = []
        self.equity_curve = []
        self.drawdown_curve = []
        self.peak_capital = self.config.initial_capital

        # Process data through strategy
        for i, candle in enumerate(data):
            # Skip early candles that don't have enough data for indicators
            if i < 50:  # Need at least 50 candles for SMA calculations
                self._update_equity_curve(candle.close)
                continue

            # Get market regime for this candle
            regime_info = self._get_market_regime(data, i)

            # Generate strategy signals
            signal = self._generate_signal(data, i, regime_info)

            # Execute trades based on signals
            if signal:
                self._execute_trade(signal, candle, regime_info)

            # Update equity curve
            self._update_equity_curve(candle.close)

            # Record market regime
            self.performance_db.record_market_regime(
                timestamp=candle.timestamp,
                symbol=self.config.symbol,
                regime=regime_info["regime"],
                confidence=regime_info["confidence"],
                trend=regime_info["trend"],
                volatility=regime_info["volatility"],
                volume_trend=regime_info["volume_trend"],
                momentum=regime_info["momentum"],
            )

        # Close any open position at the end
        if self.position:
            self._close_position(data[-1], "end_of_backtest")

        # Calculate final results
        result = self._calculate_results()

        # Save to performance database
        self._save_backtest_results(result)

        logger.info(
            f"Backtest completed: {result.total_trades} trades, ${result.total_pnl:,.2f} PnL"
        )
        return result

    def _get_market_regime(
        self, data: List[OHLCVData], current_index: int
    ) -> Dict[str, Any]:
        """Get market regime for current candle"""
        # Use last 100 candles for regime detection
        start_idx = max(0, current_index - 99)
        window_data = data[start_idx : current_index + 1]

        # Convert to regime detector format
        regime_data = []
        for candle in window_data:
            regime_data.append(
                {
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
            )

        # Detect regime
        regime_result = self.regime_detector.detect_regime(regime_data)

        return {
            "regime": regime_result.regime.value,
            "confidence": regime_result.confidence,
            "trend": regime_result.trend_strength,
            "volatility": regime_result.volatility,
            "volume_trend": regime_result.volume_trend,
            "momentum": regime_result.momentum,
        }

    def _generate_signal(
        self, data: List[OHLCVData], current_index: int, regime_info: Dict[str, Any]
    ) -> Optional[str]:
        """Generate trading signal based on strategy and market regime"""
        try:
            # Get price data for indicators
            closes = [d.close for d in data[: current_index + 1]]

            # Calculate SMAs
            fast_sma, slow_sma = indicators(closes, fast=10, slow=20, closed_only=True)

            if len(fast_sma) < 3 or len(slow_sma) < 3:
                return None

            # Mock configuration for strategy
            class MockConfig:
                confirm_bars = 3
                threshold_pct = 0.01
                min_hold_bars = 5

            config = MockConfig()

            # Generate signal
            signal, reason, cooldown_ok, sep = decide(
                fast_sma,
                slow_sma,
                closes[-1],
                config,
                self.entry_time,
                data[current_index].timestamp,
                86400000,  # Daily timeframe
            )

            # Only trade if cooldown is OK
            if not cooldown_ok:
                return None

            # Filter signals based on market regime
            if (
                regime_info["regime"] == "sideways"
                and abs(regime_info["trend"]) < 0.005
            ):
                # Reduce trading in sideways markets
                if sep < 0.02:  # Higher threshold for sideways markets
                    return None

            return signal if signal != "none" else None

        except Exception as e:
            logger.warning(f"Error generating signal: {e}")
            return None

    def _execute_trade(
        self, signal: str, candle: OHLCVData, regime_info: Dict[str, Any]
    ):
        """Execute a trade based on signal"""
        if signal == "buy" and self.position != "long":
            # Close existing position if any
            if self.position:
                self._close_position(candle, "switch_to_long")

            # Open long position
            self._open_long_position(candle, regime_info)

        elif signal == "sell" and self.position == "long":
            # Close long position
            self._close_position(candle, "signal_sell")

    def _open_long_position(self, candle: OHLCVData, regime_info: Dict[str, Any]):
        """Open a long position"""
        position_value = self.current_capital * self.config.position_size
        shares = position_value / candle.close

        # Apply slippage
        entry_price = candle.close * (1 + self.config.slippage)

        self.position = "long"
        self.entry_price = entry_price
        self.entry_time = candle.timestamp

        # Record trade
        trade_record = TradeRecord(
            timestamp=candle.timestamp,
            strategy_name=self.config.strategy_name,
            symbol=self.config.symbol,
            signal="buy",
            reason="strategy_signal",
            price=entry_price,
            market_regime=regime_info["regime"],
            regime_confidence=regime_info["confidence"],
            regime_trend=regime_info["trend"],
            regime_volatility=regime_info["volatility"],
            volume=candle.volume,
            timeframe=self.config.timeframe,
        )

        self.performance_db.record_trade(trade_record)

        logger.info(f"Opened long position: {shares:.4f} shares at ${entry_price:.2f}")

    def _close_position(self, candle: OHLCVData, reason: str):
        """Close current position"""
        if not self.position:
            return

        # Calculate exit price with slippage
        exit_price = candle.close * (1 - self.config.slippage)

        # Calculate PnL
        if self.position == "long":
            pnl = (exit_price - self.entry_price) / self.entry_price
        else:
            pnl = (self.entry_price - exit_price) / self.entry_price

        # Apply commission
        pnl -= self.config.commission * 2  # Entry and exit

        # Update capital
        position_value = self.current_capital * self.config.position_size
        self.current_capital += position_value * pnl

        # Record trade
        trade_record = TradeRecord(
            timestamp=candle.timestamp,
            strategy_name=self.config.strategy_name,
            symbol=self.config.symbol,
            signal="sell",
            reason=reason,
            price=exit_price,
            market_regime="unknown",  # Will be updated by regime detection
            regime_confidence=0.0,
            regime_trend=0.0,
            regime_volatility=0.0,
            volume=candle.volume,
            timeframe=self.config.timeframe,
        )

        self.performance_db.record_trade(trade_record)

        # Record trade details
        self.trades.append(
            {
                "entry_time": self.entry_time,
                "exit_time": candle.timestamp,
                "entry_price": self.entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "reason": reason,
            }
        )

        logger.info(
            f"Closed {self.position} position: ${self.entry_price:.2f} -> ${exit_price:.2f}, PnL: {pnl:.2%}"
        )

        # Reset position
        self.position = None
        self.entry_price = 0.0
        self.entry_time = 0

    def _update_equity_curve(self, current_price: float):
        """Update equity curve and drawdown calculations"""
        # Calculate current portfolio value
        if self.position == "long":
            position_value = self.current_capital * self.config.position_size
            current_value = (
                position_value * (current_price / self.entry_price)
                if self.entry_price > 0
                else position_value
            )
            portfolio_value = self.current_capital + current_value - position_value
        else:
            portfolio_value = self.current_capital

        self.equity_curve.append(portfolio_value)

        # Update peak and drawdown
        if portfolio_value > self.peak_capital:
            self.peak_capital = portfolio_value

        current_drawdown = (self.peak_capital - portfolio_value) / self.peak_capital
        self.drawdown_curve.append(current_drawdown)

    def _calculate_results(self) -> BacktestResult:
        """Calculate final backtest results"""
        if not self.trades:
            return BacktestResult(
                config=self.config,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                final_capital=self.current_capital,
                trade_history=[],
                market_regime_stats={},
            )

        # Calculate basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t["pnl"] > 0])
        losing_trades = len([t for t in self.trades if t["pnl"] <= 0])
        win_rate = winning_trades / total_trades

        # Calculate PnL metrics
        total_pnl = sum(t["pnl"] for t in self.trades)
        total_return = (
            self.current_capital - self.config.initial_capital
        ) / self.config.initial_capital

        # Calculate max drawdown
        max_drawdown = max(self.drawdown_curve) if self.drawdown_curve else 0.0

        # Calculate Sharpe ratio (simplified)
        if len(self.trades) > 1:
            returns = [t["pnl"] for t in self.trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # Get market regime statistics
        regime_stats = self._get_regime_statistics()

        return BacktestResult(
            config=self.config,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            final_capital=self.current_capital,
            trade_history=self.trades,
            market_regime_stats=regime_stats,
        )

    def _get_regime_statistics(self) -> Dict[str, int]:
        """Get statistics about market regimes during backtest"""
        try:
            # Query performance database for regime distribution
            analysis = self.performance_db.get_market_regime_analysis(
                self.config.symbol, self.config.start_date, self.config.end_date
            )

            regime_stats = {}
            for regime_info in analysis["regime_distribution"]:
                regime_stats[regime_info["regime"]] = regime_info["count"]

            return regime_stats

        except Exception as e:
            logger.warning(f"Error getting regime statistics: {e}")
            return {}

    def _save_backtest_results(self, result: BacktestResult):
        """Save backtest results to performance database"""
        try:
            # Calculate performance metrics for database
            from .performance_db import PerformanceMetrics

            metrics = PerformanceMetrics(
                strategy_name=result.config.strategy_name,
                symbol=result.config.symbol,
                timeframe=result.config.timeframe,
                total_trades=result.total_trades,
                winning_trades=result.winning_trades,
                losing_trades=result.losing_trades,
                win_rate=result.win_rate,
                total_pnl=result.total_pnl,
                avg_win=0.0,  # Would need to calculate from trade history
                avg_loss=0.0,  # Would need to calculate from trade history
                profit_factor=0.0,  # Would need to calculate from trade history
                max_drawdown=result.max_drawdown,
                sharpe_ratio=result.sharpe_ratio,
                start_date=result.config.start_date,
                end_date=result.config.end_date,
                market_regimes=result.market_regime_stats,
            )

            self.performance_db.save_performance(metrics)
            logger.info("Backtest results saved to performance database")

        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")


def run_strategy_backtest(
    strategy_name: str,
    symbol: str,
    timeframe: str,
    days: int = 365,
    initial_capital: float = 10000.0,
) -> BacktestResult:
    """Convenience function to run a complete backtest"""

    # Create configuration
    config = BacktestConfig(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=initial_capital,
    )

    # Create backtesting engine
    engine = BacktestingEngine(config)

    # Generate synthetic data
    preprocessor = DataPreprocessor()
    synthetic_data = preprocessor.generate_synthetic_data(days=days)

    # Run backtest
    result = engine.run_backtest(synthetic_data)

    return result


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing Backtesting Framework...")

    # Run a backtest
    result = run_strategy_backtest(
        strategy_name="SMA_Crossover",
        symbol="BTC/USDT",
        timeframe="1d",
        days=365,
        initial_capital=10000.0,
    )

    # Display results
    print("\n📊 Backtest Results:")
    print(f"  Strategy: {result.config.strategy_name}")
    print(f"  Symbol: {result.config.symbol}")
    print(f"  Timeframe: {result.config.timeframe}")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate:.2%}")
    print(f"  Total PnL: ${result.total_pnl:,.2f}")
    print(f"  Total Return: {result.total_return:.2%}")
    print(f"  Max Drawdown: {result.max_drawdown:.2%}")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Final Capital: ${result.final_capital:,.2f}")

    print("\n📈 Market Regime Statistics:")
    for regime, count in result.market_regime_stats.items():
        print(f"  {regime}: {count} periods")

    print("\n✅ Backtesting framework test completed!")
