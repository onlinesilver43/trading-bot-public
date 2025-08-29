"""
Market Analysis Package for Trading Bot System
Contains market regime detection and analysis components.
"""

# Import market analysis components for easy access
try:
    from .regime_detection import MarketRegimeDetector
except ImportError:
    # Allow import even if some components aren't available
    pass
