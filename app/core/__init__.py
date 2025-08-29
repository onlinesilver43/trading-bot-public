"""
Core Package for Trading Bot System
Contains core utilities, time functions, and trading algorithms.
"""

# Import core utilities for easy access
try:
    from .utils import now_iso, tf_to_ms, sma_series
except ImportError:
    # Allow import even if some components aren't available
    pass
