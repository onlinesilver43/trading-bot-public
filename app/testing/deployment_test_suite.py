#!/usr/bin/env python3
"""
Deployment Testing Suite
Tests the reorganized codebase deployment directly using production endpoints
"""

import requests
import json
import time
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
    
    def run_comprehensive_test(self):
        """Run the complete deployment test suite"""
        print("🚀 Starting Comprehensive Deployment Test Suite")
        print("=" * 60)
        
        # Test all endpoints
        summary = self.test_all_endpoints()
        
        # Test bot functionality
        bot_test = self.test_bot_functionality()
        summary["bot_functionality"] = bot_test
        
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
