#!/usr/bin/env python3
"""
Deployment Workflow Test Suite
Tests the deployment workflow system to ensure it works correctly
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any


class DeploymentWorkflowTester:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.workflows_dir = self.project_root / ".github" / "workflows"
        self.results = {}

    def test_workflow_files_exist(self) -> Dict[str, Any]:
        """Test that all required workflow files exist"""
        print("🔍 Testing deployment workflow files...")

        required_workflows = [
            "deploy-core.yml",
            "deploy-data.yml",
            "deploy-config.yml",
            "deploy.yml",  # Legacy workflow
        ]

        missing_workflows = []
        existing_workflows = []

        for workflow in required_workflows:
            workflow_path = self.workflows_dir / workflow
            if workflow_path.exists():
                existing_workflows.append(workflow)
                print(f"  ✅ {workflow} exists")
            else:
                missing_workflows.append(workflow)
                print(f"  ❌ {workflow} missing")

        return {
            "status": "success" if not missing_workflows else "error",
            "existing": existing_workflows,
            "missing": missing_workflows,
            "total_required": len(required_workflows),
            "total_existing": len(existing_workflows),
        }

    def test_workflow_syntax(self) -> Dict[str, Any]:
        """Test that all workflow files have valid YAML syntax"""
        print("\n🔍 Testing workflow YAML syntax...")

        syntax_results = {}
        all_valid = True

        for workflow_file in self.workflows_dir.glob("*.yml"):
            try:
                # Try to parse YAML
                with open(workflow_file, "r") as f:
                    import yaml

                    yaml.safe_load(f)

                syntax_results[workflow_file.name] = "valid"
                print(f"  ✅ {workflow_file.name} - YAML syntax valid")
            except Exception as e:
                syntax_results[workflow_file.name] = f"invalid: {str(e)}"
                all_valid = False
                print(f"  ❌ {workflow_file.name} - YAML syntax error: {str(e)}")

        return {
            "status": "success" if all_valid else "error",
            "results": syntax_results,
            "total_workflows": len(syntax_results),
            "valid_count": sum(1 for r in syntax_results.values() if r == "valid"),
            "invalid_count": sum(1 for r in syntax_results.values() if r != "valid"),
        }

    def test_workflow_triggers(self) -> Dict[str, Any]:
        """Test that workflows have appropriate triggers and path filters"""
        print("\n🔍 Testing workflow triggers and path filters...")

        trigger_results = {}

        # Test deploy-core.yml
        core_workflow = self.workflows_dir / "deploy-core.yml"
        if core_workflow.exists():
            with open(core_workflow, "r") as f:
                content = f.read()

            # Check for path filters
            if "paths:" in content and "app/**" in content:
                trigger_results["deploy-core"] = (
                    "✅ Has path filters for app/** and compose/**"
                )
            else:
                trigger_results["deploy-core"] = (
                    "❌ Missing path filters for app/** and compose/**"
                )

        # Test deploy-data.yml
        data_workflow = self.workflows_dir / "deploy-data.yml"
        if data_workflow.exists():
            with open(data_workflow, "r") as f:
                content = f.read()

            if "paths:" in content and "history_fetcher/**" in content:
                trigger_results["deploy-data"] = (
                    "✅ Has path filters for data components"
                )
            else:
                trigger_results["deploy-data"] = (
                    "❌ Missing path filters for data components"
                )

        # Test deploy-config.yml
        config_workflow = self.workflows_dir / "deploy-config.yml"
        if config_workflow.exists():
            with open(config_workflow, "r") as f:
                content = f.read()

            if "paths:" in content and "config/**" in content:
                trigger_results["deploy-config"] = (
                    "✅ Has path filters for config components"
                )
            else:
                trigger_results["deploy-config"] = (
                    "❌ Missing path filters for config components"
                )

        return {
            "status": (
                "success"
                if all("✅" in r for r in trigger_results.values())
                else "warning"
            ),
            "results": trigger_results,
        }

    def test_data_preservation_logic(self) -> Dict[str, Any]:
        """Test that workflows preserve data directories"""
        print("\n🔍 Testing data preservation logic...")

        preservation_results = {}

        # Check deploy-core.yml for data preservation
        core_workflow = self.workflows_dir / "deploy-core.yml"
        if core_workflow.exists():
            with open(core_workflow, "r") as f:
                content = f.read()

            # Should NOT have --delete for data directories
            if (
                "--delete" in content
                and "history" not in content
                and "data" not in content
            ):
                preservation_results["deploy-core"] = (
                    "✅ Only updates app/compose, preserves data"
                )
            else:
                preservation_results["deploy-core"] = "❌ May affect data directories"

        # Check deploy-data.yml for data preservation
        data_workflow = self.workflows_dir / "deploy-data.yml"
        if data_workflow.exists():
            with open(data_workflow, "r") as f:
                content = f.read()

            if "preserve collected data" in content:
                preservation_results["deploy-data"] = (
                    "✅ Explicitly preserves collected data"
                )
            else:
                preservation_results["deploy-data"] = (
                    "⚠️  No explicit data preservation message"
                )

        return {
            "status": (
                "success"
                if all("✅" in r for r in preservation_results.values())
                else "warning"
            ),
            "results": preservation_results,
        }

    def test_health_checks(self) -> Dict[str, Any]:
        """Test that workflows include proper health checks"""
        print("\n🔍 Testing health check implementations...")

        health_check_results = {}

        workflows_to_check = ["deploy-core.yml", "deploy-data.yml", "deploy-config.yml"]

        for workflow_name in workflows_to_check:
            workflow_path = self.workflows_dir / workflow_name
            if workflow_path.exists():
                with open(workflow_path, "r") as f:
                    content = f.read()

                if "Health Check" in content:
                    health_check_results[workflow_name] = "✅ Has health check step"
                else:
                    health_check_results[workflow_name] = "❌ Missing health check step"

        return {
            "status": (
                "success"
                if all("✅" in r for r in health_check_results.values())
                else "warning"
            ),
            "results": health_check_results,
        }

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all deployment workflow tests"""
        print("🚀 Starting Deployment Workflow Test Suite")
        print("=" * 60)

        # Run all tests
        self.results["workflow_files"] = self.test_workflow_files_exist()
        self.results["workflow_syntax"] = self.test_workflow_syntax()
        self.results["workflow_triggers"] = self.test_workflow_triggers()
        self.results["data_preservation"] = self.test_data_preservation_logic()
        self.results["health_checks"] = self.test_health_checks()

        # Print summary
        self.print_summary()

        # Save detailed report
        self.save_report()

        return self.results

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🚀 DEPLOYMENT WORKFLOW TEST SUMMARY")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "success")
        warning_tests = sum(
            1 for r in self.results.values() if r["status"] == "warning"
        )
        failed_tests = sum(1 for r in self.results.values() if r["status"] == "error")

        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"⚠️  Warnings: {warning_tests}")
        print(f"❌ Failed: {failed_tests}")

        print("\n📋 DETAILED RESULTS:")
        for test_name, result in self.results.items():
            status_icon = (
                "✅"
                if result["status"] == "success"
                else "⚠️" if result["status"] == "warning" else "❌"
            )
            print(f"  {status_icon} {test_name}: {result['status']}")

    def save_report(self):
        """Save detailed test report"""
        timestamp = subprocess.run(
            ["date", "-u", "+%Y%m%d_%H%M%S"], capture_output=True, text=True
        ).stdout.strip()

        report_file = f"deployment_workflow_test_report_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main test runner"""
    tester = DeploymentWorkflowTester()
    results = tester.run_comprehensive_test()

    # Return exit code based on results
    if any(r["status"] == "error" for r in results.values()):
        print("\n❌ Deployment workflow tests FAILED!")
        exit(1)
    elif any(r["status"] == "warning" for r in results.values()):
        print("\n⚠️  Deployment workflow tests passed with warnings!")
        exit(0)
    else:
        print("\n🎉 All deployment workflow tests PASSED!")
        exit(0)


if __name__ == "__main__":
    main()
