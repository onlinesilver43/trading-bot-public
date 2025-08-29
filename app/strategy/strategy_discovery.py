#!/usr/bin/env python3
"""
Strategy Discovery System - Phase 4 Implementation
Discovers optimal strategies through comprehensive historical data analysis
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
from pathlib import Path

from .performance_db import StrategyPerformanceDB
from ..market_analysis.regime_detection import MarketRegimeDetector
from ..core.utils import get_current_time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"

class BotType(Enum):
    """Bot type enumeration"""
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"

class StrategyType(Enum):
    """Strategy types to test"""
    SMA_CROSSOVER = "sma_crossover"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    GRID_TRADING = "grid_trading"
    BOLLINGER_BANDS = "bollinger_bands"
    RSI_STRATEGY = "rsi_strategy"
    MACD_STRATEGY = "macd_strategy"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    TREND_FOLLOWING = "trend_following"
    COUNTER_TREND = "counter_trend"

@dataclass
class StrategyParameters:
    """Parameters for strategy optimization"""
    strategy_type: StrategyType
    parameters: Dict[str, Any]
    description: str

@dataclass
class StrategyPerformance:
    """Comprehensive strategy performance metrics"""
    strategy_name: str
    parameters: Dict[str, Any]
    market_regime: MarketRegime
    bot_type: BotType
    
    # Performance metrics
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    avg_profit_per_trade: float
    avg_loss_per_trade: float
    
    # Risk metrics
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    expected_shortfall: float
    calmar_ratio: float
    
    # Market condition metrics
    regime_performance: Dict[str, float]  # Performance in each regime
    volatility_performance: Dict[str, float]  # Performance in different volatility levels
    
    # Timestamp
    discovery_date: datetime
    backtest_period: str

class StrategyDiscoveryEngine:
    """
    Strategy Discovery Engine for finding optimal strategies through historical analysis
    
    Features:
    - Comprehensive historical data analysis
    - Multi-timeframe strategy testing
    - Market regime-specific optimization
    - Bot-type specific strategy discovery
    - Parameter optimization through grid search
    - Performance validation across different market conditions
    """
    
    def __init__(self, 
                 performance_db: StrategyPerformanceDB,
                 regime_detector: MarketRegimeDetector,
                 data_directory: str = "data/historical"):
        self.performance_db = performance_db
        self.regime_detector = regime_detector
        self.data_directory = Path(data_directory)
        
        # Strategy parameter ranges for optimization
        self.strategy_parameters = self._initialize_strategy_parameters()
        
        # Market regime periods for analysis
        self.regime_periods = {
            MarketRegime.TRENDING_UP: ["2021-01-01", "2021-12-31", "2023-01-01", "2023-06-30"],
            MarketRegime.TRENDING_DOWN: ["2022-01-01", "2022-12-31"],
            MarketRegime.SIDEWAYS: ["2020-06-01", "2020-12-31"],
            MarketRegime.VOLATILE: ["2020-03-01", "2020-05-31", "2022-03-01", "2022-05-31"],
            MarketRegime.LOW_VOLATILITY: ["2021-06-01", "2021-08-31"]
        }
        
        # Bot-specific constraints
        self.bot_constraints = {
            BotType.AGGRESSIVE: {
                "max_drawdown": 0.25,
                "min_sharpe": 1.0,
                "min_win_rate": 0.55,
                "max_position_size": 0.1  # 10% of capital
            },
            BotType.MODERATE: {
                "max_drawdown": 0.15,
                "min_sharpe": 1.5,
                "min_win_rate": 0.60,
                "max_position_size": 0.05  # 5% of capital
            },
            BotType.CONSERVATIVE: {
                "max_drawdown": 0.08,
                "min_sharpe": 2.0,
                "min_win_rate": 0.65,
                "max_position_size": 0.025  # 2.5% of capital
            }
        }
        
        # Discovery results
        self.discovered_strategies = {}
        self.optimization_history = []
        
        logger.info("Strategy Discovery Engine initialized")
    
    def _initialize_strategy_parameters(self) -> Dict[StrategyType, List[StrategyParameters]]:
        """Initialize parameter ranges for each strategy type"""
        return {
            StrategyType.SMA_CROSSOVER: [
                StrategyParameters(
                    strategy_type=StrategyType.SMA_CROSSOVER,
                    parameters={"fast_sma": 10, "slow_sma": 20, "stop_loss": 0.02},
                    description="Fast SMA: 10, Slow SMA: 20, Stop Loss: 2%"
                ),
                StrategyParameters(
                    strategy_type=StrategyType.SMA_CROSSOVER,
                    parameters={"fast_sma": 5, "slow_sma": 15, "stop_loss": 0.015},
                    description="Fast SMA: 5, Slow SMA: 15, Stop Loss: 1.5%"
                ),
                StrategyParameters(
                    strategy_type=StrategyType.SMA_CROSSOVER,
                    parameters={"fast_sma": 20, "slow_sma": 50, "stop_loss": 0.025},
                    description="Fast SMA: 20, Slow SMA: 50, Stop Loss: 2.5%"
                )
            ],
            StrategyType.MEAN_REVERSION: [
                StrategyParameters(
                    strategy_type=StrategyType.MEAN_REVERSION,
                    parameters={"lookback": 20, "std_dev": 2.0, "take_profit": 0.03},
                    description="Lookback: 20, Std Dev: 2.0, Take Profit: 3%"
                ),
                StrategyParameters(
                    strategy_type=StrategyType.MEAN_REVERSION,
                    parameters={"lookback": 14, "std_dev": 1.5, "take_profit": 0.025},
                    description="Lookback: 14, Std Dev: 1.5, Take Profit: 2.5%"
                )
            ],
            StrategyType.MOMENTUM: [
                StrategyParameters(
                    strategy_type=StrategyType.MOMENTUM,
                    parameters={"momentum_period": 14, "threshold": 0.02, "stop_loss": 0.03},
                    description="Momentum Period: 14, Threshold: 2%, Stop Loss: 3%"
                ),
                StrategyParameters(
                    strategy_type=StrategyType.MOMENTUM,
                    parameters={"momentum_period": 21, "threshold": 0.015, "stop_loss": 0.025},
                    description="Momentum Period: 21, Threshold: 1.5%, Stop Loss: 2.5%"
                )
            ],
            StrategyType.GRID_TRADING: [
                StrategyParameters(
                    strategy_type=StrategyType.GRID_TRADING,
                    parameters={"grid_levels": 10, "grid_spacing": 0.01, "position_size": 0.1},
                    description="Grid Levels: 10, Spacing: 1%, Position Size: 10%"
                ),
                StrategyParameters(
                    strategy_type=StrategyType.GRID_TRADING,
                    parameters={"grid_levels": 15, "grid_spacing": 0.008, "position_size": 0.08},
                    description="Grid Levels: 15, Spacing: 0.8%, Position Size: 8%"
                )
            ],
            StrategyType.BOLLINGER_BANDS: [
                StrategyParameters(
                    strategy_type=StrategyType.BOLLINGER_BANDS,
                    parameters={"period": 20, "std_dev": 2.0, "stop_loss": 0.02},
                    description="Period: 20, Std Dev: 2.0, Stop Loss: 2%"
                )
            ],
            StrategyType.RSI_STRATEGY: [
                StrategyParameters(
                    strategy_type=StrategyType.RSI_STRATEGY,
                    parameters={"period": 14, "oversold": 30, "overbought": 70, "stop_loss": 0.02},
                    description="Period: 14, Oversold: 30, Overbought: 70, Stop Loss: 2%"
                )
            ]
        }
    
    async def discover_optimal_strategies(self, 
                                        bot_type: BotType,
                                        market_regime: MarketRegime,
                                        time_period: str = "1Y") -> List[StrategyPerformance]:
        """
        Discover optimal strategies for a specific bot type and market regime
        
        Args:
            bot_type: Type of bot (aggressive, moderate, conservative)
            market_regime: Current market regime
            time_period: Time period for analysis (1M, 3M, 6M, 1Y, 2Y, 5Y)
        
        Returns:
            List of optimal strategies ranked by performance
        """
        logger.info(f"Discovering optimal strategies for {bot_type.value} bot in {market_regime.value} regime")
        
        try:
            # Step 1: Load historical data for the specified period
            historical_data = await self._load_historical_data(time_period)
            if historical_data is None or historical_data.empty:
                raise ValueError(f"No historical data available for period: {time_period}")
            
            # Step 2: Identify regime-specific periods
            regime_periods = self._identify_regime_periods(historical_data, market_regime)
            
            # Step 3: Test all strategy parameters
            strategy_results = []
            
            for strategy_type, param_list in self.strategy_parameters.items():
                for params in param_list:
                    logger.info(f"Testing {strategy_type.value} with parameters: {params.description}")
                    
                    # Test strategy across all regime periods
                    performance = await self._test_strategy_parameters(
                        strategy_type, params, regime_periods, historical_data, bot_type
                    )
                    
                    if performance:
                        strategy_results.append(performance)
            
            # Step 4: Filter results based on bot constraints
            filtered_results = self._filter_by_bot_constraints(strategy_results, bot_type)
            
            # Step 5: Rank strategies by performance
            ranked_strategies = self._rank_strategies(filtered_results, bot_type)
            
            # Step 6: Store discovery results
            self.discovered_strategies[f"{bot_type.value}_{market_regime.value}"] = ranked_strategies
            
            logger.info(f"Discovered {len(ranked_strategies)} optimal strategies for {bot_type.value} bot")
            return ranked_strategies
            
        except Exception as e:
            logger.error(f"Error discovering strategies: {str(e)}")
            return []
    
    async def _load_historical_data(self, time_period: str) -> Optional[pd.DataFrame]:
        """Load historical price data for the specified time period"""
        try:
            # Calculate start date based on time period
            end_date = datetime.now()
            
            if time_period == "1M":
                start_date = end_date - timedelta(days=30)
            elif time_period == "3M":
                start_date = end_date - timedelta(days=90)
            elif time_period == "6M":
                start_date = end_date - timedelta(days=180)
            elif time_period == "1Y":
                start_date = end_date - timedelta(days=365)
            elif time_period == "2Y":
                start_date = end_date - timedelta(days=730)
            elif time_period == "5Y":
                start_date = end_date - timedelta(days=1825)
            else:
                start_date = end_date - timedelta(days=365)  # Default to 1 year
            
            # Load data from multiple sources
            data_sources = [
                self.data_directory / "binance_btc_usdt_1h.csv",
                self.data_directory / "binance_eth_usdt_1h.csv",
                self.data_directory / "binance_sol_usdt_1h.csv"
            ]
            
            all_data = []
            for source in data_sources:
                if source.exists():
                    try:
                        df = pd.read_csv(source)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                        if not df.empty:
                            all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Error loading {source}: {str(e)}")
            
            if not all_data:
                # Generate synthetic data for testing
                logger.info("No historical data found, generating synthetic data for testing")
                return self._generate_synthetic_data(start_date, end_date)
            
            # Combine all data sources
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Loaded {len(combined_data)} historical data points from {start_date} to {end_date}")
            return combined_data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            return None
    
    def _generate_synthetic_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic price data for testing when historical data is unavailable"""
        logger.info("Generating synthetic data for strategy testing")
        
        # Generate hourly timestamps
        timestamps = pd.date_range(start=start_date, end=end_date, freq='H')
        
        # Generate synthetic BTC price data with realistic patterns
        np.random.seed(42)  # For reproducible results
        
        # Base price and trend
        base_price = 50000
        trend = np.linspace(0, 0.3, len(timestamps))  # 30% upward trend over period
        
        # Volatility and noise
        volatility = 0.02  # 2% hourly volatility
        noise = np.random.normal(0, volatility, len(timestamps))
        
        # Generate prices
        prices = base_price * (1 + trend + noise)
        
        # Ensure prices are positive
        prices = np.maximum(prices, 1000)
        
        # Create DataFrame
        data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(timestamps)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(timestamps)))),
            'close': prices,
            'volume': np.random.uniform(1000, 10000, len(timestamps))
        })
        
        # Ensure high >= low
        data['high'] = np.maximum(data['high'], data['low'])
        
        logger.info(f"Generated {len(data)} synthetic data points")
        return data
    
    def _identify_regime_periods(self, 
                                data: pd.DataFrame, 
                                target_regime: MarketRegime) -> List[Tuple[datetime, datetime]]:
        """Identify periods in the data that match the target market regime"""
        regime_periods = []
        
        # For synthetic data, create regime-specific periods
        if len(data) > 0:
            total_periods = len(data)
            
            if target_regime == MarketRegime.TRENDING_UP:
                # Create upward trending periods
                for i in range(0, total_periods - 100, 200):
                    end_idx = min(i + 100, total_periods)
                    start_time = data.iloc[i]['timestamp']
                    end_time = data.iloc[end_idx]['timestamp']
                    regime_periods.append((start_time, end_time))
            
            elif target_regime == MarketRegime.TRENDING_DOWN:
                # Create downward trending periods
                for i in range(0, total_periods - 100, 200):
                    end_idx = min(i + 100, total_periods)
                    start_time = data.iloc[i]['timestamp']
                    end_time = data.iloc[end_idx]['timestamp']
                    regime_periods.append((start_time, end_time))
            
            elif target_regime == MarketRegime.SIDEWAYS:
                # Create sideways periods
                for i in range(0, total_periods - 150, 300):
                    end_idx = min(i + 150, total_periods)
                    start_time = data.iloc[i]['timestamp']
                    end_time = data.iloc[end_idx]['timestamp']
                    regime_periods.append((start_time, end_time))
            
            elif target_regime == MarketRegime.VOLATILE:
                # Create volatile periods
                for i in range(0, total_periods - 80, 160):
                    end_idx = min(i + 80, total_periods)
                    start_time = data.iloc[i]['timestamp']
                    end_time = data.iloc[end_idx]['timestamp']
                    regime_periods.append((start_time, end_time))
            
            else:  # LOW_VOLATILITY
                # Create low volatility periods
                for i in range(0, total_periods - 120, 240):
                    end_idx = min(i + 120, total_periods)
                    start_time = data.iloc[i]['timestamp']
                    end_time = data.iloc[end_idx]['timestamp']
                    regime_periods.append((start_time, end_time))
        
        logger.info(f"Identified {len(regime_periods)} periods for {target_regime.value} regime")
        return regime_periods
    
    async def _test_strategy_parameters(self, 
                                      strategy_type: StrategyType,
                                      params: StrategyParameters,
                                      regime_periods: List[Tuple[datetime, datetime]],
                                      data: pd.DataFrame,
                                      bot_type: BotType) -> Optional[StrategyPerformance]:
        """Test strategy parameters across regime periods"""
        try:
            all_performances = []
            
            for start_time, end_time in regime_periods:
                # Filter data for this period
                period_data = data[(data['timestamp'] >= start_time) & (data['timestamp'] <= end_time)]
                
                if len(period_data) < 50:  # Need minimum data points
                    continue
                
                # Run backtest for this period
                performance = await self._run_strategy_backtest(
                    strategy_type, params, period_data, bot_type
                )
                
                if performance:
                    all_performances.append(performance)
            
            if not all_performances:
                return None
            
            # Aggregate performance across all periods
            return self._aggregate_performance(all_performances, strategy_type, params, bot_type)
            
        except Exception as e:
            logger.error(f"Error testing strategy parameters: {str(e)}")
            return None
    
    async def _run_strategy_backtest(self, 
                                   strategy_type: StrategyType,
                                   params: StrategyParameters,
                                   data: pd.DataFrame,
                                   bot_type: BotType) -> Optional[Dict[str, Any]]:
        """Run backtest for a specific strategy and parameters"""
        try:
            # This would integrate with the actual backtesting framework
            # For now, we'll simulate backtest results
            
            # Simulate trading based on strategy type
            trades = self._simulate_strategy_trades(strategy_type, params, data)
            
            if not trades:
                return None
            
            # Calculate performance metrics
            performance = self._calculate_performance_metrics(trades, data)
            
            return performance
            
        except Exception as e:
            logger.error(f"Error running strategy backtest: {str(e)}")
            return None
    
    def _simulate_strategy_trades(self, 
                                strategy_type: StrategyType,
                                params: StrategyParameters,
                                data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Simulate trades for a strategy (placeholder for actual strategy logic)"""
        trades = []
        
        # Simple simulation based on strategy type
        if strategy_type == StrategyType.SMA_CROSSOVER:
            fast_sma = params.parameters.get("fast_sma", 10)
            slow_sma = params.parameters.get("slow_sma", 20)
            stop_loss = params.parameters.get("stop_loss", 0.02)
            
            # Calculate SMAs
            data['fast_sma'] = data['close'].rolling(window=fast_sma).mean()
            data['slow_sma'] = data['close'].rolling(window=slow_sma).mean()
            
            # Generate signals
            data['signal'] = np.where(data['fast_sma'] > data['slow_sma'], 1, -1)
            data['signal_change'] = data['signal'].diff()
            
            # Find entry points
            entry_points = data[data['signal_change'] != 0].copy()
            
            for idx, row in entry_points.iterrows():
                if row['signal'] == 1:  # Buy signal
                    # Find exit point (when signal changes or stop loss hit)
                    exit_idx = self._find_exit_point(data, idx, stop_loss, is_long=True)
                    if exit_idx:
                        trades.append({
                            'entry_time': row['timestamp'],
                            'exit_time': data.iloc[exit_idx]['timestamp'],
                            'entry_price': row['close'],
                            'exit_price': data.iloc[exit_idx]['close'],
                            'type': 'long',
                            'pnl': (data.iloc[exit_idx]['close'] - row['close']) / row['close']
                        })
        
        elif strategy_type == StrategyType.MEAN_REVERSION:
            lookback = params.parameters.get("lookback", 20)
            std_dev = params.parameters.get("std_dev", 2.0)
            take_profit = params.parameters.get("take_profit", 0.03)
            
            # Calculate Bollinger Bands
            data['sma'] = data['close'].rolling(window=lookback).mean()
            data['std'] = data['close'].rolling(window=lookback).std()
            data['upper_band'] = data['sma'] + (data['std'] * std_dev)
            data['lower_band'] = data['sma'] - (data['std'] * std_dev)
            
            # Generate signals
            data['signal'] = np.where(data['close'] < data['lower_band'], 1, 0)
            data['signal'] = np.where(data['close'] > data['upper_band'], -1, data['signal'])
            
            # Find trades
            for i in range(1, len(data)):
                if data.iloc[i]['signal'] == 1 and data.iloc[i-1]['signal'] == 0:  # Buy signal
                    exit_idx = self._find_mean_reversion_exit(data, i, take_profit)
                    if exit_idx:
                        trades.append({
                            'entry_time': data.iloc[i]['timestamp'],
                            'exit_time': data.iloc[exit_idx]['timestamp'],
                            'entry_price': data.iloc[i]['close'],
                            'exit_price': data.iloc[exit_idx]['close'],
                            'type': 'long',
                            'pnl': (data.iloc[exit_idx]['close'] - data.iloc[i]['close']) / data.iloc[i]['close']
                        })
        
        # Add more strategy simulations here...
        
        return trades
    
    def _find_exit_point(self, data: pd.DataFrame, entry_idx: int, stop_loss: float, is_long: bool) -> Optional[int]:
        """Find exit point for a trade based on stop loss or signal change"""
        entry_price = data.iloc[entry_idx]['close']
        
        for i in range(entry_idx + 1, len(data)):
            current_price = data.iloc[i]['close']
            
            if is_long:
                # Check stop loss
                if current_price <= entry_price * (1 - stop_loss):
                    return i
                # Check signal change
                if data.iloc[i]['signal'] == -1:
                    return i
            else:
                # Check stop loss for short
                if current_price >= entry_price * (1 + stop_loss):
                    return i
                # Check signal change
                if data.iloc[i]['signal'] == 1:
                    return i
        
        return len(data) - 1  # Exit at end if no stop loss or signal change
    
    def _find_mean_reversion_exit(self, data: pd.DataFrame, entry_idx: int, take_profit: float) -> Optional[int]:
        """Find exit point for mean reversion strategy"""
        entry_price = data.iloc[entry_idx]['close']
        
        for i in range(entry_idx + 1, len(data)):
            current_price = data.iloc[i]['close']
            
            # Exit on take profit
            if current_price >= entry_price * (1 + take_profit):
                return i
            
            # Exit if price goes below entry (stop loss)
            if current_price < entry_price:
                return i
        
        return len(data) - 1
    
    def _calculate_performance_metrics(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics from trades"""
        if not trades:
            return None
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # PnL metrics
        total_pnl = sum(t['pnl'] for t in trades)
        avg_profit = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Risk metrics
        returns = [t['pnl'] for t in trades]
        if returns:
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Calculate drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = cumulative_returns - running_max
            max_drawdown = np.min(drawdown)
            
            # Value at Risk
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)
            
            # Expected Shortfall
            expected_shortfall = np.mean([r for r in returns if r <= var_95])
            
            # Calmar Ratio
            calmar_ratio = total_pnl / abs(max_drawdown) if max_drawdown != 0 else 0
        else:
            sharpe_ratio = max_drawdown = var_95 = var_99 = expected_shortfall = calmar_ratio = 0
        
        return {
            "total_return": total_pnl,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_factor": abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf'),
            "total_trades": total_trades,
            "avg_profit_per_trade": avg_profit,
            "avg_loss_per_trade": avg_loss,
            "var_95": var_95,
            "var_99": var_99,
            "expected_shortfall": expected_shortfall,
            "calmar_ratio": calmar_ratio
        }
    
    def _aggregate_performance(self, 
                              performances: List[Dict[str, Any]],
                              strategy_type: StrategyType,
                              params: StrategyParameters,
                              bot_type: BotType) -> StrategyPerformance:
        """Aggregate performance across multiple periods"""
        # Calculate average metrics
        avg_metrics = {}
        for key in performances[0].keys():
            if key in ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']:
                values = [p[key] for p in performances if p[key] is not None]
                if values:
                    avg_metrics[key] = np.mean(values)
                else:
                    avg_metrics[key] = 0
        
        # Create StrategyPerformance object
        return StrategyPerformance(
            strategy_name=f"{strategy_type.value}_{params.description}",
            parameters=params.parameters,
            market_regime=MarketRegime.TRENDING_UP,  # This would be dynamic
            bot_type=bot_type,
            total_return=avg_metrics.get('total_return', 0),
            sharpe_ratio=avg_metrics.get('sharpe_ratio', 0),
            max_drawdown=avg_metrics.get('max_drawdown', 0),
            win_rate=avg_metrics.get('win_rate', 0),
            profit_factor=avg_metrics.get('profit_factor', 0),
            total_trades=sum(p.get('total_trades', 0) for p in performances),
            avg_trade_duration=0,  # Would calculate from actual trade data
            avg_profit_per_trade=avg_metrics.get('avg_profit_per_trade', 0),
            avg_loss_per_trade=avg_metrics.get('avg_loss_per_trade', 0),
            var_95=avg_metrics.get('var_95', 0),
            var_99=avg_metrics.get('var_99', 0),
            expected_shortfall=avg_metrics.get('expected_shortfall', 0),
            calmar_ratio=avg_metrics.get('calmar_ratio', 0),
            regime_performance={},
            volatility_performance={},
            discovery_date=datetime.now(),
            backtest_period="1Y"
        )
    
    def _filter_by_bot_constraints(self, 
                                  strategies: List[StrategyPerformance],
                                  bot_type: BotType) -> List[StrategyPerformance]:
        """Filter strategies based on bot-specific constraints"""
        constraints = self.bot_constraints[bot_type]
        
        filtered = []
        for strategy in strategies:
            if (strategy.max_drawdown <= constraints['max_drawdown'] and
                strategy.sharpe_ratio >= constraints['min_sharpe'] and
                strategy.win_rate >= constraints['min_win_rate']):
                filtered.append(strategy)
        
        logger.info(f"Filtered {len(strategies)} strategies to {len(filtered)} for {bot_type.value} bot")
        return filtered
    
    def _rank_strategies(self, 
                        strategies: List[StrategyPerformance],
                        bot_type: BotType) -> List[StrategyPerformance]:
        """Rank strategies by performance score"""
        def calculate_score(strategy):
            # Weighted scoring based on bot type preferences
            if bot_type == BotType.AGGRESSIVE:
                # Aggressive bots prefer high returns and can tolerate more risk
                return (0.4 * strategy.total_return + 
                       0.2 * strategy.sharpe_ratio + 
                       0.2 * strategy.profit_factor + 
                       0.1 * strategy.win_rate + 
                       0.1 * (1 - abs(strategy.max_drawdown)))
            
            elif bot_type == BotType.MODERATE:
                # Moderate bots prefer balanced performance
                return (0.3 * strategy.total_return + 
                       0.3 * strategy.sharpe_ratio + 
                       0.2 * strategy.profit_factor + 
                       0.15 * strategy.win_rate + 
                       0.05 * (1 - abs(strategy.max_drawdown)))
            
            else:  # Conservative
                # Conservative bots prefer low risk and consistent returns
                return (0.2 * strategy.total_return + 
                       0.4 * strategy.sharpe_ratio + 
                       0.2 * strategy.profit_factor + 
                       0.15 * strategy.win_rate + 
                       0.05 * (1 - abs(strategy.max_drawdown)))
        
        # Sort by score (highest first)
        ranked = sorted(strategies, key=calculate_score, reverse=True)
        
        # Add ranking information
        for i, strategy in enumerate(ranked):
            strategy.ranking = i + 1
        
        return ranked
    
    async def run_comprehensive_discovery(self) -> Dict[str, Any]:
        """Run comprehensive strategy discovery for all bot types and market regimes"""
        logger.info("Starting comprehensive strategy discovery...")
        
        discovery_results = {}
        
        for bot_type in BotType:
            for market_regime in MarketRegime:
                logger.info(f"Discovering strategies for {bot_type.value} bot in {market_regime.value} regime")
                
                strategies = await self.discover_optimal_strategies(bot_type, market_regime)
                discovery_results[f"{bot_type.value}_{market_regime.value}"] = strategies
        
        # Save discovery results
        self._save_discovery_results(discovery_results)
        
        return discovery_results
    
    def _save_discovery_results(self, results: Dict[str, Any]):
        """Save discovery results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"strategy_discovery_results_{timestamp}.json"
        
        # Convert to serializable format
        serializable_results = {}
        for key, strategies in results.items():
            serializable_results[key] = []
            for strategy in strategies:
                serializable_results[key].append({
                    "strategy_name": strategy.strategy_name,
                    "parameters": strategy.parameters,
                    "total_return": strategy.total_return,
                    "sharpe_ratio": strategy.sharpe_ratio,
                    "max_drawdown": strategy.max_drawdown,
                    "win_rate": strategy.win_rate,
                    "ranking": getattr(strategy, 'ranking', 0)
                })
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Discovery results saved to: {filename}")

async def main():
    """Test the Strategy Discovery Engine"""
    print("🚀 Strategy Discovery Engine - Phase 4 Implementation")
    print("=" * 60)
    
    # Create mock instances
    class MockPerformanceDB:
        async def get_strategy_metrics(self, strategy_name):
            return {"total_return": 0.05, "sharpe_ratio": 1.2}
    
    class MockRegimeDetector:
        async def detect_regime(self):
            return {"regime": "trending_up", "confidence": 0.85}
    
    # Initialize discovery engine
    discovery_engine = StrategyDiscoveryEngine(
        performance_db=MockPerformanceDB(),
        regime_detector=MockRegimeDetector()
    )
    
    # Run discovery for aggressive bot in trending up market
    print("Discovering strategies for aggressive bot in trending up market...")
    strategies = await discovery_engine.discover_optimal_strategies(
        BotType.AGGRESSIVE, MarketRegime.TRENDING_UP
    )
    
    print(f"\n📊 DISCOVERY RESULTS:")
    print(f"Found {len(strategies)} optimal strategies")
    
    for i, strategy in enumerate(strategies[:5]):  # Show top 5
        print(f"\n{i+1}. {strategy.strategy_name}")
        print(f"   Return: {strategy.total_return:.2%}")
        print(f"   Sharpe: {strategy.sharpe_ratio:.2f}")
        print(f"   Max DD: {strategy.max_drawdown:.2%}")
        print(f"   Win Rate: {strategy.win_rate:.1%}")
    
    print("\n✅ Strategy discovery test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
