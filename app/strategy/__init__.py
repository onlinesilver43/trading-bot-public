# Strategy Package
"""
Strategy implementation package for the trading bot system.
Provides access to strategy components, backtesting, and performance tracking.
"""

# Strategy performance database
from .performance_db import StrategyPerformanceDB  # noqa: F401

# Strategy implementations
from .sma_crossover import decide, indicators  # noqa: F401

# Note: BacktestingEngine import moved to avoid circular imports
# Import it directly when needed: from strategy.backtesting import BacktestingEngine
