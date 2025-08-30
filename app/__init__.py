# Trading Bot Application Package
"""
Main application package for the trading bot system.
Provides access to core trading functionality, strategies, and utilities.
"""

# Core utilities and functions
from .core.utils import now_iso, tf_to_ms, sma_series  # noqa: F401

# Market analysis components
from .market_analysis.regime_detection import MarketRegimeDetector  # noqa: F401

# Strategy components
from .strategy.performance_db import StrategyPerformanceDB  # noqa: F401

# Data collection components
from .data_collection.data_preprocessor import DataPreprocessor  # noqa: F401

# Version information
__version__ = "1.0.0"
__author__ = "Trading Bot Team"
