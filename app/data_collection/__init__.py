"""
Data Collection Package for Trading Bot System
Contains data collection, processing, and storage components.
"""

# Import data collection components for easy access
try:
    from .data_preprocessor import DataPreprocessor
    from .historical_data import HistoricalDataCollector
except ImportError:
    # Allow import even if some components aren't available
    pass
