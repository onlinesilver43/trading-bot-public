# Bot Package
"""
Bot functionality package for the trading bot system.
Provides access to bot main logic, utilities, and trading functions.
"""

# Bot main functionality
from .bot_main import main  # noqa: F401

# Bot utilities and trading functions
from .bot import load_profile, get_exchange, sma, slope_pct_per_bar  # noqa: F401
