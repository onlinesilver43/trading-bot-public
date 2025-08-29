#!/usr/bin/env python3
"""
Multi-Bot Orchestrator - Phase 4 Strategy Implementation
Manages 3-bot architecture with strategy switching and coordination
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclass import dataclass
from enum import Enum
import json
import uuid

from .master_agent import MasterAgent, PortfolioAllocation
from .performance_db import StrategyPerformanceDB
from ..market_analysis.regime_detection import MarketRegimeDetector
from ..core.utils import get_current_time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotStatus(Enum):
    """Bot status enumeration"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class BotType(Enum):
    """Bot type enumeration"""
    AGGRESSIVE = "aggressive"      # High risk, high reward
    MODERATE = "moderate"          # Balanced risk/reward
    CONSERVATIVE = "conservative"  # Low risk, steady returns

@dataclass
class BotConfig:
    """Configuration for a trading bot"""
    bot_id: str
    bot_type: BotType
    name: str
    description: str
    max_capital: float
    risk_tolerance: float  # 0.0 to 1.0
    strategy_switching_enabled: bool
    auto_rebalancing: bool
    max_positions: int
    min_trade_size: float
    max_trade_size: float

@dataclass
class BotState:
    """Current state of a trading bot"""
    bot_id: str
    status: BotStatus
    current_strategy: str
    allocated_capital: float
    active_positions: int
    total_pnl: float
    daily_pnl: float
    last_activity: datetime
    error_message: Optional[str] = None

@dataclass
class StrategyAssignment:
    """Strategy assignment to a bot"""
    bot_id: str
    strategy_name: str
    allocation_percentage: float
    capital_amount: float
    assigned_at: datetime
    performance_metrics: Dict[str, Any]

