#!/usr/bin/env python3
"""
Master Agent System - Phase 4 Strategy Implementation
AI orchestrator for multiple strategies with dynamic selection and risk management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

from .performance_db import StrategyPerformanceDB
from ..market_analysis.regime_detection import MarketRegimeDetector
from ..core.utils import get_current_time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Available strategy types"""
    SMA_CROSSOVER = "sma_crossover"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    GRID_TRADING = "grid_trading"

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"

@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    name: str
    strategy_type: StrategyType
    min_capital: float
    max_capital: float
    risk_per_trade: float
    max_drawdown: float
    enabled: bool = True
    priority: int = 1

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: float
    last_updated: datetime
    market_regime: MarketRegime

@dataclass
class PortfolioAllocation:
    """Portfolio allocation decision"""
    strategy_name: str
    allocation_percentage: float
    capital_amount: float
    risk_score: float
    confidence: float
    reasoning: str

class MasterAgent:
    """
    Master Agent System for orchestrating multiple trading strategies
    
    Features:
    - Dynamic strategy selection based on market regime
    - Performance-based capital allocation
    - Risk management and portfolio control
    - Multi-bot orchestration
    - Real-time strategy switching
    """
    
    def __init__(self, 
                 performance_db: StrategyPerformanceDB,
                 regime_detector: MarketRegimeDetector,
                 total_capital: float = 10000.0):
        self.performance_db = performance_db
        self.regime_detector = regime_detector
        self.total_capital = total_capital
        self.allocated_capital = 0.0
        
        # Strategy configurations
        self.strategies = self._initialize_strategies()
        
        # Performance tracking
        self.performance_history = []
        self.allocation_history = []
        
        # Risk management
        self.max_portfolio_risk = 0.02  # 2% max portfolio risk
        self.max_strategy_risk = 0.01   # 1% max risk per strategy
        
        # Market regime tracking
        self.current_regime = None
        self.regime_history = []
        
        logger.info("Master Agent initialized with %d strategies", len(self.strategies))
    
    def _initialize_strategies(self) -> Dict[str, StrategyConfig]:
        """Initialize available trading strategies"""
        return {
            "sma_crossover": StrategyConfig(
                name="SMA Crossover",
                strategy_type=StrategyType.SMA_CROSSOVER,
                min_capital=1000.0,
                max_capital=5000.0,
                risk_per_trade=0.005,  # 0.5% per trade
                max_drawdown=0.15,     # 15% max drawdown
                enabled=True,
                priority=1
            ),
            "mean_reversion": StrategyConfig(
                name="Mean Reversion",
                strategy_type=StrategyType.MEAN_REVERSION,
                min_capital=1000.0,
                max_capital=4000.0,
                risk_per_trade=0.008,  # 0.8% per trade
                max_drawdown=0.20,     # 20% max drawdown
                enabled=True,
                priority=2
            ),
            "momentum": StrategyConfig(
                name="Momentum Trading",
                strategy_type=StrategyType.MOMENTUM,
                min_capital=1500.0,
                max_capital=6000.0,
                risk_per_trade=0.010,  # 1.0% per trade
                max_drawdown=0.25,     # 25% max drawdown
                enabled=True,
                priority=3
            ),
            "grid_trading": StrategyConfig(
                name="Grid Trading",
                strategy_type=StrategyType.GRID_TRADING,
                min_capital=2000.0,
                max_capital=8000.0,
                risk_per_trade=0.003,  # 0.3% per trade
                max_drawdown=0.10,     # 10% max drawdown
                enabled=True,
                priority=4
            )
        }
    
    async def analyze_market_regime(self) -> MarketRegime:
        """Analyze current market regime using the regime detector"""
        try:
            # Get current market data and detect regime
            regime_data = await self.regime_detector.detect_regime()
            current_regime = self._map_regime_data(regime_data)
            
            self.current_regime = current_regime
            self.regime_history.append({
                "timestamp": get_current_time(),
                "regime": current_regime.value,
                "confidence": regime_data.get("confidence", 0.0)
            })
            
            logger.info("Market regime detected: %s (confidence: %.2f)", 
                       current_regime.value, regime_data.get("confidence", 0.0))
            
            return current_regime
            
        except Exception as e:
            logger.error("Error analyzing market regime: %s", str(e))
            # Default to sideways if analysis fails
            return MarketRegime.SIDEWAYS
    
    def _map_regime_data(self, regime_data: Dict[str, Any]) -> MarketRegime:
        """Map regime detector output to MarketRegime enum"""
        regime_name = regime_data.get("regime", "sideways").lower()
        
        if "trend" in regime_name and "up" in regime_name:
            return MarketRegime.TRENDING_UP
        elif "trend" in regime_name and "down" in regime_name:
            return MarketRegime.TRENDING_DOWN
        elif "volatile" in regime_name:
            return MarketRegime.VOLATILE
        elif "low" in regime_name and "volatility" in regime_name:
            return MarketRegime.LOW_VOLATILITY
        else:
            return MarketRegime.SIDEWAYS
    
    async def evaluate_strategy_performance(self) -> Dict[str, StrategyPerformance]:
        """Evaluate performance of all strategies"""
        performance_data = {}
        
        for strategy_name, config in self.strategies.items():
            if not config.enabled:
                continue
                
            try:
                # Get performance metrics from database
                metrics = await self.performance_db.get_strategy_metrics(strategy_name)
                
                if metrics:
                    performance = StrategyPerformance(
                        strategy_name=strategy_name,
                        total_return=metrics.get("total_return", 0.0),
                        sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
                        max_drawdown=metrics.get("max_drawdown", 0.0),
                        win_rate=metrics.get("win_rate", 0.0),
                        total_trades=metrics.get("total_trades", 0),
                        avg_trade_duration=metrics.get("avg_trade_duration", 0.0),
                        last_updated=datetime.now(),
                        market_regime=self.current_regime or MarketRegime.SIDEWAYS
                    )
                    performance_data[strategy_name] = performance
                    
            except Exception as e:
                logger.error("Error evaluating strategy %s: %s", strategy_name, str(e))
        
        return performance_data
    
    def calculate_strategy_scores(self, 
                                performance_data: Dict[str, StrategyPerformance],
                                market_regime: MarketRegime) -> Dict[str, float]:
        """Calculate strategy scores based on performance and market regime"""
        scores = {}
        
        for strategy_name, perf in performance_data.items():
            if strategy_name not in self.strategies:
                continue
                
            config = self.strategies[strategy_name]
            
            # Base score from performance metrics
            base_score = 0.0
            
            # Return-based scoring (40% weight)
            if perf.total_return > 0:
                base_score += 0.4 * min(perf.total_return / 0.1, 1.0)  # Cap at 10% return
            
            # Risk-adjusted scoring (30% weight)
            if perf.sharpe_ratio > 0:
                base_score += 0.3 * min(perf.sharpe_ratio / 2.0, 1.0)  # Cap at 2.0 Sharpe
            
            # Win rate scoring (20% weight)
            base_score += 0.2 * perf.win_rate
            
            # Drawdown penalty (10% weight)
            drawdown_penalty = max(0, perf.max_drawdown - config.max_drawdown)
            base_score -= 0.1 * (drawdown_penalty / config.max_drawdown)
            
            # Market regime adjustment
            regime_multiplier = self._get_regime_multiplier(config.strategy_type, market_regime)
            base_score *= regime_multiplier
            
            # Priority bonus
            priority_bonus = 1.0 + (config.priority * 0.1)
            base_score *= priority_bonus
            
            scores[strategy_name] = max(0.0, base_score)
        
        return scores
    
    def _get_regime_multiplier(self, strategy_type: StrategyType, regime: MarketRegime) -> float:
        """Get performance multiplier based on strategy type and market regime"""
        multipliers = {
            StrategyType.SMA_CROSSOVER: {
                MarketRegime.TRENDING_UP: 1.2,
                MarketRegime.TRENDING_DOWN: 0.8,
                MarketRegime.SIDEWAYS: 1.0,
                MarketRegime.VOLATILE: 0.9,
                MarketRegime.LOW_VOLATILITY: 1.1
            },
            StrategyType.MEAN_REVERSION: {
                MarketRegime.TRENDING_UP: 0.7,
                MarketRegime.TRENDING_DOWN: 0.7,
                MarketRegime.SIDEWAYS: 1.3,
                MarketRegime.VOLATILE: 1.2,
                MarketRegime.LOW_VOLATILITY: 0.9
            },
            StrategyType.MOMENTUM: {
                MarketRegime.TRENDING_UP: 1.4,
                MarketRegime.TRENDING_DOWN: 0.6,
                MarketRegime.SIDEWAYS: 0.8,
                MarketRegime.VOLATILE: 1.1,
                MarketRegime.LOW_VOLATILITY: 0.7
            },
            StrategyType.GRID_TRADING: {
                MarketRegime.TRENDING_UP: 0.9,
                MarketRegime.TRENDING_DOWN: 0.9,
                MarketRegime.SIDEWAYS: 1.1,
                MarketRegime.VOLATILE: 1.0,
                MarketRegime.LOW_VOLATILITY: 1.2
            }
        }
        
        return multipliers.get(strategy_type, {}).get(regime, 1.0)
    
    def calculate_portfolio_allocation(self, 
                                     strategy_scores: Dict[str, float],
                                     available_capital: float) -> List[PortfolioAllocation]:
        """Calculate optimal portfolio allocation based on strategy scores"""
        allocations = []
        
        if not strategy_scores:
            return allocations
        
        # Normalize scores to sum to 1
        total_score = sum(strategy_scores.values())
        if total_score == 0:
            return allocations
        
        # Calculate allocation percentages
        for strategy_name, score in strategy_scores.items():
            if strategy_name not in self.strategies:
                continue
                
            config = self.strategies[strategy_name]
            
            # Calculate allocation percentage
            allocation_pct = score / total_score
            
            # Apply risk constraints
            max_allocation = min(
                allocation_pct,
                self.max_strategy_risk / config.risk_per_trade,
                config.max_capital / available_capital
            )
            
            # Calculate capital amount
            capital_amount = max_allocation * available_capital
            
            # Ensure minimum capital requirement
            if capital_amount < config.min_capital:
                capital_amount = 0.0
                allocation_pct = 0.0
            
            # Calculate risk score and confidence
            risk_score = self._calculate_risk_score(config, capital_amount)
            confidence = self._calculate_confidence(score, config, self.current_regime)
            
            allocation = PortfolioAllocation(
                strategy_name=strategy_name,
                allocation_percentage=allocation_pct,
                capital_amount=capital_amount,
                risk_score=risk_score,
                confidence=confidence,
                reasoning=self._generate_allocation_reasoning(
                    strategy_name, allocation_pct, risk_score, confidence
                )
            )
            
            allocations.append(allocation)
        
        # Sort by allocation percentage (highest first)
        allocations.sort(key=lambda x: x.allocation_percentage, reverse=True)
        
        return allocations
    
    def _calculate_risk_score(self, config: StrategyConfig, capital: float) -> float:
        """Calculate risk score for a strategy allocation"""
        # Risk increases with capital allocation and strategy risk
        base_risk = config.risk_per_trade * (capital / config.min_capital)
        
        # Adjust for drawdown tolerance
        drawdown_factor = config.max_drawdown / 0.20  # Normalize to 20%
        risk_score = base_risk * drawdown_factor
        
        return min(risk_score, 1.0)  # Cap at 100%
    
    def _calculate_confidence(self, score: float, config: StrategyConfig, regime: MarketRegime) -> float:
        """Calculate confidence level for allocation decision"""
        # Base confidence from strategy score
        base_confidence = min(score, 1.0)
        
        # Adjust for strategy priority
        priority_factor = 1.0 + (config.priority * 0.1)
        confidence = base_confidence * priority_factor
        
        # Adjust for market regime alignment
        regime_multiplier = self._get_regime_multiplier(config.strategy_type, regime)
        confidence *= regime_multiplier
        
        return min(confidence, 1.0)  # Cap at 100%
    
    def _generate_allocation_reasoning(self, 
                                     strategy_name: str, 
                                     allocation_pct: float, 
                                     risk_score: float, 
                                     confidence: float) -> str:
        """Generate human-readable reasoning for allocation decision"""
        if allocation_pct == 0:
            return f"{strategy_name}: Insufficient capital or performance for allocation"
        
        reasoning = f"{strategy_name}: {allocation_pct:.1%} allocation"
        
        if confidence > 0.8:
            reasoning += " - High confidence based on strong performance and market alignment"
        elif confidence > 0.6:
            reasoning += " - Good confidence with solid performance metrics"
        else:
            reasoning += " - Lower confidence, monitoring required"
        
        if risk_score > 0.8:
            reasoning += " - High risk allocation, close monitoring needed"
        elif risk_score > 0.5:
            reasoning += " - Moderate risk level"
        else:
            reasoning += " - Low risk allocation"
        
        return reasoning
    
    async def execute_portfolio_rebalancing(self, 
                                         allocations: List[PortfolioAllocation]) -> bool:
        """Execute portfolio rebalancing based on allocation decisions"""
        try:
            logger.info("Executing portfolio rebalancing...")
            
            # Calculate total allocated capital
            total_allocated = sum(alloc.capital_amount for alloc in allocations)
            
            if total_allocated > self.total_capital:
                logger.warning("Total allocation exceeds available capital: %.2f > %.2f", 
                             total_allocated, self.total_capital)
                return False
            
            # Update allocated capital
            self.allocated_capital = total_allocated
            
            # Record allocation decision
            allocation_record = {
                "timestamp": get_current_time(),
                "market_regime": self.current_regime.value if self.current_regime else "unknown",
                "total_capital": self.total_capital,
                "allocated_capital": total_allocated,
                "allocations": [
                    {
                        "strategy": alloc.strategy_name,
                        "percentage": alloc.allocation_percentage,
                        "capital": alloc.capital_amount,
                        "risk_score": alloc.risk_score,
                        "confidence": alloc.confidence
                    }
                    for alloc in allocations
                ]
            }
            
            self.allocation_history.append(allocation_record)
            
            logger.info("Portfolio rebalancing completed: %.2f allocated across %d strategies", 
                       total_allocated, len(allocations))
            
            return True
            
        except Exception as e:
            logger.error("Error executing portfolio rebalancing: %s", str(e))
            return False
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run complete optimization cycle: regime analysis, performance evaluation, and allocation"""
        logger.info("Starting Master Agent optimization cycle...")
        
        try:
            # Step 1: Analyze market regime
            market_regime = await self.analyze_market_regime()
            
            # Step 2: Evaluate strategy performance
            performance_data = await self.evaluate_strategy_performance()
            
            # Step 3: Calculate strategy scores
            strategy_scores = self.calculate_strategy_scores(performance_data, market_regime)
            
            # Step 4: Calculate portfolio allocation
            available_capital = self.total_capital - self.allocated_capital
            allocations = self.calculate_portfolio_allocation(strategy_scores, available_capital)
            
            # Step 5: Execute rebalancing
            rebalancing_success = await self.execute_portfolio_rebalancing(allocations)
            
            # Step 6: Generate summary
            summary = {
                "timestamp": get_current_time(),
                "market_regime": market_regime.value,
                "total_capital": self.total_capital,
                "allocated_capital": self.allocated_capital,
                "available_capital": available_capital,
                "strategy_scores": strategy_scores,
                "allocations": [
                    {
                        "strategy": alloc.strategy_name,
                        "allocation": f"{alloc.allocation_percentage:.1%}",
                        "capital": alloc.capital_amount,
                        "risk_score": f"{alloc.risk_score:.3f}",
                        "confidence": f"{alloc.confidence:.3f}",
                        "reasoning": alloc.reasoning
                    }
                    for alloc in allocations
                ],
                "rebalancing_success": rebalancing_success
            }
            
            logger.info("Master Agent optimization cycle completed successfully")
            return summary
            
        except Exception as e:
            logger.error("Error in optimization cycle: %s", str(e))
            return {
                "timestamp": get_current_time(),
                "error": str(e),
                "status": "failed"
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and metrics"""
        return {
            "timestamp": get_current_time(),
            "total_capital": self.total_capital,
            "allocated_capital": self.allocated_capital,
            "utilization_rate": self.allocated_capital / self.total_capital if self.total_capital > 0 else 0,
            "current_regime": self.current_regime.value if self.current_regime else "unknown",
            "active_strategies": len([s for s in self.strategies.values() if s.enabled]),
            "total_strategies": len(self.strategies),
            "recent_allocations": self.allocation_history[-5:] if self.allocation_history else [],
            "performance_history": self.performance_history[-5:] if self.performance_history else []
        }
    
    def save_state(self, filename: str = None) -> str:
        """Save current state to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"master_agent_state_{timestamp}.json"
        
        state_data = {
            "timestamp": get_current_time(),
            "total_capital": self.total_capital,
            "allocated_capital": self.allocated_capital,
            "current_regime": self.current_regime.value if self.current_regime else "unknown",
            "strategies": {
                name: {
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "min_capital": config.min_capital,
                    "max_capital": config.max_capital,
                    "risk_per_trade": config.risk_per_trade,
                    "max_drawdown": config.max_drawdown
                }
                for name, config in self.strategies.items()
            },
            "allocation_history": self.allocation_history[-10:],  # Last 10 allocations
            "regime_history": self.regime_history[-10:]  # Last 10 regime changes
        }
        
        with open(filename, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        logger.info("Master Agent state saved to: %s", filename)
        return filename

async def main():
    """Test the Master Agent system"""
    # This would be replaced with actual database and regime detector instances
    # For now, we'll create a mock test
    
    print("🚀 Master Agent System - Phase 4 Implementation")
    print("=" * 60)
    
    # Create mock instances (in production, these would be real)
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
    
    # Initialize Master Agent
    master_agent = MasterAgent(
        performance_db=MockPerformanceDB(),
        regime_detector=MockRegimeDetector(),
        total_capital=10000.0
    )
    
    # Run optimization cycle
    print("Running optimization cycle...")
    result = await master_agent.run_optimization_cycle()
    
    print("\n📊 OPTIMIZATION RESULTS:")
    print("-" * 40)
    print(f"Market Regime: {result['market_regime']}")
    print(f"Total Capital: ${result['total_capital']:,.2f}")
    print(f"Allocated: ${result['allocated_capital']:,.2f}")
    print(f"Available: ${result['available_capital']:,.2f}")
    
    print("\n📈 STRATEGY ALLOCATIONS:")
    for alloc in result['allocations']:
        print(f"  {alloc['strategy']:<15} {alloc['allocation']:<8} ${alloc['capital']:>8,.2f}")
        print(f"    Risk: {alloc['risk_score']} | Confidence: {alloc['confidence']}")
        print(f"    {alloc['reasoning']}")
        print()
    
    # Get system status
    status = master_agent.get_system_status()
    print(f"🎯 System Status: {status['active_strategies']}/{status['total_strategies']} strategies active")
    print(f"📊 Utilization Rate: {status['utilization_rate']:.1%}")
    
    print("\n✅ Master Agent system test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
