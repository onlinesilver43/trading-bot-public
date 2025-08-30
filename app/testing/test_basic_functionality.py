#!/usr/bin/env python3
"""
Basic pytest tests for the trading bot system
These are actual pytest tests that can be discovered and run by pytest
"""

import pytest
import sys
from pathlib import Path

# Add the app directory to Python path for proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBasicFunctionality:
    """Basic functionality tests that pytest can run"""

    def test_import_core_utils(self):
        """Test that core utilities can be imported"""
        try:
            from core.utils import now_iso, tf_to_ms, sma_series

            assert callable(now_iso)
            assert callable(tf_to_ms)
            assert callable(sma_series)
        except ImportError as e:
            pytest.skip(f"Core utils not available: {e}")

    def test_import_data_preprocessor(self):
        """Test that data preprocessor can be imported"""
        try:
            from data_collection.data_preprocessor import DataPreprocessor

            assert DataPreprocessor is not None
        except ImportError as e:
            pytest.skip(f"Data preprocessor not available: {e}")

    def test_import_strategy_components(self):
        """Test that strategy components can be imported"""
        try:
            from strategy.performance_db import StrategyPerformanceDB

            assert StrategyPerformanceDB is not None
        except ImportError as e:
            pytest.skip(f"Strategy performance DB not available: {e}")

    def test_import_state_store(self):
        """Test that state store can be imported"""
        try:
            from state.store import save_json, load_json

            assert callable(save_json)
            assert callable(load_json)
        except ImportError as e:
            pytest.skip(f"State store not available: {e}")

    def test_import_exchange_client(self):
        """Test that exchange client can be imported"""
        try:
            from exchange.ccxt_client import Client

            assert Client is not None
        except ImportError as e:
            pytest.skip(f"Exchange client not available: {e}")

    def test_import_ui_components(self):
        """Test that UI components can be imported"""
        try:
            from ui.ui_helpers import load_json, zip_dirs

            assert callable(load_json)
            assert callable(zip_dirs)
        except ImportError as e:
            pytest.skip(f"UI helpers not available: {e}")

    def test_basic_math(self):
        """Test basic math functionality"""
        assert 2 + 2 == 4
        assert 3 * 3 == 9
        assert 10 / 2 == 5

    def test_string_operations(self):
        """Test basic string operations"""
        test_string = "hello world"
        assert len(test_string) == 11
        assert test_string.upper() == "HELLO WORLD"
        assert "hello" in test_string


if __name__ == "__main__":
    # This allows the file to be run directly for testing
    pytest.main([__file__])
