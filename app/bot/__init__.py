"""
Bot Package for Trading Bot System
Contains all trading bot logic and execution components.
"""

# Import main bot components for easy access
try:
    from .bot_main import main
    from .bot import load_profile, get_exchange, sma, slope_pct_per_bar
except ImportError:
    # Allow import even if some components aren't available
    pass
