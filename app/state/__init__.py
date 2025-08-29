"""
State Package for Trading Bot System
Contains state persistence and management components.
"""

# Import state components for easy access
try:
    from .store import save_json, load_json
except ImportError:
    # Allow import even if some components aren't available
    pass
