#!/usr/bin/env python3
"""
Strategy Performance Database
Tracks strategy performance metrics and correlates with market conditions
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Record of a single trade"""
    timestamp: int
    strategy_name: str
    symbol: str
    signal: str  # "buy", "sell", "none"
    reason: str
    price: float
    market_regime: str
    regime_confidence: float
    regime_trend: float
    regime_volatility: float
    volume: float
    timeframe: str
    trade_id: Optional[str] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for a strategy"""
    strategy_name: str
    symbol: str
    timeframe: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    start_date: str
    end_date: str
    market_regimes: Dict[str, int]  # regime -> count

class StrategyPerformanceDB:
    """Database for tracking strategy performance and market correlations"""
    
    def __init__(self, db_path: str = "strategy_performance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL,
                        strategy_name TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        signal TEXT NOT NULL,
                        reason TEXT,
                        price REAL NOT NULL,
                        market_regime TEXT NOT NULL,
                        regime_confidence REAL NOT NULL,
                        regime_trend REAL NOT NULL,
                        regime_volatility REAL NOT NULL,
                        volume REAL NOT NULL,
                        timeframe TEXT NOT NULL,
                        trade_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create performance table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        total_trades INTEGER NOT NULL,
                        winning_trades INTEGER NOT NULL,
                        losing_trades INTEGER NOT NULL,
                        win_rate REAL NOT NULL,
                        total_pnl REAL NOT NULL,
                        avg_win REAL NOT NULL,
                        avg_loss REAL NOT NULL,
                        profit_factor REAL NOT NULL,
                        max_drawdown REAL NOT NULL,
                        sharpe_ratio REAL NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        market_regimes TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(strategy_name, symbol, timeframe)
                    )
                """)
                
                # Create market_regimes table for analysis
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_regimes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        regime TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        trend REAL NOT NULL,
                        volatility REAL NOT NULL,
                        volume_trend REAL NOT NULL,
                        momentum REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_regime ON trades(market_regime)")
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def record_trade(self, trade: TradeRecord) -> bool:
        """Record a trade in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trades (
                        timestamp, strategy_name, symbol, signal, reason, price,
                        market_regime, regime_confidence, regime_trend, regime_volatility,
                        volume, timeframe, trade_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.timestamp, trade.strategy_name, trade.symbol, trade.signal,
                    trade.reason, trade.price, trade.market_regime, trade.regime_confidence,
                    trade.regime_trend, trade.regime_volatility, trade.volume,
                    trade.timeframe, trade.trade_id
                ))
                
                conn.commit()
                logger.info(f"Recorded trade: {trade.strategy_name} {trade.signal} {trade.symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return False
    
    def record_market_regime(self, timestamp: int, symbol: str, regime: str, 
                           confidence: float, trend: float, volatility: float,
                           volume_trend: float, momentum: float) -> bool:
        """Record market regime data for analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO market_regimes (
                        timestamp, symbol, regime, confidence, trend, volatility,
                        volume_trend, momentum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, symbol, regime, confidence, trend, volatility, volume_trend, momentum))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error recording market regime: {e}")
            return False
    
    def calculate_performance(self, strategy_name: str, symbol: str, 
                            timeframe: str, start_date: str, end_date: str) -> PerformanceMetrics:
        """Calculate performance metrics for a strategy"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all trades for the strategy
                cursor.execute("""
                    SELECT signal, price, market_regime FROM trades 
                    WHERE strategy_name = ? AND symbol = ? AND timeframe = ?
                    AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                """, (strategy_name, symbol, timeframe, 
                      int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000),
                      int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)))
                
                trades = cursor.fetchall()
                
                if not trades:
                    return PerformanceMetrics(
                        strategy_name=strategy_name, symbol=symbol, timeframe=timeframe,
                        total_trades=0, winning_trades=0, losing_trades=0,
                        win_rate=0.0, total_pnl=0.0, avg_win=0.0, avg_loss=0.0,
                        profit_factor=0.0, max_drawdown=0.0, sharpe_ratio=0.0,
                        start_date=start_date, end_date=end_date, market_regimes={}
                    )
                
                # Calculate basic metrics
                total_trades = len(trades)
                buy_trades = [t for t in trades if t[0] == "buy"]
                sell_trades = [t for t in trades if t[0] == "sell"]
                
                # Calculate PnL (simplified - assumes we can buy/sell at signal prices)
                pnl = 0.0
                wins = []
                losses = []
                current_position = None
                entry_price = 0.0
                
                for signal, price, regime in trades:
                    if signal == "buy" and current_position is None:
                        current_position = "long"
                        entry_price = price
                    elif signal == "sell" and current_position == "long":
                        trade_pnl = price - entry_price
                        pnl += trade_pnl
                        
                        if trade_pnl > 0:
                            wins.append(trade_pnl)
                        else:
                            losses.append(abs(trade_pnl))
                        
                        current_position = None
                        entry_price = 0.0
                
                # Calculate derived metrics
                winning_trades = len(wins)
                losing_trades = len(losses)
                win_rate = winning_trades / max(total_trades, 1)
                avg_win = sum(wins) / max(len(wins), 1)
                avg_loss = sum(losses) / max(len(losses), 1)
                profit_factor = sum(wins) / max(sum(losses), 0.01)
                
                # Calculate max drawdown (simplified)
                max_drawdown = 0.0
                peak = 0.0
                running_pnl = 0.0
                
                for signal, price, regime in trades:
                    if signal == "buy" and current_position is None:
                        current_position = "long"
                        entry_price = price
                    elif signal == "sell" and current_position == "long":
                        trade_pnl = price - entry_price
                        running_pnl += trade_pnl
                        
                        if running_pnl > peak:
                            peak = running_pnl
                        else:
                            drawdown = peak - running_pnl
                            max_drawdown = max(max_drawdown, drawdown)
                        
                        current_position = None
                        entry_price = 0.0
                
                # Calculate Sharpe ratio (simplified - assumes 0 risk-free rate)
                if len(wins) + len(losses) > 0:
                    returns = wins + [-l for l in losses]
                    avg_return = sum(returns) / len(returns)
                    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                    sharpe_ratio = avg_return / (variance ** 0.5) if variance > 0 else 0.0
                else:
                    sharpe_ratio = 0.0
                
                # Count market regimes
                regime_counts = {}
                for _, _, regime in trades:
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                return PerformanceMetrics(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    win_rate=win_rate,
                    total_pnl=pnl,
                    avg_win=avg_win,
                    avg_loss=avg_loss,
                    profit_factor=profit_factor,
                    max_drawdown=max_drawdown,
                    sharpe_ratio=sharpe_ratio,
                    start_date=start_date,
                    end_date=end_date,
                    market_regimes=regime_counts
                )
                
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            raise
    
    def save_performance(self, metrics: PerformanceMetrics) -> bool:
        """Save performance metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert market_regimes dict to JSON string
                regimes_json = json.dumps(metrics.market_regimes)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO performance (
                        strategy_name, symbol, timeframe, total_trades, winning_trades,
                        losing_trades, win_rate, total_pnl, avg_win, avg_loss,
                        profit_factor, max_drawdown, sharpe_ratio, start_date, end_date,
                        market_regimes, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    metrics.strategy_name, metrics.symbol, metrics.timeframe,
                    metrics.total_trades, metrics.winning_trades, metrics.losing_trades,
                    metrics.win_rate, metrics.total_pnl, metrics.avg_win, metrics.avg_loss,
                    metrics.profit_factor, metrics.max_drawdown, metrics.sharpe_ratio,
                    metrics.start_date, metrics.end_date, regimes_json
                ))
                
                conn.commit()
                logger.info(f"Saved performance metrics for {metrics.strategy_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving performance: {e}")
            return False
    
    def get_performance_summary(self, strategy_name: str = None) -> List[PerformanceMetrics]:
        """Get performance summary for all strategies or a specific strategy"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if strategy_name:
                    cursor.execute("SELECT * FROM performance WHERE strategy_name = ?", (strategy_name,))
                else:
                    cursor.execute("SELECT * FROM performance ORDER BY strategy_name, symbol, timeframe")
                
                rows = cursor.fetchall()
                metrics = []
                
                for row in rows:
                    # Parse market_regimes JSON
                    regimes = json.loads(row[16]) if row[16] else {}
                    
                    metric = PerformanceMetrics(
                        strategy_name=row[1],
                        symbol=row[2],
                        timeframe=row[3],
                        total_trades=row[4],
                        winning_trades=row[5],
                        losing_trades=row[6],
                        win_rate=row[7],
                        total_pnl=row[8],
                        avg_win=row[9],
                        avg_loss=row[10],
                        profit_factor=row[11],
                        max_drawdown=row[12],
                        sharpe_ratio=row[13],
                        start_date=row[14],
                        end_date=row[15],
                        market_regimes=regimes
                    )
                    metrics.append(metric)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return []
    
    def get_market_regime_analysis(self, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Analyze market regime distribution and performance correlation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get regime distribution
                cursor.execute("""
                    SELECT regime, COUNT(*) as count, AVG(confidence) as avg_confidence,
                           AVG(trend) as avg_trend, AVG(volatility) as avg_volatility
                    FROM market_regimes 
                    WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                    GROUP BY regime
                """, (symbol, 
                      int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000),
                      int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)))
                
                regime_stats = cursor.fetchall()
                
                # Get performance by regime
                cursor.execute("""
                    SELECT t.market_regime, COUNT(*) as trades, AVG(t.price) as avg_price
                    FROM trades t
                    WHERE t.symbol = ? AND t.timestamp BETWEEN ? AND ?
                    GROUP BY t.market_regime
                """, (symbol,
                      int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000),
                      int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)))
                
                regime_performance = cursor.fetchall()
                
                return {
                    "regime_distribution": [
                        {
                            "regime": row[0],
                            "count": row[1],
                            "avg_confidence": row[2],
                            "avg_trend": row[3],
                            "avg_volatility": row[4]
                        }
                        for row in regime_stats
                    ],
                    "regime_performance": [
                        {
                            "regime": row[0],
                            "trades": row[1],
                            "avg_price": row[2]
                        }
                        for row in regime_performance
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error analyzing market regimes: {e}")
            return {"regime_distribution": [], "regime_performance": []}

# Example usage and testing
if __name__ == "__main__":
    # Test the performance database
    db = StrategyPerformanceDB("test_performance.db")
    
    # Create sample trade records
    sample_trades = [
        TradeRecord(
            timestamp=int(datetime.now().timestamp() * 1000),
            strategy_name="SMA_Crossover",
            symbol="BTC/USDT",
            signal="buy",
            reason="fast_cross_up",
            price=50000.0,
            market_regime="trending",
            regime_confidence=0.75,
            regime_trend=0.02,
            regime_volatility=0.03,
            volume=1000.0,
            timeframe="1h"
        ),
        TradeRecord(
            timestamp=int(datetime.now().timestamp() * 1000) + 3600000,
            strategy_name="SMA_Crossover",
            symbol="BTC/USDT",
            signal="sell",
            reason="fast_cross_down",
            price=51000.0,
            market_regime="trending",
            regime_confidence=0.70,
            regime_trend=0.01,
            regime_volatility=0.04,
            volume=1200.0,
            timeframe="1h"
        )
    ]
    
    # Record trades
    for trade in sample_trades:
        db.record_trade(trade)
    
    # Calculate and save performance
    metrics = db.calculate_performance("SMA_Crossover", "BTC/USDT", "1h", 
                                     "2024-01-01", "2024-12-31")
    db.save_performance(metrics)
    
    # Get performance summary
    summary = db.get_performance_summary()
    print("Performance Summary:")
    for metric in summary:
        print(f"  {metric.strategy_name} {metric.symbol} {metric.timeframe}")
        print(f"    Win Rate: {metric.win_rate:.2%}")
        print(f"    Total PnL: ${metric.total_pnl:.2f}")
        print(f"    Profit Factor: {metric.profit_factor:.2f}")
        print(f"    Max Drawdown: ${metric.max_drawdown:.2f}")
        print(f"    Sharpe Ratio: {metric.sharpe_ratio:.2f}")
        print(f"    Market Regimes: {metric.market_regimes}")
        print()
    
    print("✅ Performance database test completed!")
