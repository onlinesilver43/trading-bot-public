#!/usr/bin/env python3
"""
Phase 4 Integration Test Runner
Tests Phase 4 components with both test data and real data
"""

import sys
import asyncio
from pathlib import Path

def main():
    """Main test runner"""
    print("🚀 Phase 4 Integration Test Runner")
    print("=" * 50)
    
    # Check command line arguments
    use_real_data = "--real-data" in sys.argv
    run_deployment_tests = "--deployment" in sys.argv
    run_simple_tests = "--simple" in sys.argv
    run_suite_tests = "--suite" in sys.argv
    
    # If no specific tests specified, run all
    if not any([run_deployment_tests, run_simple_tests, run_suite_tests]):
        run_deployment_tests = True
        run_simple_tests = True
        run_suite_tests = True
    
    print(f"🔍 Data Source: {'REAL DATA' if use_real_data else 'TEST DATA'}")
    print(f"🧪 Deployment Tests: {'Yes' if run_deployment_tests else 'No'}")
    print(f"🧪 Simple Tests: {'Yes' if run_simple_tests else 'No'}")
    print(f"🧪 Suite Tests: {'Yes' if run_suite_tests else 'No'}")
    print()
    
    results = {}
    
    # Run deployment tests
    if run_deployment_tests:
        print("🐳 Running Deployment Tests...")
        try:
            from testing.deployment_test_suite import DeploymentTestSuite
            suite = DeploymentTestSuite()
            deployment_results = suite.run_comprehensive_test()
            results["deployment"] = deployment_results
            print("✅ Deployment tests completed")
        except Exception as e:
            print(f"❌ Deployment tests failed: {e}")
            results["deployment"] = {"error": str(e)}
    
    # Run simple Phase 4 tests
    if run_simple_tests:
        print("\n🧪 Running Simple Phase 4 Tests...")
        try:
            from simple_phase4_test import SimplePhase4Test
            test = SimplePhase4Test(use_real_data=use_real_data)
            simple_results = asyncio.run(test.run_simple_test())
            results["simple"] = simple_results
            print("✅ Simple Phase 4 tests completed")
        except Exception as e:
            print(f"❌ Simple Phase 4 tests failed: {e}")
            results["simple"] = {"error": str(e)}
    
    # Run Phase 4 suite tests
    if run_suite_tests:
        print("\n🧪 Running Phase 4 Suite Tests...")
        try:
            from testing.test_phase4_suite import Phase4TestSuite
            suite = Phase4TestSuite()
            suite_results = suite.run_all_tests()
            results["suite"] = {"success": suite_results}
            print("✅ Phase 4 suite tests completed")
        except Exception as e:
            print(f"❌ Phase 4 suite tests failed: {e}")
            results["suite"] = {"error": str(e)}
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 50)
    
    for test_type, result in results.items():
        if "error" in result:
            print(f"❌ {test_type.title()}: Failed - {result['error']}")
        elif test_type == "deployment":
            success_rate = result.get("success_rate", 0)
            print(f"✅ {test_type.title()}: {success_rate}% success rate")
        elif test_type == "simple":
            status = result.get("status", "unknown")
            print(f"✅ {test_type.title()}: {status}")
        elif test_type == "suite":
            success = result.get("success", False)
            print(f"✅ {test_type.title()}: {'Passed' if success else 'Failed'}")
    
    print("\n💡 Usage:")
    print("  python3 test_phase4_integration.py                    # Run all tests with test data")
    print("  python3 test_phase4_integration.py --real-data        # Run all tests with real data")
    print("  python3 test_phase4_integration.py --deployment       # Run only deployment tests")
    print("  python3 test_phase4_integration.py --simple           # Run only simple tests")
    print("  python3 test_phase4_integration.py --suite            # Run only suite tests")
    
    return all("error" not in result for result in results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
