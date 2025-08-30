#!/usr/bin/env python3
"""
Core Test Infrastructure for Trading Bot System
Provides clean, maintainable test framework with proper organization

This file provides the foundation for all test suites in the system.
"""

import sys
import os
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from enum import Enum

# Configure logging
import logging

# Add the app directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir.endswith("testing"):
    app_dir = os.path.dirname(current_dir)
else:
    app_dir = current_dir
sys.path.insert(0, app_dir)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test status enumeration"""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


class ComponentHealth(Enum):
    """Component health status"""

    OPERATIONAL = "OPERATIONAL"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class TestResult:
    """Result of a single test"""

    component: str
    test_name: str
    status: TestStatus
    duration: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None


@dataclass
class ComponentStatus:
    """Status of a component"""

    name: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    overall_status: ComponentHealth = ComponentHealth.UNKNOWN
    last_test_time: datetime = field(default_factory=datetime.now)


class TestSuite:
    """Base class for all test suites with clean architecture"""

    def __init__(self, name: str):
        self.name = name
        self.test_results: List[TestResult] = []
        self.component_status: Dict[str, ComponentStatus] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Test configuration
        self.enabled_components: List[str] = []
        self.skip_missing_dependencies: bool = True

    def add_component(self, component_name: str) -> None:
        """Add a component to be tested"""
        if component_name not in self.component_status:
            self.component_status[component_name] = ComponentStatus(name=component_name)
        self.enabled_components.append(component_name)

    def run_test(
        self,
        component: str,
        test_name: str,
        test_func: Callable[[], Any],
        skip_if_missing: bool = True,
    ) -> TestResult:
        """Run a single test with proper error handling"""
        start_time = time.time()

        try:
            # Run the test
            result = test_func()
            duration = time.time() - start_time

            # Record successful test
            test_result = TestResult(
                component=component,
                test_name=test_name,
                status=TestStatus.PASS,
                duration=duration,
                message="Test passed successfully",
                details={"result": result},
            )

        except ImportError as e:
            duration = time.time() - start_time
            if skip_if_missing and self.skip_missing_dependencies:
                test_result = TestResult(
                    component=component,
                    test_name=test_name,
                    status=TestStatus.SKIP,
                    duration=duration,
                    message=f"Module not available: {str(e)}",
                    error=e,
                )
            else:
                test_result = TestResult(
                    component=component,
                    test_name=test_name,
                    status=TestStatus.FAIL,
                    duration=duration,
                    message=f"Import failed: {str(e)}",
                    error=e,
                )

        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(
                component=component,
                test_name=test_name,
                status=TestStatus.ERROR,
                duration=duration,
                message=f"Test error: {str(e)}",
                error=e,
            )

        # Record the result
        self._record_test_result(test_result)
        return test_result

    def _record_test_result(self, result: TestResult) -> None:
        """Record a test result and update component status"""
        self.test_results.append(result)

        # Get or create component status
        if result.component not in self.component_status:
            self.component_status[result.component] = ComponentStatus(
                name=result.component
            )

        comp_status = self.component_status[result.component]
        comp_status.total_tests += 1
        comp_status.last_test_time = datetime.now()

        # Update test counts
        if result.status == TestStatus.PASS:
            comp_status.passed_tests += 1
        elif result.status == TestStatus.FAIL:
            comp_status.failed_tests += 1
        elif result.status == TestStatus.SKIP:
            comp_status.skipped_tests += 1
        elif result.status == TestStatus.ERROR:
            comp_status.error_tests += 1

        # Update overall component status
        if comp_status.failed_tests > 0 or comp_status.error_tests > 0:
            comp_status.overall_status = ComponentHealth.FAILED
        elif comp_status.passed_tests == comp_status.total_tests:
            comp_status.overall_status = ComponentHealth.OPERATIONAL
        elif comp_status.passed_tests > 0:
            comp_status.overall_status = ComponentHealth.PARTIAL
        else:
            comp_status.overall_status = ComponentHealth.UNKNOWN

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests in the suite - to be implemented by subclasses"""
        self.start_time = datetime.now()
        logger.info(f"🚀 Starting {self.name}")
        logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Subclasses implement this
            self._run_tests()

            self.end_time = datetime.now()
            report = self._generate_test_report()

            logger.info(f"✅ {self.name} completed")
            return report

        except Exception as e:
            logger.error(f"❌ {self.name} failed with error: {e}")
            traceback.print_exc()
            return {"status": "ERROR", "error": str(e)}

    def _run_tests(self) -> None:
        """Override this method in subclasses to implement actual tests"""
        raise NotImplementedError("Subclasses must implement _run_tests")

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        if not self.end_time or not self.start_time:
            duration = 0
        else:
            duration = (self.end_time - self.start_time).total_seconds()

        total_tests = len(self.test_results)
        passed_tests = len(
            [r for r in self.test_results if r.status == TestStatus.PASS]
        )
        failed_tests = len(
            [r for r in self.test_results if r.status == TestStatus.FAIL]
        )
        skipped_tests = len(
            [r for r in self.test_results if r.status == TestStatus.SKIP]
        )
        error_tests = len(
            [r for r in self.test_results if r.status == TestStatus.ERROR]
        )

        # Calculate component summary
        component_summary = {}
        for comp_name, comp_status in self.component_status.items():
            component_summary[comp_name] = {
                "total_tests": comp_status.total_tests,
                "passed_tests": comp_status.passed_tests,
                "failed_tests": comp_status.failed_tests,
                "skipped_tests": comp_status.skipped_tests,
                "error_tests": comp_status.error_tests,
                "overall_status": comp_status.overall_status.value,
                "last_test_time": comp_status.last_test_time.isoformat(),
            }

        return {
            "status": "COMPLETED",
            "test_suite": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "error_tests": error_tests,
                "success_rate": (
                    (passed_tests / total_tests * 100) if total_tests > 0 else 0
                ),
            },
            "component_summary": component_summary,
            "test_results": [
                {
                    "component": r.component,
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details,
                    "error": str(r.error) if r.error else None,
                }
                for r in self.test_results
            ],
        }

    def print_test_report(self) -> None:
        """Print a formatted test report to console"""
        report = self._generate_test_report()

        print("\n" + "=" * 80)
        print(f"🧪 {report['test_suite'].upper()} REPORT")
        print("=" * 80)

        if report["status"] == "COMPLETED":
            summary = report["summary"]
            print("📊 Overall Results:")
            print(f"   Total Tests: {summary['total_tests']}")
            print(f"   Passed: {summary['passed_tests']} ✅")
            print(f"   Failed: {summary['failed_tests']} ❌")
            print(f"   Skipped: {summary['skipped_tests']} ⏭️")
            print(f"   Errors: {summary['error_tests']} 💥")
            print(f"   Success Rate: {summary['success_rate']:.1f}%")

            if report["duration_seconds"]:
                print(f"\n⏱️  Total Duration: {report['duration_seconds']:.2f} seconds")

            print("\n🔧 Component Status:")
            for comp_name, comp_data in report["component_summary"].items():
                status_emoji = {
                    "OPERATIONAL": "✅",
                    "PARTIAL": "⚠️",
                    "FAILED": "❌",
                    "UNKNOWN": "❓",
                }.get(comp_data["overall_status"], "❓")

                print(f"   {status_emoji} {comp_name}: {comp_data['overall_status']}")
                print(
                    f"      Tests: {comp_data['passed_tests']}/{comp_data['total_tests']} passed"
                )

            if summary["failed_tests"] > 0 or summary["error_tests"] > 0:
                print("\n❌ Failed Tests:")
                for result in report["test_results"]:
                    if result["status"] in ["FAIL", "ERROR"]:
                        print(
                            f"   • {result['component']} - {result['test_name']}: {result['message']}"
                        )
        else:
            print(f"❌ Test suite failed: {report.get('error', 'Unknown error')}")

        print("=" * 80)


def safe_import_test(module_path: str, class_name: Optional[str] = None) -> Any:
    """Safely test importing a module or class"""
    try:
        # Since we're in app/testing and the Python path includes the app directory,
        # we can import directly using the module path
        if class_name:
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        else:
            return __import__(module_path)
    except ImportError:
        raise ImportError(f"Module {module_path} not available")


def safe_function_test(func: Callable, *args, **kwargs) -> Any:
    """Safely test calling a function"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        raise Exception(f"Function {func.__name__} failed: {str(e)}")
