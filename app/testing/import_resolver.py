#!/usr/bin/env python3
"""
Import Resolver for Testing
Provides a clean, maintainable way to import modules from different parts of the codebase
"""

import sys
import importlib
from pathlib import Path
from typing import Any, Optional, Tuple


class ImportResolver:
    """Clean import resolver that handles complex import paths"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.app_dir = self.project_root / "app"
        self._setup_paths()

    def _setup_paths(self):
        """Setup Python paths in the correct order"""
        # Clear any existing problematic paths
        paths_to_remove = [str(p) for p in sys.path if "app/testing" in str(p)]
        for path in paths_to_remove:
            sys.path.remove(path)

        # Add paths in correct order
        sys.path.insert(0, str(self.project_root))
        sys.path.insert(0, str(self.app_dir))

    def resolve_import(
        self, module_path: str, class_name: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """
        Resolve imports using multiple strategies
        Returns (success, result_or_error_message)
        """
        strategies = [
            self._try_absolute_import,
            self._try_app_relative_import,
            self._try_project_relative_import,
        ]

        for strategy in strategies:
            try:
                result = strategy(module_path, class_name)
                if result[0]:  # Success
                    return True, result[1]
            except Exception:
                continue

        return False, f"All import strategies failed for {module_path}"

    def _try_absolute_import(
        self, module_path: str, class_name: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """Try absolute import from project root"""
        try:
            if class_name:
                module = importlib.import_module(module_path)
                return True, getattr(module, class_name)
            else:
                return True, importlib.import_module(module_path)
        except Exception:
            return False, None

    def _try_app_relative_import(
        self, module_path: str, class_name: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """Try import relative to app directory"""
        try:
            app_module_path = f"app.{module_path}"
            if class_name:
                module = importlib.import_module(app_module_path)
                return True, getattr(module, class_name)
            else:
                return True, importlib.import_module(app_module_path)
        except Exception:
            return False, None

    def _try_project_relative_import(
        self, module_path: str, class_name: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """Try import relative to project root"""
        try:
            # Handle cases like "strategy.backtesting" -> "app.strategy.backtesting"
            if not module_path.startswith("app."):
                project_module_path = f"app.{module_path}"
            else:
                project_module_path = module_path

            if class_name:
                module = importlib.import_module(project_module_path)
                return True, getattr(module, class_name)
            else:
                return True, importlib.import_module(project_module_path)
        except Exception:
            return False, None

    def get_available_modules(self) -> list:
        """Get list of modules that can be imported successfully"""
        available = []

        # Test common module paths
        test_modules = [
            "strategy.backtesting",
            "strategy.historical_data_analyzer",
            "strategy.master_agent",
            "data_collection.data_preprocessor",
            "market_analysis.regime_detection",
            "ui.ui",
            "exchange.ccxt_client",
        ]

        for module_path in test_modules:
            success, _ = self.resolve_import(module_path)
            if success:
                available.append(module_path)

        return available

    def test_imports(self) -> dict:
        """Test all imports and return results"""
        results = {}

        test_modules = [
            ("strategy.backtesting", "BacktestingEngine"),
            ("strategy.historical_data_analyzer", "HistoricalDataAnalyzer"),
            ("strategy.master_agent", "MasterAgent"),
            ("data_collection.data_preprocessor", "DataPreprocessor"),
            ("market_analysis.regime_detection", "MarketRegimeDetector"),
            ("ui.ui", None),  # No specific class
            ("exchange.ccxt_client", "CCXTClient"),
        ]

        for module_path, class_name in test_modules:
            success, result = self.resolve_import(module_path, class_name)
            results[module_path] = {
                "success": success,
                "class_name": class_name,
                "result": result if success else str(result),
            }

        return results


# Global import resolver instance
import_resolver = ImportResolver()