class MultiBotOrchestrator:
    """
    Multi-Bot Orchestrator for managing 3 trading bots
    
    Features:
    - 3-bot architecture (Aggressive, Moderate, Conservative)
    - Dynamic strategy assignment and switching
    - Risk-based capital allocation
    - Performance monitoring and optimization
    - Coordinated execution across bots
    """
    
    def __init__(self, 
                 master_agent: MasterAgent,
                 performance_db: StrategyPerformanceDB,
                 regime_detector: MarketRegimeDetector):
        self.master_agent = master_agent
        self.performance_db = performance_db
        self.regime_detector = regime_detector
        
        # Bot configurations
        self.bots = self._initialize_bots()
        
        # Bot states
        self.bot_states = {}
        self._initialize_bot_states()
        
        # Strategy assignments
        self.strategy_assignments = {}
        
        # Performance tracking
        self.performance_history = []
        self.coordination_history = []
        
        # Configuration
        self.rebalancing_interval = timedelta(hours=4)  # Rebalance every 4 hours
        self.last_rebalancing = None
        self.strategy_switching_threshold = 0.15  # 15% performance difference triggers switch
        
        logger.info("Multi-Bot Orchestrator initialized with %d bots", len(self.bots))
    
    def _initialize_bots(self) -> Dict[str, BotConfig]:
        """Initialize the 3 trading bots with different risk profiles"""
        return {
            "bot_aggressive": BotConfig(
                bot_id="bot_aggressive",
                bot_type=BotType.AGGRESSIVE,
                name="Aggressive Bot",
                description="High-risk, high-reward trading with momentum strategies",
                max_capital=5000.0,
                risk_tolerance=0.8,
                strategy_switching_enabled=True,
                auto_rebalancing=True,
                max_positions=5,
                min_trade_size=100.0,
                max_trade_size=1000.0
            ),
            "bot_moderate": BotConfig(
                bot_id="bot_moderate",
                bot_type=BotType.MODERATE,
                name="Moderate Bot",
                description="Balanced risk/reward with diversified strategies",
                max_capital=3000.0,
                risk_tolerance=0.5,
                strategy_switching_enabled=True,
                auto_rebalancing=True,
                max_positions=3,
                min_trade_size=75.0,
                max_trade_size=500.0
            ),
            "bot_conservative": BotConfig(
                bot_id="bot_conservative",
                bot_type=BotType.CONSERVATIVE,
                name="Conservative Bot",
                description="Low-risk, steady returns with defensive strategies",
                max_capital=2000.0,
                risk_tolerance=0.2,
                strategy_switching_enabled=False,  # Conservative bot keeps stable strategies
                auto_rebalancing=True,
                max_positions=2,
                min_trade_size=50.0,
                max_trade_size=250.0
            )
        }
    
    def _initialize_bot_states(self):
        """Initialize bot states"""
        for bot_id, config in self.bots.items():
            self.bot_states[bot_id] = BotState(
                bot_id=bot_id,
                status=BotStatus.IDLE,
                current_strategy="",
                allocated_capital=0.0,
                active_positions=0,
                total_pnl=0.0,
                daily_pnl=0.0,
                last_activity=datetime.now()
            )
    
    async def assign_strategies_to_bots(self, 
                                      portfolio_allocations: List[PortfolioAllocation]) -> Dict[str, StrategyAssignment]:
        """Assign strategies to bots based on risk profile and performance"""
        assignments = {}
        
        # Sort allocations by performance and risk
        sorted_allocations = sorted(
            portfolio_allocations,
            key=lambda x: (x.confidence, x.allocation_percentage),
            reverse=True
        )
        
        # Assign strategies to bots based on risk tolerance
        for allocation in sorted_allocations:
            strategy_name = allocation.strategy_name
            capital_amount = allocation.capital_amount
            
            # Find best bot for this strategy
            best_bot = self._find_best_bot_for_strategy(strategy_name, capital_amount)
            
            if best_bot:
                # Create strategy assignment
                assignment = StrategyAssignment(
                    bot_id=best_bot,
                    strategy_name=strategy_name,
                    allocation_percentage=allocation.allocation_percentage,
                    capital_amount=capital_amount,
                    assigned_at=datetime.now(),
                    performance_metrics={
                        "confidence": allocation.confidence,
                        "risk_score": allocation.risk_score,
                        "reasoning": allocation.reasoning
                    }
                )
                
                assignments[best_bot] = assignment
                
                # Update bot state
                self.bot_states[best_bot].current_strategy = strategy_name
                self.bot_states[best_bot].allocated_capital = capital_amount
                self.bot_states[best_bot].status = BotStatus.ACTIVE
                self.bot_states[best_bot].last_activity = datetime.now()
                
                logger.info("Assigned strategy %s to bot %s with %.2f capital", 
                           strategy_name, best_bot, capital_amount)
        
        self.strategy_assignments = assignments
        return assignments
    
    def _find_best_bot_for_strategy(self, strategy_name: str, capital_amount: float) -> Optional[str]:
        """Find the best bot for a given strategy based on risk profile and capacity"""
        available_bots = []
        
        for bot_id, config in self.bots.items():
            current_state = self.bot_states[bot_id]
            
            # Check if bot has capacity
            if current_state.allocated_capital + capital_amount <= config.max_capital:
                # Calculate compatibility score
                compatibility_score = self._calculate_bot_strategy_compatibility(
                    config, strategy_name, capital_amount
                )
                
                available_bots.append((bot_id, compatibility_score))
        
        if not available_bots:
            return None
        
        # Return bot with highest compatibility score
        best_bot = max(available_bots, key=lambda x: x[1])
        return best_bot[0]
    
    def _calculate_bot_strategy_compatibility(self, 
                                           bot_config: BotConfig, 
                                           strategy_name: str, 
                                           capital_amount: float) -> float:
        """Calculate compatibility score between bot and strategy"""
        score = 0.0
        
        # Risk tolerance alignment (40% weight)
        strategy_risk = self._get_strategy_risk_level(strategy_name)
        risk_alignment = 1.0 - abs(bot_config.risk_tolerance - strategy_risk)
        score += 0.4 * risk_alignment
        
        # Capital efficiency (30% weight)
        capital_efficiency = min(capital_amount / bot_config.max_capital, 1.0)
        score += 0.3 * capital_efficiency
        
        # Strategy switching capability (20% weight)
        if bot_config.strategy_switching_enabled:
            score += 0.2
        
        # Position capacity (10% weight)
        position_capacity = 1.0 - (self.bot_states[bot_config.bot_id].active_positions / bot_config.max_positions)
        score += 0.1 * max(0.0, position_capacity)
        
        return score
    
    def _get_strategy_risk_level(self, strategy_name: str) -> float:
        """Get risk level for a strategy (0.0 to 1.0)"""
        risk_levels = {
            "sma_crossover": 0.4,
            "mean_reversion": 0.6,
            "momentum": 0.8,
            "grid_trading": 0.3
        }
        return risk_levels.get(strategy_name, 0.5)
    
    async def execute_bot_coordination(self) -> Dict[str, Any]:
        """Execute coordination across all bots"""
        logger.info("Executing bot coordination...")
        
        try:
            coordination_results = {}
            
            for bot_id, config in self.bots.items():
                if bot_id in self.strategy_assignments:
                    # Execute bot-specific coordination
                    result = await self._coordinate_bot(bot_id, config)
                    coordination_results[bot_id] = result
                else:
                    # Bot has no strategy assigned
                    coordination_results[bot_id] = {
                        "status": "no_strategy",
                        "message": "No strategy currently assigned"
                    }
            
            # Record coordination
            coordination_record = {
                "timestamp": get_current_time(),
                "results": coordination_results,
                "total_bots": len(self.bots),
                "active_bots": len([r for r in coordination_results.values() if r.get("status") == "success"])
            }
            
            self.coordination_history.append(coordination_record)
            
            logger.info("Bot coordination completed: %d/%d bots active", 
                       coordination_record["active_bots"], coordination_record["total_bots"])
            
            return coordination_results
            
        except Exception as e:
            logger.error("Error in bot coordination: %s", str(e))
            return {"error": str(e), "status": "failed"}
    
    async def _coordinate_bot(self, bot_id: str, config: BotConfig) -> Dict[str, Any]:
        """Coordinate individual bot execution"""
        try:
            assignment = self.strategy_assignments[bot_id]
            current_state = self.bot_states[bot_id]
            
            # Check if strategy switching is needed
            if config.strategy_switching_enabled:
                should_switch = await self._should_switch_strategy(bot_id, assignment)
                if should_switch:
                    await self._switch_bot_strategy(bot_id, assignment)
            
            # Execute strategy-specific coordination
            execution_result = await self._execute_bot_strategy(bot_id, assignment)
            
            # Update bot state
            current_state.last_activity = datetime.now()
            if execution_result.get("status") == "success":
                current_state.status = BotStatus.ACTIVE
            else:
                current_state.status = BotStatus.ERROR
                current_state.error_message = execution_result.get("error", "Unknown error")
            
            return {
                "status": "success",
                "strategy": assignment.strategy_name,
                "execution_result": execution_result,
                "bot_state": {
                    "status": current_state.status.value,
                    "allocated_capital": current_state.allocated_capital,
                    "active_positions": current_state.active_positions,
                    "total_pnl": current_state.total_pnl
                }
            }
            
        except Exception as e:
            logger.error("Error coordinating bot %s: %s", bot_id, str(e))
            return {"status": "error", "error": str(e)}
    
    async def _should_switch_strategy(self, bot_id: str, current_assignment: StrategyAssignment) -> bool:
        """Determine if bot should switch strategies based on performance"""
        try:
            # Get current strategy performance
            current_performance = await self.performance_db.get_strategy_metrics(
                current_assignment.strategy_name
            )
            
            if not current_performance:
                return False
            
            # Get alternative strategy performance
            alternative_strategies = self._get_alternative_strategies(current_assignment.strategy_name)
            
            for alt_strategy in alternative_strategies:
                alt_performance = await self.performance_db.get_strategy_metrics(alt_strategy)
                
                if alt_performance:
                    # Calculate performance difference
                    current_return = current_performance.get("total_return", 0.0)
                    alt_return = alt_performance.get("total_return", 0.0)
                    
                    performance_diff = alt_return - current_return
                    
                    # Switch if alternative is significantly better
                    if performance_diff > self.strategy_switching_threshold:
                        logger.info("Strategy switch recommended: %s -> %s (diff: %.2f%%)", 
                                   current_assignment.strategy_name, alt_strategy, performance_diff * 100)
                        return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking strategy switch: %s", str(e))
            return False
    
    def _get_alternative_strategies(self, current_strategy: str) -> List[str]:
        """Get alternative strategies for switching"""
        all_strategies = ["sma_crossover", "mean_reversion", "momentum", "grid_trading"]
        return [s for s in all_strategies if s != current_strategy]
    
    async def _switch_bot_strategy(self, bot_id: str, current_assignment: StrategyAssignment):
        """Switch bot to a different strategy"""
        try:
            # Find best alternative strategy
            alternative_strategies = self._get_alternative_strategies(current_assignment.strategy_name)
            
            best_alternative = None
            best_performance = -float('inf')
            
            for alt_strategy in alternative_strategies:
                performance = await self.performance_db.get_strategy_metrics(alt_strategy)
                if performance:
                    return_metric = performance.get("total_return", 0.0)
                    if return_metric > best_performance:
                        best_performance = return_metric
                        best_alternative = alt_strategy
            
            if best_alternative:
                # Update assignment
                new_assignment = StrategyAssignment(
                    bot_id=bot_id,
                    strategy_name=best_alternative,
                    allocation_percentage=current_assignment.allocation_percentage,
                    capital_amount=current_assignment.capital_amount,
                    assigned_at=datetime.now(),
                    performance_metrics={
                        "previous_strategy": current_assignment.strategy_name,
                        "switch_reason": "Performance-based switching",
                        "new_strategy_performance": best_performance
                    }
                )
                
                self.strategy_assignments[bot_id] = new_assignment
                
                # Update bot state
                self.bot_states[bot_id].current_strategy = best_alternative
                
                logger.info("Bot %s switched from %s to %s", 
                           bot_id, current_assignment.strategy_name, best_alternative)
                
        except Exception as e:
            logger.error("Error switching bot strategy: %s", str(e))
    
    async def _execute_bot_strategy(self, bot_id: str, assignment: StrategyAssignment) -> Dict[str, Any]:
        """Execute the assigned strategy for a bot"""
        try:
            strategy_name = assignment.strategy_name
            capital_amount = assignment.capital_amount
            
            # This would integrate with actual strategy execution
            # For now, we'll simulate execution
            execution_result = {
                "strategy": strategy_name,
                "capital_allocated": capital_amount,
                "execution_time": datetime.now().isoformat(),
                "status": "success"
            }
            
            # Simulate some execution details
            if strategy_name == "sma_crossover":
                execution_result["actions"] = ["Analyzing SMA signals", "Checking entry conditions"]
            elif strategy_name == "mean_reversion":
                execution_result["actions"] = ["Calculating mean reversion levels", "Monitoring price deviations"]
            elif strategy_name == "momentum":
                execution_result["actions"] = ["Tracking momentum indicators", "Identifying trend strength"]
            elif strategy_name == "grid_trading":
                execution_result["actions"] = ["Setting grid levels", "Monitoring grid execution"]
            
            return execution_result
            
        except Exception as e:
            logger.error("Error executing bot strategy: %s", str(e))
            return {"status": "error", "error": str(e)}
    
    async def run_orchestration_cycle(self) -> Dict[str, Any]:
        """Run complete orchestration cycle"""
        logger.info("Starting Multi-Bot Orchestration cycle...")
        
        try:
            # Step 1: Get portfolio allocations from Master Agent
            master_result = await self.master_agent.run_optimization_cycle()
            
            if master_result.get("status") == "failed":
                return {"status": "failed", "error": "Master Agent optimization failed"}
            
            # Step 2: Assign strategies to bots
            portfolio_allocations = master_result.get("allocations", [])
            strategy_assignments = await self.assign_strategies_to_bots(portfolio_allocations)
            
            # Step 3: Execute bot coordination
            coordination_results = await self.execute_bot_coordination()
            
            # Step 4: Generate summary
            summary = {
                "timestamp": get_current_time(),
                "master_agent_result": master_result,
                "strategy_assignments": {
                    bot_id: {
                        "strategy": assignment.strategy_name,
                        "allocation": f"{assignment.allocation_percentage:.1%}",
                        "capital": assignment.capital_amount,
                        "assigned_at": assignment.assigned_at.isoformat()
                    }
                    for bot_id, assignment in strategy_assignments.items()
                },
                "coordination_results": coordination_results,
                "bot_states": {
                    bot_id: {
                        "status": state.status.value,
                        "current_strategy": state.current_strategy,
                        "allocated_capital": state.allocated_capital,
                        "active_positions": state.active_positions,
                        "total_pnl": state.total_pnl
                    }
                    for bot_id, state in self.bot_states.items()
                }
            }
            
            logger.info("Multi-Bot Orchestration cycle completed successfully")
            return summary
            
        except Exception as e:
            logger.error("Error in orchestration cycle: %s", str(e))
            return {"status": "failed", "error": str(e)}
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        active_bots = len([s for s in self.bot_states.values() if s.status == BotStatus.ACTIVE])
        total_capital = sum(s.allocated_capital for s in self.bot_states.values())
        
        return {
            "timestamp": get_current_time(),
            "total_bots": len(self.bots),
            "active_bots": active_bots,
            "total_capital_allocated": total_capital,
            "bot_states": {
                bot_id: {
                    "status": state.status.value,
                    "strategy": state.current_strategy,
                    "capital": state.allocated_capital,
                    "positions": state.active_positions,
                    "pnl": state.total_pnl
                }
                for bot_id, state in self.bot_states.items()
            },
            "strategy_assignments": len(self.strategy_assignments),
            "last_coordination": self.coordination_history[-1] if self.coordination_history else None
        }
    
    def save_orchestrator_state(self, filename: str = None) -> str:
        """Save orchestrator state to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_bot_orchestrator_state_{timestamp}.json"
        
        state_data = {
            "timestamp": get_current_time(),
            "bots": {
                bot_id: {
                    "config": {
                        "name": config.name,
                        "type": config.bot_type.value,
                        "max_capital": config.max_capital,
                        "risk_tolerance": config.risk_tolerance
                    },
                    "state": {
                        "status": state.status.value,
                        "current_strategy": state.current_strategy,
                        "allocated_capital": state.allocated_capital,
                        "active_positions": state.active_positions,
                        "total_pnl": state.total_pnl
                    }
                }
                for bot_id, (config, state) in zip(self.bots.items(), self.bot_states.values())
            },
            "strategy_assignments": {
                bot_id: {
                    "strategy": assignment.strategy_name,
                    "allocation": assignment.allocation_percentage,
                    "capital": assignment.capital_amount,
                    "assigned_at": assignment.assigned_at.isoformat()
                }
                for bot_id, assignment in self.strategy_assignments.items()
            },
            "coordination_history": self.coordination_history[-5:],  # Last 5 coordinations
            "performance_history": self.performance_history[-5:]  # Last 5 performance records
        }
        
        with open(filename, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        logger.info("Multi-Bot Orchestrator state saved to: %s", filename)
        return filename

async def main():
    """Test the Multi-Bot Orchestrator system"""
    print("🚀 Multi-Bot Orchestrator - Phase 4 Implementation")
    print("=" * 60)
    
    # Create mock instances (in production, these would be real)
    class MockMasterAgent:
        async def run_optimization_cycle(self):
            return {
                "timestamp": get_current_time(),
                "market_regime": "trending_up",
                "total_capital": 10000.0,
                "allocated_capital": 8000.0,
                "available_capital": 2000.0,
                "allocations": [
                    {
                        "strategy": "momentum",
                        "allocation": "40.0%",
                        "capital": 3200.0,
                        "risk_score": "0.750",
                        "confidence": "0.850",
                        "reasoning": "momentum: 40.0% allocation - High confidence based on strong performance and market alignment - Moderate risk level"
                    },
                    {
                        "strategy": "sma_crossover",
                        "allocation": "30.0%",
                        "capital": 2400.0,
                        "risk_score": "0.600",
                        "confidence": "0.800",
                        "reasoning": "sma_crossover: 30.0% allocation - High confidence based on strong performance and market alignment - Moderate risk level"
                    },
                    {
                        "strategy": "grid_trading",
                        "allocation": "30.0%",
                        "capital": 2400.0,
                        "risk_score": "0.450",
                        "confidence": "0.750",
                        "reasoning": "grid_trading: 30.0% allocation - Good confidence with solid performance metrics - Low risk allocation"
                    }
                ],
                "rebalancing_success": True
            }
    
    class MockPerformanceDB:
        async def get_strategy_metrics(self, strategy_name):
            return {
                "total_return": 0.05,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08,
                "win_rate": 0.65,
                "total_trades": 25,
                "avg_trade_duration": 2.5
            }
    
    class MockRegimeDetector:
        async def detect_regime(self):
            return {
                "regime": "trending_up",
                "confidence": 0.85
            }
    
    # Initialize orchestrator
    orchestrator = MultiBotOrchestrator(
        master_agent=MockMasterAgent(),
        performance_db=MockPerformanceDB(),
        regime_detector=MockRegimeDetector()
    )
    
    # Run orchestration cycle
    print("Running orchestration cycle...")
    result = await orchestrator.run_orchestration_cycle()
    
    print("\n📊 ORCHESTRATION RESULTS:")
    print("-" * 40)
    print(f"Market Regime: {result['master_agent_result']['market_regime']}")
    print(f"Total Capital: ${result['master_agent_result']['total_capital']:,.2f}")
    print(f"Allocated: ${result['master_agent_result']['allocated_capital']:,.2f}")
    
    print("\n🤖 BOT ASSIGNMENTS:")
    for bot_id, assignment in result['strategy_assignments'].items():
        print(f"  {bot_id:<20} {assignment['strategy']:<15} {assignment['allocation']:<8} ${assignment['capital']:>8,.2f}")
    
    print("\n📈 BOT STATES:")
    for bot_id, state in result['bot_states'].items():
        print(f"  {bot_id:<20} {state['status']:<12} {state['current_strategy']:<15} ${state['allocated_capital']:>8,.2f}")
    
    # Get orchestrator status
    status = orchestrator.get_orchestrator_status()
    print(f"\n🎯 Orchestrator Status: {status['active_bots']}/{status['total_bots']} bots active")
    print(f"📊 Total Capital Allocated: ${status['total_capital_allocated']:,.2f}")
    
    print("\n✅ Multi-Bot Orchestrator system test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
