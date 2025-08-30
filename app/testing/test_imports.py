#!/usr/bin/env python3
"""
Simple import test to debug import issues
"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent
app_dir = project_root / "app"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(app_dir))


def test_imports():
    """Test imports step by step"""
    print("Testing imports step by step...")

    # Test 1: Basic modules
    try:
        import numpy  # noqa: F401

        print("✅ numpy imported successfully")
    except Exception as e:
        print(f"❌ numpy import failed: {e}")

    # Test 2: Strategy module
    try:
        import strategy  # noqa: F401

        print("✅ strategy module imported successfully")
    except Exception as e:
        print(f"❌ strategy module import failed: {e}")

    # Test 3: Data collection module - handle ccxt dependency gracefully
    try:
        # Try to import ccxt first
        import ccxt  # noqa: F401

        print("✅ ccxt imported successfully")

        # Now try data_collection module
        import data_collection  # noqa: F401

        print("✅ data_collection module imported successfully")
    except ImportError as e:
        if "ccxt" in str(e):
            print("⚠️ ccxt not available - data_collection module will be limited")
            # Try to import individual components that don't depend on ccxt
            try:
                from data_collection.data_preprocessor import (
                    DataPreprocessor,
                )  # noqa: F401

                print("✅ DataPreprocessor imported successfully (ccxt-independent)")
            except Exception as e2:
                print(f"❌ DataPreprocessor import failed: {e2}")
        else:
            print(f"❌ data_collection module import failed: {e}")
    except Exception as e:
        print(f"❌ data_collection module import failed: {e}")

    # Test 4: Market analysis module
    try:
        import market_analysis  # noqa: F401

        print("✅ market_analysis module imported successfully")
    except Exception as e:
        print(f"❌ market_analysis module import failed: {e}")

    # Test 5: Specific classes
    try:
        from strategy.backtesting import BacktestingEngine  # noqa: F401

        print("✅ BacktestingEngine imported successfully")
    except Exception as e:
        print(f"❌ BacktestingEngine import failed: {e}")

    try:
        from data_collection.data_preprocessor import DataPreprocessor  # noqa: F401

        print("✅ DataPreprocessor imported successfully")
    except Exception as e:
        print(f"❌ DataPreprocessor import failed: {e}")

    try:
        from market_analysis.regime_detection import MarketRegimeDetector  # noqa: F401

        print("✅ MarketRegimeDetector imported successfully")
    except Exception as e:
        print(f"❌ MarketRegimeDetector import failed: {e}")


if __name__ == "__main__":
    test_imports()
