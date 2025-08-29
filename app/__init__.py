"""
Trading Bot System
A comprehensive trading bot system with multiple strategies, market analysis, and AI-powered decision making.

This package contains:
- Core trading logic and utilities
- Market analysis and regime detection
- Strategy implementation and backtesting
- Portfolio management and risk control
- User interface and API endpoints
- Data collection and processing
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Team"
__description__ = "Intelligent Trading Bot System with AI-Powered Strategy Selection"

# Import key components for easy access
try:
    from .core.utils import now_iso, tf_to_ms, sma_series
    from .market_analysis.regime_detection import MarketRegimeDetector
    from .strategy.performance_db import StrategyPerformanceDB
    from .data_collection.data_preprocessor import DataPreprocessor
except ImportError:
    # Allow import even if some components aren't available
    pass
