"""
Portfolio Package for Trading Bot System
Contains portfolio management and position tracking components.
"""

# Import portfolio components for easy access
try:
    from .portfolio import Portfolio
except ImportError:
    # Allow import even if some components aren't available
    pass
