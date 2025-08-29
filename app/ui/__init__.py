"""
UI Package for Trading Bot System
Contains all user interface components including FastAPI app, routes, and enhanced functions.
"""

# Import main UI components for easy access
try:
    from .ui import app
    from .ui_enhanced import get_enhanced_system_health, get_enhanced_system_resources
    from .ui_routes import router
    from .ui_helpers import load_json, zip_dirs
except ImportError:
    # Allow import even if some components aren't available
    pass
