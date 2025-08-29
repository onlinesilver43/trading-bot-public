#!/usr/bin/env python3
"""
Deployment Testing Suite
Tests the reorganized codebase deployment directly using production endpoints
"""

import requests
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List

# Production endpoint configuration
PRODUCTION_BASE_URL = "http://64.23.214.191:8080"
ENDPOINTS = {
    "system_health": "/api/system/health",
    "system_resources": "/api/system/resources", 
    "system_performance": "/api/system/performance",
    "system_deployments": "/api/system/deployments",
    "bot_state": "/api/state",
    "history_manifest": "/api/history/manifest",
    "history_status": "/api/history/status",
    "exports": "/exports",
    "home": "/"
}

class DeploymentTester:
    def __init__(self, base_url: str = PRODUCTION_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        self.results = {}
        
    def test_endpoint(self, name: str, endpoint: str) -> Dict[str, Any]:
        """Test a single endpoint and return results"""
        url = f"{self.base_url}{endpoint}"
        result = {
            "name": name,
            "endpoint": endpoint,
            "url": url,
            "status": "unknown",
            "response_time": None,
            "status_code": None,
            "error": None,
            "data": None
        }
        
        try:
            start_time = time.time()
            response = self.session.get(url)
            response_time = time.time() - start_time
            
            result["status_code"] = response.status_code
            result["response_time"] = round(response_time * 1000, 2)  # Convert to ms
            
            if response.status_code == 200:
                result["status"] = "success"
                try:
                    result["data"] = response.json()
                except json.JSONDecodeError:
                    result["data"] = response.text[:500]  # First 500 chars if not JSON
            else:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["error"] = "Request timed out"
        except requests.exceptions.ConnectionError:
            result["status"] = "connection_error"
            result["error"] = "Connection failed"
        except Exception as e:
            result["status"] = "exception"
            result["error"] = str(e)
            
        return result

    def test_container_status(self) -> Dict[str, Any]:
        """Test container status and configuration"""
        print("\n🐳 Testing Container Status...")
        
        container_results = {
            "bot_container": {"status": "not_tested", "error": None, "details": {}},
            "ui_container": {"status": "not_tested", "error": None, "details": {}},
            "history_fetcher": {"status": "not_tested", "error": None, "details": {}}
        }
        
        try:
            # Test 1: Bot Container Status
            print("  🤖 Testing Bot Container...")
            bot_cmd = 'sshpass -f ~/.ssh/tb_pw ssh tb "docker ps --format \\"{{.Names}}\\t{{.Image}}\\t{{.Status}}\\" | grep tb-bot-1"'
            bot_result = subprocess.run(bot_cmd, shell=True, capture_output=True, text=True)
            
            if bot_result.returncode == 0 and bot_result.stdout.strip():
                container_results["bot_container"]["status"] = "success"
                container_results["bot_container"]["details"] = {
                    "name": "tb-bot-1",
                    "status": "running",
                    "output": bot_result.stdout.strip()
                }
                print("    ✅ Bot container running")
            else:
                container_results["bot_container"]["status"] = "error"
                container_results["bot_container"]["error"] = "Bot container not found or not running"
                print("    ❌ Bot container not running")
            
            # Test 2: UI Container Status
            print("  🖥️  Testing UI Container...")
            ui_cmd = 'sshpass -f ~/.ssh/tb_pw ssh tb "docker ps --format \\"{{.Names}}\\t{{.Image}}\\t{{.Status}}\\" | grep tb-ui-1"'
            ui_result = subprocess.run(ui_cmd, shell=True, capture_output=True, text=True)
            
            if ui_result.returncode == 0 and ui_result.stdout.strip():
                container_results["ui_container"]["status"] = "success"
                container_results["ui_container"]["details"] = {
                    "name": "tb-ui-1",
                    "status": "running",
                    "output": ui_result.stdout.strip()
                }
                print("    ✅ UI container running")
            else:
                container_results["ui_container"]["status"] = "error"
                container_results["ui_container"]["error"] = "UI container not found or not running"
                print("    ❌ UI container not running")
            
            # Test 3: History Fetcher Status
            print("  📊 Testing History Fetcher...")
            history_cmd = 'sshpass -f ~/.ssh/tb_pw ssh tb "docker ps -a | grep history-fetcher || echo \\"No history fetcher containers found\\""'
            history_result = subprocess.run(history_cmd, shell=True, capture_output=True, text=True)
            
            if "No history fetcher containers found" in history_result.stdout:
                container_results["history_fetcher"]["status"] = "warning"
                container_results["history_fetcher"]["error"] = "History fetcher container not running"
                container_results["history_fetcher"]["details"] = {
                    "status": "not_running",
                    "note": "Container exists but not currently running"
                }
                print("    ⚠️  History fetcher container not running")
            elif history_result.stdout.strip():
                container_results["history_fetcher"]["status"] = "success"
                container_results["history_fetcher"]["details"] = {
                    "status": "running",
                    "output": history_result.stdout.strip()
                }
                print("    ✅ History fetcher container running")
            else:
                container_results["history_fetcher"]["status"] = "error"
                container_results["history_fetcher"]["error"] = "History fetcher status unknown"
                print("    ❌ History fetcher status unknown")
            
            # Test 4: Container Configuration
            print("  ⚙️  Testing Container Configuration...")
            config_cmd = 'sshpass -f ~/.ssh/tb_pw ssh tb "echo \\"--- Bot Config ---\\"; head -n 5 /srv/trading-bots/data/bot_config.json 2>/dev/null || echo \\"Config not found\\""'
            config_result = subprocess.run(config_cmd, shell=True, capture_output=True, text=True)
            
            if "Config not found" not in config_result.stdout:
                print("    ✅ Bot configuration accessible")
            else:
                print("    ⚠️  Bot configuration not accessible")
            
        except Exception as e:
            print(f"    ❌ Container testing error: {str(e)}")
            for container in container_results:
                if container_results[container]["status"] == "not_tested":
                    container_results[container]["status"] = "error"
                    container_results[container]["error"] = f"Testing error: {str(e)}"
        
        return {
            "status": "completed",
            "containers": container_results,
            "summary": {
                "tested": sum(1 for c in container_results.values() if c["status"] != "not_tested"),
                "success": sum(1 for c in container_results.values() if c["status"] == "success"),
                "warning": sum(1 for c in container_results.values() if c["status"] == "warning"),
                "error": sum(1 for c in container_results.values() if c["status"] == "error")
            }
        }
    
    def test_all_endpoints(self) -> Dict[str, Any]:
        """Test all endpoints and return comprehensive results"""
        print("🧪 Testing Production Deployment...")
        print(f"📍 Base URL: {self.base_url}")
        print(f"⏰ Start Time: {datetime.now().isoformat()}")
        print()
        
        all_results = []
        success_count = 0
        total_count = len(ENDPOINTS)
        
        for name, endpoint in ENDPOINTS.items():
            print(f"Testing {name}...", end=" ")
            result = self.test_endpoint(name, endpoint)
            all_results.append(result)
            
            if result["status"] == "success":
                print("✅")
                success_count += 1
            else:
                print(f"❌ ({result['error']})")
                
            # Small delay between requests
            time.sleep(0.5)
        
        # Generate summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_endpoints": total_count,
            "successful_endpoints": success_count,
            "failed_endpoints": total_count - success_count,
            "success_rate": round((success_count / total_count) * 100, 1),
            "results": all_results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print a formatted summary of test results"""
        print()
        print("=" * 60)
        print("🚀 DEPLOYMENT TEST SUMMARY")
        print("=" * 60)
        print(f"📍 Production URL: {summary['base_url']}")
        print(f"⏰ Test Time: {summary['timestamp']}")
        print(f"📊 Success Rate: {summary['success_rate']}% ({summary['successful_endpoints']}/{summary['total_endpoints']})")
        print()
        
        if summary['success_rate'] == 100:
            print("🎉 ALL ENDPOINTS WORKING PERFECTLY!")
        elif summary['success_rate'] >= 80:
            print("✅ Most endpoints working - deployment successful")
        elif summary['success_rate'] >= 60:
            print("⚠️  Some endpoints failing - deployment needs attention")
        else:
            print("❌ Many endpoints failing - deployment has issues")
        
        print()
        print("📋 DETAILED RESULTS:")
        print("-" * 60)
        
        for result in summary['results']:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            response_time = f"({result['response_time']}ms)" if result['response_time'] else ""
            print(f"{status_icon} {result['name']:<20} {result['status']:<15} {response_time}")
            
            if result['error']:
                print(f"    └─ Error: {result['error']}")
        
        # Print Phase 4 component results if available
        if 'phase4_components' in summary and summary['phase4_components']['status'] == 'completed':
            print()
            print("🚀 PHASE 4 COMPONENT RESULTS:")
            print("-" * 60)
            phase4 = summary['phase4_components']
            for component, result in phase4['components'].items():
                if result['status'] == 'success':
                    status_icon = "✅"
                elif result['status'] == 'warning':
                    status_icon = "⚠️"
                elif result['status'] == 'error':
                    status_icon = "❌"
                else:
                    status_icon = "⏸️"
                
                print(f"{status_icon} {component:<20} {result['status']:<15}")
                if result['error']:
                    print(f"    └─ {result['error']}")
            
            print(f"\n📊 Phase 4 Summary: {phase4['summary']['success']}✅ {phase4['summary']['warning']}⚠️ {phase4['summary']['error']}❌")
        
        # Print container status results if available
        if 'container_status' in summary and summary['container_status']['status'] == 'completed':
            print()
            print("🐳 CONTAINER STATUS RESULTS:")
            print("-" * 60)
            containers = summary['container_status']
            for container, result in containers['containers'].items():
                if result['status'] == 'success':
                    status_icon = "✅"
                elif result['status'] == 'warning':
                    status_icon = "⚠️"
                elif result['status'] == 'error':
                    status_icon = "❌"
                else:
                    status_icon = "⏸️"
                
                print(f"{status_icon} {container:<20} {result['status']:<15}")
                if result['error']:
                    print(f"    └─ {result['error']}")
                if result['details']:
                    for key, value in result['details'].items():
                        print(f"        {key}: {value}")
            
            print(f"\n📊 Container Summary: {containers['summary']['success']}✅ {containers['summary']['warning']}⚠️ {containers['summary']['error']}❌")
        
        print()
        print("=" * 60)
    
    def save_report(self, summary: Dict[str, Any], filename: str = None):
        """Save test results to a JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deployment_test_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Detailed report saved to: {filename}")
    
    def test_bot_functionality(self) -> Dict[str, Any]:
        """Test specific bot functionality"""
        print("\n🤖 Testing Bot Functionality...")
        
        # Test bot state
        state_result = self.test_endpoint("bot_state", "/api/state")
        
        if state_result["status"] == "success" and state_result["data"]:
            data = state_result["data"]
            
            # Check for key bot data
            bot_status = {
                "has_portfolio": "portfolio" in data,
                "has_trades": "trades" in data and len(data["trades"]) > 0,
                "has_current_position": "position" in data,
                "has_equity": "equity_usd" in data,
                "trading_active": False
            }
            
            # Check if trading is active (recent trades)
            if bot_status["has_trades"]:
                trades = data["trades"]
                if trades:
                    latest_trade = trades[-1]
                    trade_time = latest_trade.get("t", "")
                    # Check if trade is within last hour
                    if trade_time:
                        try:
                            trade_dt = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
                            time_diff = datetime.now().astimezone() - trade_dt
                            bot_status["trading_active"] = time_diff.total_seconds() < 3600
                        except:
                            pass
            
            return {
                "status": "success",
                "bot_status": bot_status,
                "portfolio_summary": {
                    "equity_usd": data.get("equity_usd", "N/A"),
                    "position": data.get("position", "N/A"),
                    "cash_usd": data.get("cash_usd", "N/A"),
                    "coin_units": data.get("coin_units", "N/A"),
                    "total_trades": len(data.get("trades", []))
                }
            }
        else:
            return {
                "status": "failed",
                "error": state_result.get("error", "Unknown error")
            }
    
    def test_phase4_components(self) -> Dict[str, Any]:
        """Test Phase 4 components after deployment"""
        print("\n🚀 Testing Phase 4 Components...")
        
        phase4_results = {
            "master_agent": {"status": "not_tested", "error": None},
            "historical_analyzer": {"status": "not_tested", "error": None},
            "strategy_discovery": {"status": "not_tested", "error": None},
            "bot_orchestrator": {"status": "not_tested", "error": None},
            "data_connector": {"status": "not_tested", "error": None},
            "real_data_access": {"status": "not_tested", "error": None}
        }
        
        try:
            # Test 1: Historical Data Access
            print("  📊 Testing Historical Data Access...")
            history_result = self.test_endpoint("history_manifest", "/api/history/manifest")
            if history_result["status"] == "success":
                if history_result["data"] and history_result["data"].get("status") != "no_data":
                    phase4_results["data_connector"]["status"] = "success"
                    print("    ✅ Historical data accessible")
                else:
                    phase4_results["data_connector"]["status"] = "warning"
                    phase4_results["data_connector"]["error"] = "No historical data available yet"
                    print("    ⚠️  No historical data available (may be normal for new deployment)")
            else:
                phase4_results["data_connector"]["status"] = "error"
                phase4_results["data_connector"]["error"] = f"History endpoint failed: {history_result.get('error')}"
                print("    ❌ Historical data endpoint failed")
            
            # Test 2: Real Data Access (Enhanced)
            print("  🔍 Testing Real Data Access...")
            real_data_result = self._test_real_data_access()
            if real_data_result["status"] == "success":
                phase4_results["real_data_access"]["status"] = "success"
                print(f"    ✅ Real data accessible: {real_data_result['details']}")
            elif real_data_result["status"] == "warning":
                phase4_results["real_data_access"]["status"] = "warning"
                phase4_results["real_data_access"]["error"] = real_data_result.get("error", "Limited real data access")
                print(f"    ⚠️  Limited real data access: {real_data_result.get('error')}")
            else:
                phase4_results["real_data_access"]["status"] = "error"
                phase4_results["real_data_access"]["error"] = real_data_result.get("error", "Real data access failed")
                print(f"    ❌ Real data access failed: {real_data_result.get('error')}")
            
            # Test 3: Enhanced System Status
            print("  🔧 Testing Enhanced System Status...")
            health_result = self.test_endpoint("system_health", "/api/system/health")
            if health_result["status"] == "success" and health_result["data"]:
                data = health_result["data"]
                if data.get("status") == "enhanced":
                    print("    ✅ Enhanced system monitoring active")
                else:
                    print("    ⚠️  Basic system monitoring (enhanced features may not be deployed)")
            
            # Test 4: Strategy Endpoints (if they exist)
            print("  🎯 Testing Strategy Endpoints...")
            # Note: These endpoints may not exist yet in current deployment
            print("    ℹ️  Strategy endpoints not yet implemented (Phase 4 in progress)")
            
            # Test 5: Performance Monitoring
            print("  📈 Testing Performance Monitoring...")
            perf_result = self.test_endpoint("system_performance", "/api/system/performance")
            if perf_result["status"] == "success":
                print("    ✅ Performance monitoring active")
            else:
                print("    ⚠️  Performance monitoring not available")
            
        except Exception as e:
            print(f"    ❌ Phase 4 testing error: {str(e)}")
            for component in phase4_results:
                if phase4_results[component]["status"] == "not_tested":
                    phase4_results[component]["status"] = "error"
                    phase4_results[component]["error"] = f"Testing error: {str(e)}"
        
        return {
            "status": "completed",
            "components": phase4_results,
            "summary": {
                "tested": sum(1 for c in phase4_results.values() if c["status"] != "not_tested"),
                "success": sum(1 for c in phase4_results.values() if c["status"] == "success"),
                "warning": sum(1 for c in phase4_results.values() if c["status"] == "warning"),
                "error": sum(1 for c in phase4_results.values() if c["status"] == "error")
            }
        }
    
    def _test_real_data_access(self) -> Dict[str, Any]:
        """Test access to real collected historical data"""
        try:
            import subprocess
            import json
            
            print("    🔍 Checking collected data on server...")
            
            # Test SSH connection and data access
            ssh_cmd = 'sshpass -f ~/.ssh/tb_pw ssh tb "cat /srv/trading-bots/history/manifest.json | jq \'.statistics\'"'
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"SSH connection failed: {result.stderr}"
                }
            
            try:
                stats = json.loads(result.stdout)
                
                # Check if we have substantial data
                total_files = stats.get("total_files", 0)
                total_size_mb = round(stats.get("total_size_bytes", 0) / (1024 * 1024), 2)
                symbols = list(stats.get("symbols", {}).keys())
                intervals = list(stats.get("intervals", {}).keys())
                
                if total_files > 100 and total_size_mb > 10:
                    return {
                        "status": "success",
                        "details": f"{total_files} files, {total_size_mb} MB, {len(symbols)} symbols, {len(intervals)} intervals"
                    }
                elif total_files > 0:
                    return {
                        "status": "warning",
                        "error": f"Limited data: {total_files} files, {total_size_mb} MB"
                    }
                else:
                    return {
                        "status": "error",
                        "error": "No collected data found"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error": "Failed to parse manifest data"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Real data testing error: {str(e)}"
            }
    
    def run_comprehensive_test(self):
        """Run the complete deployment test suite"""
        print("🚀 Starting Comprehensive Deployment Test Suite")
        print("=" * 60)
        
        # Test all endpoints
        summary = self.test_all_endpoints()
        
        # Test bot functionality
        bot_test = self.test_bot_functionality()
        summary["bot_functionality"] = bot_test
        
        # Test Phase 4 components
        phase4_test = self.test_phase4_components()
        summary["phase4_components"] = phase4_test

        # Test container status
        container_test = self.test_container_status()
        summary["container_status"] = container_test
        
        # Print summary
        self.print_summary(summary)
        
        # Save detailed report
        self.save_report(summary)
        
        return summary

def main():
    """Main test runner"""
    tester = DeploymentTester()
    results = tester.run_comprehensive_test()
    
    # Return exit code based on success rate
    if results["success_rate"] >= 80:
        print("🎉 Deployment test PASSED - system is operational!")
        exit(0)
    else:
        print("❌ Deployment test FAILED - system has issues!")
        exit(1)

if __name__ == "__main__":
    main()
