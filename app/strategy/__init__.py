"""
Strategy Package for Trading Bot System
Contains trading strategies, performance tracking, and backtesting components.
"""

# Import strategy components for easy access
try:
    from .performance_db import StrategyPerformanceDB
    from .backtesting import BacktestingFramework
    from .sma_crossover import SMACrossoverStrategy
except ImportError:
    # Allow import even if some components aren't available
    pass
