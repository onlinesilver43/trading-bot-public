"""
Exchange Package for Trading Bot System
Contains exchange integration and API client components.
"""

# Import exchange components for easy access
try:
    from .ccxt_client import Client
except ImportError:
    # Allow import even if some components aren't available
    pass
